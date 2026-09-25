/**
 * ChartStateBridge.js — Synchronized State Bridge for Dual-Engine Financial Charting (Milestone M3)
 * 
 * Provides seamless, zero-data-loss synchronization between:
 *   1. Hardware-accelerated Native Lightweight-Charts canvas (with SMC overlays)
 *   2. Embedded TradingView Pro widget (iframe / widget SDK)
 * 
 * Persists and synchronizes across toggles:
 *   - Active financial symbol (with automated brokerage prefix mapping)
 *   - Active timeframe / interval (M1, M5, M15, M30, H1, H4, D1 <-> TV interval)
 *   - Real-time crosshair coordinate & price alignment
 *   - User drawings, annotations, and SMC level tags
 *   - Layer visibility toggles (FVG, OB, VPVR, VWAP, CVD, CHoCH/BOS)
 *   - Visible time range and viewport pan/zoom state
 */

class ChartStateBridge {
    constructor(initialState = {}) {
        this.storageKey = initialState.storageKey || 'jarvis_chart_state_bridge_v1';
        
        // Canonical State Store
        this.state = {
            activeSymbol: 'XAUUSD',
            activeTimeframe: 'M15',
            activeEngine: 'lightweight', // 'lightweight' | 'tradingview'
            theme: 'dark',
            crosshair: {
                visible: false,
                price: null,
                time: null,
                x: null,
                y: null
            },
            visibleRange: {
                from: null,
                to: null
            },
            drawings: [],
            indicatorLayers: {
                fvg: true,
                fvgCe: true,
                ob: true,
                chochBos: true,
                vpvr: true,
                vwap: true,
                cvdWaves: true,
                rsiDiv: true,
                ote: true,
                sweeps: true,
                killzones: true
            },
            lastUpdated: Date.now()
        };

        // Brokerage Symbol Mappings (Lightweight <-> TradingView)
        this.symbolMap = {
            'XAUUSD': 'OANDA:XAUUSD',
            'EURUSD': 'FX:EURUSD',
            'GBPUSD': 'FX:GBPUSD',
            'USDJPY': 'FX:USDJPY',
            'BTCUSD': 'BINANCE:BTCUSDT',
            'ETHUSD': 'BINANCE:ETHUSDT',
            'SOLUSD': 'COINBASE:SOLUSD'
        };

        this.reverseSymbolMap = {};
        for (const [k, v] of Object.entries(this.symbolMap)) {
            this.reverseSymbolMap[v] = k;
        }

        // Timeframe Interval Mappings (Lightweight <-> TradingView)
        this.intervalMap = {
            'M1': '1',
            'M5': '5',
            'M15': '15',
            'M30': '30',
            'H1': '60',
            'H4': '240',
            'D1': 'D'
        };

        this.reverseIntervalMap = {};
        for (const [k, v] of Object.entries(this.intervalMap)) {
            this.reverseIntervalMap[v] = k;
        }

        // Subscribers & Engine References
        this.subscribers = [];
        this.lightweightEngine = null;
        this.tvIframeElement = null;

        // Merge initial state or restore from storage
        this.restoreFromStorage();
        if (initialState) {
            this.importState(initialState);
        }
    }

    /* -------------------------------------------------------------
     * SYMBOL & TIMEFRAME ACCESSORS WITH ZERO-LOSS SYNC
     * ------------------------------------------------------------- */
    getSymbol() {
        return this.state.activeSymbol;
    }

    setSymbol(newSymbol, sourceEngine = null) {
        if (!newSymbol) return;
        const normalized = newSymbol.toUpperCase();
        if (this.state.activeSymbol === normalized) return;

        this.state.activeSymbol = normalized;
        this.state.lastUpdated = Date.now();
        this._notify('symbol', { symbol: normalized, source: sourceEngine });
        this.persistToStorage();
        return normalized;
    }

    getTimeframe() {
        return this.state.activeTimeframe;
    }

    setTimeframe(newTimeframe, sourceEngine = null) {
        if (!newTimeframe) return;
        const normalized = newTimeframe.toUpperCase();
        if (this.state.activeTimeframe === normalized) return;

        this.state.activeTimeframe = normalized;
        this.state.lastUpdated = Date.now();
        this._notify('timeframe', { timeframe: normalized, source: sourceEngine });
        this.persistToStorage();
        return normalized;
    }

    getActiveEngine() {
        return this.state.activeEngine;
    }

    /* -------------------------------------------------------------
     * CROSSHAIR & VIEWPORT SYNCHRONIZATION
     * ------------------------------------------------------------- */
    setCrosshair(crosshairData) {
        if (!crosshairData) return;
        this.state.crosshair = Object.assign({}, this.state.crosshair, crosshairData);
        this._notify('crosshair', this.state.crosshair);
    }

    getCrosshair() {
        return Object.assign({}, this.state.crosshair);
    }

    setVisibleRange(range) {
        if (!range) return;
        this.state.visibleRange = {
            from: range.from !== undefined ? range.from : this.state.visibleRange.from,
            to: range.to !== undefined ? range.to : this.state.visibleRange.to
        };
        this._notify('visible_range', this.state.visibleRange);
    }

    getVisibleRange() {
        return Object.assign({}, this.state.visibleRange);
    }

    /* -------------------------------------------------------------
     * DRAWINGS & ANNOTATIONS PERSISTENCE
     * ------------------------------------------------------------- */
    addDrawing(drawing) {
        if (!drawing) return null;
        const d = Object.assign({
            id: drawing.id || `draw_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
            symbol: drawing.symbol || this.state.activeSymbol,
            timeframe: drawing.timeframe || this.state.activeTimeframe,
            type: drawing.type || 'line',
            points: drawing.points || [],
            properties: drawing.properties || {},
            text: drawing.text || '',
            created: Date.now()
        }, drawing);

        this.state.drawings.push(d);
        this.persistToStorage();
        this._notify('drawing_added', d);
        return d;
    }

    updateDrawing(id, updates) {
        const idx = this.state.drawings.findIndex(d => d.id === id);
        if (idx === -1) return null;
        this.state.drawings[idx] = Object.assign({}, this.state.drawings[idx], updates);
        this.persistToStorage();
        this._notify('drawing_updated', this.state.drawings[idx]);
        return this.state.drawings[idx];
    }

    removeDrawing(id) {
        const initialLen = this.state.drawings.length;
        this.state.drawings = this.state.drawings.filter(d => d.id !== id);
        if (this.state.drawings.length !== initialLen) {
            this.persistToStorage();
            this._notify('drawing_removed', { id });
            return true;
        }
        return false;
    }

    getDrawings(filter = {}) {
        let results = [...this.state.drawings];
        if (filter.symbol) {
            const sym = filter.symbol.toUpperCase();
            results = results.filter(d => (d.symbol || '').toUpperCase() === sym);
        }
        if (filter.timeframe) {
            const tf = filter.timeframe.toUpperCase();
            results = results.filter(d => (d.timeframe || '').toUpperCase() === tf);
        }
        if (filter.type) {
            results = results.filter(d => d.type === filter.type);
        }
        return results;
    }

    clearDrawings(symbol = null) {
        if (symbol) {
            const sym = symbol.toUpperCase();
            this.state.drawings = this.state.drawings.filter(d => (d.symbol || '').toUpperCase() !== sym);
        } else {
            this.state.drawings = [];
        }
        this.persistToStorage();
        this._notify('drawings_cleared', { symbol });
    }

    /* -------------------------------------------------------------
     * INDICATOR LAYER VISIBILITY SYNCHRONIZATION
     * ------------------------------------------------------------- */
    setIndicatorLayer(layerName, isVisible) {
        this.state.indicatorLayers[layerName] = Boolean(isVisible);
        this.persistToStorage();
        this._notify('indicator_layer', { layer: layerName, visible: Boolean(isVisible) });
    }

    getIndicatorLayers() {
        return Object.assign({}, this.state.indicatorLayers);
    }

    /* -------------------------------------------------------------
     * DUAL-ENGINE SEAMLESS TOGGLE (ZERO DATA LOSS)
     * ------------------------------------------------------------- */
    bindLightweightEngine(engineInstance) {
        this.lightweightEngine = engineInstance;
        if (engineInstance && typeof engineInstance.attachStateBridge === 'function') {
            engineInstance.attachStateBridge(this);
        }
    }

    bindTradingViewIframe(iframeElement) {
        this.tvIframeElement = iframeElement;
    }

    mapToTradingViewSymbol(symbol) {
        const sym = (symbol || this.state.activeSymbol).toUpperCase();
        return this.symbolMap[sym] || `OANDA:${sym}`;
    }

    mapFromTradingViewSymbol(tvSymbol) {
        if (!tvSymbol) return this.state.activeSymbol;
        if (this.reverseSymbolMap[tvSymbol]) return this.reverseSymbolMap[tvSymbol];
        const parts = tvSymbol.split(':');
        return parts.length > 1 ? parts[1].replace('USDT', 'USD') : tvSymbol;
    }

    mapToTradingViewInterval(timeframe) {
        const tf = (timeframe || this.state.activeTimeframe).toUpperCase();
        return this.intervalMap[tf] || '15';
    }

    mapFromTradingViewInterval(interval) {
        return this.reverseIntervalMap[String(interval)] || 'M15';
    }

    generateTradingViewWidgetUrl(options = {}) {
        const tvSym = this.mapToTradingViewSymbol(options.symbol || this.state.activeSymbol);
        const tvInterval = this.mapToTradingViewInterval(options.timeframe || this.state.activeTimeframe);
        const theme = options.theme || this.state.theme || 'dark';

        const params = new URLSearchParams({
            symbol: tvSym,
            interval: tvInterval,
            theme: theme,
            style: '1',
            timezone: 'Etc/UTC',
            studies: '[]',
            hide_side_toolbar: '0',
            allow_symbol_change: '1',
            save_image: '1',
            details: '1',
            hotlist: '1',
            calendar: '1'
        });

        return `https://s.tradingview.com/widgetembed/?${params.toString()}`;
    }

    switchToTradingView(targetIframe = null) {
        const iframe = targetIframe || this.tvIframeElement;
        const targetUrl = this.generateTradingViewWidgetUrl();

        if (iframe) {
            // Only update iframe source if it differs, preserving existing cache if matching
            if (!iframe.src || !iframe.src.includes(this.mapToTradingViewSymbol(this.state.activeSymbol))) {
                iframe.src = targetUrl;
            }
        }

        this.state.activeEngine = 'tradingview';
        this.state.lastUpdated = Date.now();
        this._notify('engine_switched', {
            engine: 'tradingview',
            symbol: this.state.activeSymbol,
            timeframe: this.state.activeTimeframe,
            tvSymbol: this.mapToTradingViewSymbol(this.state.activeSymbol),
            tvInterval: this.mapToTradingViewInterval(this.state.activeTimeframe)
        });
        this.persistToStorage();
        return targetUrl;
    }

    switchToLightweight(targetEngine = null) {
        const engine = targetEngine || this.lightweightEngine;

        if (engine) {
            if (typeof engine.setSymbol === 'function') {
                engine.setSymbol(this.state.activeSymbol);
            }
            if (typeof engine.setTimeframe === 'function') {
                engine.setTimeframe(this.state.activeTimeframe);
            }
        }

        this.state.activeEngine = 'lightweight';
        this.state.lastUpdated = Date.now();
        this._notify('engine_switched', {
            engine: 'lightweight',
            symbol: this.state.activeSymbol,
            timeframe: this.state.activeTimeframe
        });
        this.persistToStorage();
        return this.state.activeEngine;
    }

    toggleEngine() {
        if (this.state.activeEngine === 'lightweight') {
            return this.switchToTradingView();
        } else {
            return this.switchToLightweight();
        }
    }

    /* -------------------------------------------------------------
     * SERIALIZATION, IMPORT/EXPORT & STORAGE PERSISTENCE
     * ------------------------------------------------------------- */
    exportState() {
        return JSON.parse(JSON.stringify(this.state));
    }

    importState(importedState) {
        if (!importedState || typeof importedState !== 'object') return;

        if (importedState.activeSymbol) this.state.activeSymbol = String(importedState.activeSymbol).toUpperCase();
        if (importedState.activeTimeframe) this.state.activeTimeframe = String(importedState.activeTimeframe).toUpperCase();
        if (importedState.activeEngine) this.state.activeEngine = importedState.activeEngine;
        if (importedState.theme) this.state.theme = importedState.theme;

        if (Array.isArray(importedState.drawings)) {
            this.state.drawings = [...importedState.drawings];
        }
        if (importedState.indicatorLayers && typeof importedState.indicatorLayers === 'object') {
            this.state.indicatorLayers = Object.assign({}, this.state.indicatorLayers, importedState.indicatorLayers);
        }
        if (importedState.visibleRange) {
            this.state.visibleRange = Object.assign({}, this.state.visibleRange, importedState.visibleRange);
        }

        this.state.lastUpdated = Date.now();
        this.persistToStorage();
        this._notify('state_imported', this.exportState());
    }

    persistToStorage() {
        if (typeof window !== 'undefined' && window.localStorage) {
            try {
                window.localStorage.setItem(this.storageKey, JSON.stringify(this.exportState()));
            } catch (e) {
                console.warn('ChartStateBridge: localStorage write failed:', e);
            }
        }
    }

    restoreFromStorage() {
        if (typeof window !== 'undefined' && window.localStorage) {
            try {
                const raw = window.localStorage.getItem(this.storageKey);
                if (raw) {
                    const parsed = JSON.parse(raw);
                    this.importState(parsed);
                    return true;
                }
            } catch (e) {
                console.warn('ChartStateBridge: localStorage read failed:', e);
            }
        }
        return false;
    }

    /* -------------------------------------------------------------
     * SUBSCRIBER & DOM EVENT DISPATCHING
     * ------------------------------------------------------------- */
    subscribe(callback) {
        if (typeof callback === 'function') {
            this.subscribers.push(callback);
        }
        return () => this.unsubscribe(callback);
    }

    unsubscribe(callback) {
        this.subscribers = this.subscribers.filter(fn => fn !== callback);
    }

    _notify(changeType, payload) {
        // 1. Notify direct subscribers
        for (const cb of this.subscribers) {
            try {
                cb(changeType, payload, this.state);
            } catch (e) {
                console.error('Error in ChartStateBridge subscriber:', e);
            }
        }

        // 2. Dispatch global DOM CustomEvent
        if (typeof window !== 'undefined' && typeof window.CustomEvent === 'function') {
            const evt = new CustomEvent('jarvis:chart:state_changed', {
                detail: {
                    changeType: changeType,
                    payload: payload,
                    state: this.exportState()
                },
                bubbles: true,
                cancelable: true
            });
            window.dispatchEvent(evt);
        }
    }
}

// Singleton global instance
const chartStateBridge = new ChartStateBridge();

// Universal Module Definition
if (typeof window !== 'undefined') {
    window.ChartStateBridge = ChartStateBridge;
    window.chartStateBridge = chartStateBridge;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ChartStateBridge,
        chartStateBridge
    };
}
