/**
 * smc_overlays.js — Institutional Smart Money Concepts (SMC) Canvas Rendering Engine (Milestone M3)
 * 
 * Synchronizes transparent HTML5 Canvas layer over ChartEngine to render:
 *   1. Fair Value Gaps (FVG) with 50% Consequent Encroachment (CE) dashed midlines & mitigation tracking.
 *   2. Institutional Order Blocks (OB) Demand & Supply zones with touch counters (TAPS) & mitigation tracking.
 *   3. Liquidity Sweeps, Change of Character (CHoCH), and Market Structure Breaks (BOS) lines.
 *   4. Visible-Range Volume Profile (VPVR) with Point of Control (POC) and 70% Value Area (VAH/VAL).
 *   5. Cumulative Volume Delta (CVD) absorption divergence waves.
 *   6. Multi-Band Anchored VWAP (±1σ, ±2σ, ±3σ standard deviation bands).
 *   7. RSI multi-timeframe divergence rays.
 *   8. Optimal Trade Entry (OTE) 62% - 79% Fibonacci grids with 70.5% Institutional Sweet Spot.
 *   9. Interbank IPDA Session Killzones (London Open, NY AM, NY PM, Asian Range).
 *  10. Interactive Canvas Click Hit-Testing dispatching 'jarvis:smc:pattern_clicked'.
 */

class SMCOverlaysRenderer {
    constructor(containerElement, chartEngineInstance, options = {}) {
        this.container = typeof containerElement === 'string' ? document.getElementById(containerElement) : containerElement;
        if (!this.container) {
            throw new Error(`SMCOverlaysRenderer: Container element '${containerElement}' not found.`);
        }

        this.chart = chartEngineInstance;
        this.options = Object.assign({
            globalOpacity: 0.88,
            autoAttachControls: false,
            enableHitTesting: true,
            vpvrWidth: 140,
            vpvrBins: 60,
            vpvrValueArea: 0.70
        }, options);

        // SMC State Data Store
        this.smcData = {
            symbol: 'XAUUSD',
            timeframe: 'M15',
            fvgs: [],
            order_blocks: [],
            ote: null,
            sweeps: [],
            killzones: [],
            choch_bos: [],
            vpvr: null,
            cvd_waves: [],
            anchored_vwap: null,
            rsi_divergences: []
        };

        // Layer Visibility Toggles
        this.layers = {
            fvg: true,
            fvgCe: true,
            ob: true,
            ote: true,
            sweeps: true,
            killzones: true,
            chochBos: true,
            vpvr: true,
            cvdWaves: true,
            vwap: true,
            rsiDiv: true
        };
        this.globalOpacity = this.options.globalOpacity;

        // Hit-test region cache for interactive pattern clicks
        this.hitTestRegions = [];
        this.patternClickedCallbacks = [];

        // Overlay Canvas Setup
        this.canvas = document.createElement('canvas');
        this.canvas.className = 'smc-canvas-overlay';
        this.canvas.style.position = 'absolute';
        this.canvas.style.left = '0';
        this.canvas.style.top = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none'; // Pass gestures to chart engine, container handles click
        this.canvas.style.zIndex = '2';
        this.container.appendChild(this.canvas);

        this.ctx = this.canvas.getContext('2d');
        this.dpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;
        this.renderPending = false;

        this._initResizeObserver();
        this._bindChartEvents();
        this._bindHitTesting();

        if (this.options.autoAttachControls) {
            this.createControlsHUD();
        }
    }

    _initResizeObserver() {
        if (typeof ResizeObserver !== 'undefined') {
            this.resizeObserver = new ResizeObserver(() => this.handleResize());
            this.resizeObserver.observe(this.container);
        }
        this.handleResize();
    }

    handleResize() {
        const rect = this.container.getBoundingClientRect ? this.container.getBoundingClientRect() : { width: 800, height: 500 };
        this.dpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;
        this.width = rect.width || 800;
        this.height = rect.height || 500;

        this.canvas.width = Math.round(this.width * this.dpr);
        this.canvas.height = Math.round(this.height * this.dpr);

        if (this.ctx) {
            this.ctx.setTransform(1, 0, 0, 1, 0, 0);
            this.ctx.scale(this.dpr, this.dpr);
        }

        this.requestRender();
    }

    _bindChartEvents() {
        if (this.chart && typeof this.chart.subscribeVisibleRangeChanged === 'function') {
            this.chart.subscribeVisibleRangeChanged(() => this.requestRender());
        }
        if (this.chart && typeof this.chart.subscribeCandleUpdate === 'function') {
            this.chart.subscribeCandleUpdate(() => this.requestRender());
        }
    }

    _bindHitTesting() {
        if (!this.options.enableHitTesting) return;

        // Container-level click delegation: respects chart panning while capturing clicks
        const clickTarget = this.container;
        if (clickTarget && typeof clickTarget.addEventListener === 'function') {
            this._clickHandler = (event) => {
                const rect = this.container.getBoundingClientRect();
                const x = event.clientX - rect.left;
                const y = event.clientY - rect.top;

                const hit = this.hitTest(x, y);
                if (hit) {
                    this._dispatchPatternClicked(hit);
                }
            };
            clickTarget.addEventListener('click', this._clickHandler);
        }
    }

    hitTest(x, y) {
        // Iterate in reverse (top-rendered layers tested first)
        for (let i = this.hitTestRegions.length - 1; i >= 0; i--) {
            const region = this.hitTestRegions[i];
            const b = region.bounds;
            if (!b) continue;

            const padding = region.padding || 4;
            if (x >= (b.x1 - padding) && x <= (b.x2 + padding) &&
                y >= (b.y1 - padding) && y <= (b.y2 + padding)) {
                return region;
            }
        }
        return null;
    }

    _dispatchPatternClicked(hit) {
        const detail = {
            pattern_type: hit.pattern_type || hit.type,
            symbol: this.smcData.symbol,
            timeframe: this.smcData.timeframe,
            price: Number(hit.price || 0),
            timestamp: Number(hit.timestamp || hit.time || Math.floor(Date.now() / 1000)),
            metadata: Object.assign({}, hit.data || {}, {
                bounds: hit.bounds,
                description: hit.description || hit.label
            })
        };

        // 1. Dispatch custom DOM event on window and canvas
        if (typeof window !== 'undefined' && typeof window.CustomEvent === 'function') {
            const evt = new CustomEvent('jarvis:smc:pattern_clicked', {
                detail: detail,
                bubbles: true,
                cancelable: true
            });
            window.dispatchEvent(evt);
            if (this.canvas) {
                this.canvas.dispatchEvent(evt);
            }
        }

        // 2. Notify direct subscribers
        for (const cb of this.patternClickedCallbacks) {
            try {
                cb(detail);
            } catch (e) {
                console.error('Error in SMC patternClickedCallback:', e);
            }
        }

        return detail;
    }

    subscribePatternClick(callback) {
        if (typeof callback === 'function') {
            this.patternClickedCallbacks.push(callback);
        }
        return () => {
            this.patternClickedCallbacks = this.patternClickedCallbacks.filter(fn => fn !== callback);
        };
    }

    onPatternClick(callback) {
        return this.subscribePatternClick(callback);
    }

    updateSMCData(newData) {
        if (!newData) return;
        this.smcData = Object.assign({}, this.smcData, newData);
        this.requestRender();
    }

    updateSMC(newData) {
        return this.updateSMCData(newData);
    }

    setSymbol(newSymbol) {
        if (!newSymbol) return;
        this.smcData.symbol = newSymbol.toUpperCase();
        this.requestRender();
    }

    setTimeframe(newTf) {
        if (!newTf) return;
        this.smcData.timeframe = newTf.toUpperCase();
        this.requestRender();
    }

    setLayerVisibility(layerName, isVisible) {
        if (this.layers.hasOwnProperty(layerName)) {
            this.layers[layerName] = Boolean(isVisible);
            this.requestRender();
        }
    }

    toggleLayer(layerName) {
        if (this.layers.hasOwnProperty(layerName)) {
            this.layers[layerName] = !this.layers[layerName];
            this.requestRender();
            return this.layers[layerName];
        }
        return false;
    }

    setGlobalOpacity(opacity) {
        this.globalOpacity = Math.max(0.05, Math.min(1.0, Number(opacity) || 0.85));
        this.requestRender();
    }

    requestRender() {
        if (!this.renderPending) {
            this.renderPending = true;
            const requestAnim = typeof requestAnimationFrame !== 'undefined' ? requestAnimationFrame : (cb => setTimeout(cb, 16));
            requestAnim(() => {
                this.render();
                this.renderPending = false;
            });
        }
    }

    render() {
        if (!this.ctx || !this.width || !this.height || !this.chart) return;

        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;

        // Clear hit-test index for new frame
        this.hitTestRegions = [];

        // Clear transparent canvas
        ctx.clearRect(0, 0, w, h);

        ctx.save();
        ctx.globalAlpha = this.globalOpacity;

        // Layer 1: Interbank IPDA Session Killzones (Background Shading)
        if (this.layers.killzones) {
            this._renderKillzones(ctx, w, h);
        }

        // Layer 2: Visible-Range Volume Profile (VPVR) & 70% Value Area
        if (this.layers.vpvr) {
            this._renderVPVR(ctx, w, h);
        }

        // Layer 3: Multi-Band Anchored VWAP (±1σ, ±2σ, ±3σ bands)
        if (this.layers.vwap) {
            this._renderAnchoredVWAP(ctx, w, h);
        }

        // Layer 4: Fair Value Gaps (FVG) with 50% CE Lines
        if (this.layers.fvg) {
            this._renderFVGs(ctx, w, h);
        }

        // Layer 5: Institutional Order Blocks (OB) with TAPS counters
        if (this.layers.ob) {
            this._renderOrderBlocks(ctx, w, h);
        }

        // Layer 6: Change of Character (CHoCH) & Market Structure Breaks (BOS)
        if (this.layers.chochBos) {
            this._renderCHoCHandBOS(ctx, w, h);
        }

        // Layer 7: Optimal Trade Entry (OTE) Fibonacci Grids
        if (this.layers.ote) {
            this._renderOTEGrid(ctx, w, h);
        }

        // Layer 8: Liquidity Sweeps & Stop-Hunt Markers
        if (this.layers.sweeps) {
            this._renderSweeps(ctx, w, h);
        }

        // Layer 9: Cumulative Volume Delta (CVD) Absorption Divergence Waves
        if (this.layers.cvdWaves) {
            this._renderCVDWaves(ctx, w, h);
        }

        // Layer 10: RSI Multi-Timeframe Divergence Rays
        if (this.layers.rsiDiv) {
            this._renderRSIDivergences(ctx, w, h);
        }

        ctx.restore();
    }

    /* -------------------------------------------------------------
     * LAYER 1: Interbank IPDA Session Killzones
     * ------------------------------------------------------------- */
    _renderKillzones(ctx, w, h) {
        const range = this.chart.getVisibleRange ? this.chart.getVisibleRange() : { from: null, to: null };

        const killzoneDefs = [
            { name: 'ASIAN', startH: 0, endH: 6, color: 'rgba(148, 163, 184, 0.04)', stroke: 'rgba(148, 163, 184, 0.18)', label: 'ASIAN RANGE' },
            { name: 'LONDON', startH: 7, endH: 10, color: 'rgba(0, 242, 254, 0.07)', stroke: 'rgba(0, 242, 254, 0.30)', label: 'LONDON OPEN' },
            { name: 'NY_AM', startH: 12, endH: 15, color: 'rgba(245, 158, 11, 0.07)', stroke: 'rgba(245, 158, 11, 0.30)', label: 'NY AM DISPLACEMENT' },
            { name: 'NY_PM', startH: 18, endH: 20, color: 'rgba(168, 85, 247, 0.07)', stroke: 'rgba(168, 85, 247, 0.30)', label: 'NY PM SILVER BULLET' }
        ];

        const SECONDS_PER_DAY = 86400;
        let startDay = 0;
        let endDay = 0;

        if (range.from && range.to) {
            startDay = Math.floor(range.from / SECONDS_PER_DAY);
            endDay = Math.ceil(range.to / SECONDS_PER_DAY);
        } else {
            const nowSec = Math.floor(Date.now() / 1000);
            startDay = Math.floor(nowSec / SECONDS_PER_DAY) - 3;
            endDay = Math.floor(nowSec / SECONDS_PER_DAY) + 1;
        }

        for (let day = startDay; day <= endDay; day++) {
            const dayBase = day * SECONDS_PER_DAY;

            for (const kz of killzoneDefs) {
                const tStart = dayBase + (kz.startH * 3600);
                const tEnd = dayBase + (kz.endH * 3600);

                const xStart = this.chart.timeToCoordinate(tStart);
                const xEnd = this.chart.timeToCoordinate(tEnd);

                if (xStart === null || xEnd === null) continue;
                if (xEnd < 0 || xStart > w) continue;

                const colW = Math.max(xEnd - xStart, 8);

                ctx.fillStyle = kz.color;
                ctx.fillRect(xStart, 0, colW, h);

                ctx.strokeStyle = kz.stroke;
                ctx.lineWidth = 1;
                ctx.setLineDash([2, 3]);
                ctx.beginPath();
                ctx.moveTo(xStart, 0);
                ctx.lineTo(xStart, h);
                ctx.moveTo(xEnd, 0);
                ctx.lineTo(xEnd, h);
                ctx.stroke();
                ctx.setLineDash([]);

                if (colW > 35) {
                    ctx.font = '8px "JetBrains Mono", monospace';
                    ctx.fillStyle = kz.stroke;
                    ctx.textAlign = 'left';
                    ctx.fillText(kz.label, xStart + 4, 14);
                }
            }
        }
    }

    /* -------------------------------------------------------------
     * LAYER 2: Visible-Range Volume Profile (VPVR) & 70% Value Area
     * ------------------------------------------------------------- */
    _renderVPVR(ctx, w, h) {
        let profile = this.smcData.vpvr;
        if (!profile && this.chart && this.chart.candles && this.chart.candles.length > 0) {
            profile = this.computeVPVR(this.chart.candles, this.options.vpvrBins, this.options.vpvrValueArea);
        }
        if (!profile || !profile.bins || profile.bins.length === 0) return;

        const maxVol = profile.max_volume || Math.max(...profile.bins.map(b => b.volume || 0), 1);
        const rightEdgeX = w - 65;
        const profileWidth = Math.min(this.options.vpvrWidth || 140, w * 0.25);

        // 1. Draw Volume Profile Bars
        for (const bin of profile.bins) {
            const yTop = this.chart.priceToCoordinate(bin.price_high);
            const yBottom = this.chart.priceToCoordinate(bin.price_low);
            if (yTop === null || yBottom === null) continue;

            const barY = Math.min(yTop, yBottom);
            const barH = Math.max(Math.abs(yBottom - yTop), 1);
            const barLen = (bin.volume / maxVol) * profileWidth;
            const barX = rightEdgeX - barLen;

            const isValueArea = Boolean(bin.in_va);
            ctx.fillStyle = isValueArea ? 'rgba(0, 242, 254, 0.28)' : 'rgba(100, 116, 139, 0.16)';
            ctx.fillRect(barX, barY, barLen, barH);

            ctx.strokeStyle = isValueArea ? 'rgba(0, 242, 254, 0.50)' : 'rgba(100, 116, 139, 0.30)';
            ctx.lineWidth = 0.5;
            ctx.strokeRect(barX, barY, barLen, barH);

            if (bin.is_poc) {
                this.hitTestRegions.push({
                    type: 'VOLUME_PROFILE_POC',
                    pattern_type: 'VOLUME_PROFILE_POC',
                    bounds: { x1: rightEdgeX - profileWidth - 20, y1: barY - 6, x2: rightEdgeX, y2: barY + barH + 6 },
                    price: profile.poc,
                    data: { poc: profile.poc, vah: profile.vah, val: profile.val, volume: bin.volume },
                    description: `VPVR Point of Control (${profile.poc.toFixed(2)})`
                });
            }
        }

        // 2. Point of Control (POC) Golden Line
        const yPoc = this.chart.priceToCoordinate(profile.poc);
        if (yPoc !== null) {
            ctx.strokeStyle = '#F59E0B';
            ctx.lineWidth = 2;
            ctx.shadowColor = 'rgba(245, 158, 11, 0.70)';
            ctx.shadowBlur = 6;
            ctx.beginPath();
            ctx.moveTo(30, yPoc);
            ctx.lineTo(rightEdgeX, yPoc);
            ctx.stroke();
            ctx.shadowBlur = 0;

            const pocText = `★ POC ${profile.poc.toFixed(2)}`;
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            const tw = ctx.measureText(pocText).width;
            ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
            ctx.fillRect(rightEdgeX - tw - 12, yPoc - 8, tw + 8, 15);
            ctx.strokeStyle = '#F59E0B';
            ctx.strokeRect(rightEdgeX - tw - 12, yPoc - 8, tw + 8, 15);
            ctx.fillStyle = '#F59E0B';
            ctx.fillText(pocText, rightEdgeX - tw - 8, yPoc + 3);
        }

        // 3. Value Area High (VAH) & Value Area Low (VAL)
        if (profile.vah) {
            const yVah = this.chart.priceToCoordinate(profile.vah);
            if (yVah !== null) {
                ctx.strokeStyle = 'rgba(0, 242, 254, 0.65)';
                ctx.lineWidth = 1.2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(rightEdgeX - profileWidth, yVah);
                ctx.lineTo(rightEdgeX, yVah);
                ctx.stroke();
                ctx.setLineDash([]);

                const vahText = `VAH ${profile.vah.toFixed(2)}`;
                ctx.font = '9px "JetBrains Mono", monospace';
                ctx.fillStyle = '#00F2FE';
                ctx.fillText(vahText, rightEdgeX - 60, yVah - 3);
            }
        }

        if (profile.val) {
            const yVal = this.chart.priceToCoordinate(profile.val);
            if (yVal !== null) {
                ctx.strokeStyle = 'rgba(0, 242, 254, 0.65)';
                ctx.lineWidth = 1.2;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(rightEdgeX - profileWidth, yVal);
                ctx.lineTo(rightEdgeX, yVal);
                ctx.stroke();
                ctx.setLineDash([]);

                const valText = `VAL ${profile.val.toFixed(2)}`;
                ctx.font = '9px "JetBrains Mono", monospace';
                ctx.fillStyle = '#00F2FE';
                ctx.fillText(valText, rightEdgeX - 60, yVal + 11);
            }
        }
    }

    /* -------------------------------------------------------------
     * LAYER 3: Multi-Band Anchored VWAP (±1σ, ±2σ, ±3σ)
     * ------------------------------------------------------------- */
    _renderAnchoredVWAP(ctx, w, h) {
        let vwapData = this.smcData.anchored_vwap;
        if (!vwapData && this.chart && this.chart.candles && this.chart.candles.length > 5) {
            const anchorTime = this.chart.candles[0].time;
            vwapData = this.computeAnchoredVWAP(this.chart.candles, anchorTime);
        }
        if (!vwapData || !vwapData.points || vwapData.points.length < 2) return;

        const points = vwapData.points;
        const coords = [];

        for (const pt of points) {
            const x = this.chart.timeToCoordinate(pt.time);
            if (x === null) continue;
            const yVwap = this.chart.priceToCoordinate(pt.vwap);
            const yU1 = this.chart.priceToCoordinate(pt.upper1);
            const yL1 = this.chart.priceToCoordinate(pt.lower1);
            const yU2 = this.chart.priceToCoordinate(pt.upper2);
            const yL2 = this.chart.priceToCoordinate(pt.lower2);
            const yU3 = this.chart.priceToCoordinate(pt.upper3);
            const yL3 = this.chart.priceToCoordinate(pt.lower3);

            if (yVwap !== null) {
                coords.push({ x, yVwap, yU1, yL1, yU2, yL2, yU3, yL3, pt });
            }
        }

        if (coords.length < 2) return;

        // 1. Shaded Fair-Value Ribbon between ±1σ and ±2σ
        ctx.fillStyle = 'rgba(0, 242, 254, 0.05)';
        ctx.beginPath();
        for (let i = 0; i < coords.length; i++) {
            const c = coords[i];
            if (c.yU2 !== null) {
                if (i === 0) ctx.moveTo(c.x, c.yU2);
                else ctx.lineTo(c.x, c.yU2);
            }
        }
        for (let i = coords.length - 1; i >= 0; i--) {
            const c = coords[i];
            if (c.yL2 !== null) ctx.lineTo(c.x, c.yL2);
        }
        ctx.closePath();
        ctx.fill();

        // 2. Draw Central VWAP Curve (Solid Gold)
        ctx.strokeStyle = '#FFD700';
        ctx.lineWidth = 2.0;
        ctx.shadowColor = 'rgba(255, 215, 0, 0.50)';
        ctx.shadowBlur = 5;
        ctx.beginPath();
        for (let i = 0; i < coords.length; i++) {
            const c = coords[i];
            if (i === 0) ctx.moveTo(c.x, c.yVwap);
            else ctx.lineTo(c.x, c.yVwap);
        }
        ctx.stroke();
        ctx.shadowBlur = 0;

        // 3. Draw ±1σ Bands (Soft Cyan Dashed)
        ctx.strokeStyle = 'rgba(0, 242, 254, 0.50)';
        ctx.lineWidth = 1.0;
        ctx.setLineDash([3, 3]);
        this._drawLinePath(ctx, coords, 'yU1');
        this._drawLinePath(ctx, coords, 'yL1');

        // 4. Draw ±2σ Bands (Cyan Solid)
        ctx.strokeStyle = 'rgba(0, 242, 254, 0.85)';
        ctx.lineWidth = 1.4;
        ctx.setLineDash([]);
        this._drawLinePath(ctx, coords, 'yU2');
        this._drawLinePath(ctx, coords, 'yL2');

        // 5. Draw ±3σ Bands (Magenta Reversal Boundary)
        ctx.strokeStyle = 'rgba(255, 0, 128, 0.90)';
        ctx.lineWidth = 1.6;
        this._drawLinePath(ctx, coords, 'yU3');
        this._drawLinePath(ctx, coords, 'yL3');

        // 6. Last-Point Pills & Hit Region
        const last = coords[coords.length - 1];
        if (last && last.x < w - 40) {
            const tag = `VWAP ${last.pt.vwap.toFixed(2)}`;
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            ctx.fillStyle = '#FFD700';
            ctx.fillText(tag, last.x + 4, last.yVwap + 3);

            this.hitTestRegions.push({
                type: 'ANCHORED_VWAP',
                pattern_type: 'ANCHORED_VWAP',
                bounds: { x1: coords[0].x, y1: Math.min(...coords.map(c => c.yU2 || c.yVwap)), x2: last.x + 40, y2: Math.max(...coords.map(c => c.yL2 || c.yVwap)) },
                price: last.pt.vwap,
                time: last.pt.time,
                data: last.pt,
                description: `Multi-Band Anchored VWAP (±1σ, ±2σ, ±3σ)`
            });
        }
    }

    _drawLinePath(ctx, coords, key) {
        ctx.beginPath();
        let started = false;
        for (const c of coords) {
            if (c[key] !== null) {
                if (!started) {
                    ctx.moveTo(c.x, c[key]);
                    started = true;
                } else {
                    ctx.lineTo(c.x, c[key]);
                }
            }
        }
        ctx.stroke();
    }

    /* -------------------------------------------------------------
     * LAYER 4: Fair Value Gaps (FVG) with 50% CE Lines
     * ------------------------------------------------------------- */
    _renderFVGs(ctx, w, h) {
        const fvgs = this.smcData.fvgs || [];
        const rightEdgeX = w - 65;

        for (const fvg of fvgs) {
            const yTop = this.chart.priceToCoordinate(fvg.top);
            const yBottom = this.chart.priceToCoordinate(fvg.bottom);
            const cePrice = fvg.ce ?? ((fvg.top + fvg.bottom) / 2.0);
            const yCe = this.chart.priceToCoordinate(cePrice);

            if (yTop === null || yBottom === null) continue;

            const rawXStart = this.chart.timeToCoordinate(fvg.time);
            if (rawXStart === null) continue;
            const xStart = Math.max(0, rawXStart);

            let xEnd = rightEdgeX;
            if (fvg.mitigated && fvg.mitigation_time) {
                const rawXEnd = this.chart.timeToCoordinate(fvg.mitigation_time);
                if (rawXEnd !== null) xEnd = rawXEnd;
            }

            if (xEnd < 0 || xStart > w) continue;

            const boxY = Math.min(yTop, yBottom);
            const boxHeight = Math.max(Math.abs(yBottom - yTop), 2);
            const boxWidth = Math.max(xEnd - xStart, 20);

            const isBullish = String(fvg.type || '').toUpperCase().includes('BULLISH');
            const baseColor = isBullish ? '16, 185, 129' : '239, 68, 68';

            // 1. Shaded Box Fill
            ctx.fillStyle = fvg.mitigated ? `rgba(${baseColor}, 0.04)` : `rgba(${baseColor}, 0.14)`;
            ctx.fillRect(xStart, boxY, boxWidth, boxHeight);

            // 2. Box Border
            ctx.strokeStyle = fvg.mitigated ? `rgba(${baseColor}, 0.20)` : `rgba(${baseColor}, 0.55)`;
            ctx.lineWidth = 1;
            ctx.setLineDash(fvg.mitigated ? [2, 2] : []);
            ctx.strokeRect(xStart, boxY, boxWidth, boxHeight);
            ctx.setLineDash([]);

            // 3. 50% Consequent Encroachment (CE) Dashed Midline
            if (this.layers.fvgCe && yCe !== null) {
                ctx.strokeStyle = fvg.mitigated ? 'rgba(245, 158, 11, 0.35)' : 'rgba(245, 158, 11, 0.90)';
                ctx.lineWidth = 1.5;
                ctx.setLineDash([4, 4]);
                ctx.beginPath();
                ctx.moveTo(xStart, yCe);
                ctx.lineTo(xStart + boxWidth, yCe);
                ctx.stroke();
                ctx.setLineDash([]);

                if (boxWidth > 70) {
                    const ceText = `50% CE ${cePrice.toFixed(2)}`;
                    ctx.font = '9px "JetBrains Mono", monospace';
                    const textW = ctx.measureText(ceText).width;
                    const pillX = xStart + boxWidth - textW - 10;
                    const pillY = yCe - 7;

                    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
                    ctx.fillRect(pillX, pillY, textW + 6, 13);
                    ctx.strokeStyle = 'rgba(245, 158, 11, 0.60)';
                    ctx.lineWidth = 0.8;
                    ctx.strokeRect(pillX, pillY, textW + 6, 13);

                    ctx.fillStyle = '#F59E0B';
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(ceText, pillX + 3, pillY + 6.5);
                }
            }

            // 4. FVG Tag (Top-left)
            if (boxWidth > 45 && boxHeight > 14) {
                const tag = isBullish ? '+FVG' : '-FVG';
                ctx.font = 'bold 9px "JetBrains Mono", monospace';
                ctx.fillStyle = isBullish ? '#10B981' : '#EF4444';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                ctx.fillText(tag, xStart + 4, boxY + 3);
            }

            // 5. Register Hit Test Region
            this.hitTestRegions.push({
                type: isBullish ? 'BULLISH_FVG' : 'BEARISH_FVG',
                pattern_type: isBullish ? 'BULLISH_FVG' : 'BEARISH_FVG',
                bounds: { x1: xStart, y1: boxY, x2: xStart + boxWidth, y2: boxY + boxHeight },
                price: cePrice,
                time: fvg.time,
                data: fvg,
                description: `${isBullish ? 'Bullish' : 'Bearish'} Fair Value Gap with 50% CE (${cePrice.toFixed(2)})`
            });
        }
    }

    /* -------------------------------------------------------------
     * LAYER 5: Institutional Order Blocks (OB) with TAPS counters
     * ------------------------------------------------------------- */
    _renderOrderBlocks(ctx, w, h) {
        const obs = this.smcData.order_blocks || [];
        const rightEdgeX = w - 65;

        for (const ob of obs) {
            const yTop = this.chart.priceToCoordinate(ob.top);
            const yBottom = this.chart.priceToCoordinate(ob.bottom);

            if (yTop === null || yBottom === null) continue;

            const rawXStart = this.chart.timeToCoordinate(ob.time);
            if (rawXStart === null) continue;
            const xStart = Math.max(0, rawXStart);

            let xEnd = rightEdgeX;
            if (ob.mitigated && ob.mitigation_time) {
                const rawXEnd = this.chart.timeToCoordinate(ob.mitigation_time);
                if (rawXEnd !== null) xEnd = rawXEnd;
            }

            if (xEnd < 0 || xStart > w) continue;

            const boxY = Math.min(yTop, yBottom);
            const boxHeight = Math.max(Math.abs(yBottom - yTop), 3);
            const boxWidth = Math.max(xEnd - xStart, 25);

            const isDemand = String(ob.type || '').toUpperCase().includes('BULLISH');
            const baseColor = isDemand ? '16, 185, 129' : '239, 68, 68';
            const solidColor = isDemand ? '#10B981' : '#EF4444';

            // 1. Order Block Background Fill
            ctx.fillStyle = ob.mitigated ? `rgba(${baseColor}, 0.05)` : `rgba(${baseColor}, 0.16)`;
            ctx.fillRect(xStart, boxY, boxWidth, boxHeight);

            // 2. Solid 4px Left Accent Anchor Bar
            ctx.fillStyle = solidColor;
            ctx.fillRect(xStart, boxY, 4, boxHeight);

            // 3. Border Outline
            ctx.strokeStyle = `rgba(${baseColor}, ${ob.mitigated ? 0.25 : 0.65})`;
            ctx.lineWidth = 1;
            ctx.setLineDash(ob.mitigated ? [3, 3] : []);
            ctx.strokeRect(xStart, boxY, boxWidth, boxHeight);
            ctx.setLineDash([]);

            // 4. Touch Counter & Tag Pill
            const touchCount = ob.touched ?? ob.touch_count ?? 0;
            const touchText = ob.mitigated ? `[MITIGATED]` : `${isDemand ? 'DEMAND' : 'SUPPLY'} OB (${touchCount} TAPS)`;
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            const labelW = ctx.measureText(touchText).width;

            const pillX = xStart + 8;
            const pillY = boxY + 3;

            if (pillY + 13 <= boxY + boxHeight || boxHeight > 16) {
                ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
                ctx.fillRect(pillX, pillY, labelW + 6, 13);
                ctx.strokeStyle = `rgba(${baseColor}, 0.60)`;
                ctx.lineWidth = 0.8;
                ctx.strokeRect(pillX, pillY, labelW + 6, 13);

                ctx.fillStyle = solidColor;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';
                ctx.fillText(touchText, pillX + 3, pillY + 6.5);
            }

            // 5. Register Hit Test Region
            this.hitTestRegions.push({
                type: isDemand ? 'BULLISH_ORDER_BLOCK' : 'BEARISH_ORDER_BLOCK',
                pattern_type: isDemand ? 'BULLISH_ORDER_BLOCK' : 'BEARISH_ORDER_BLOCK',
                bounds: { x1: xStart, y1: boxY, x2: xStart + boxWidth, y2: boxY + boxHeight },
                price: (ob.top + ob.bottom) / 2.0,
                time: ob.time,
                data: ob,
                description: `${isDemand ? 'Demand' : 'Supply'} Order Block (${touchCount} Taps)`
            });
        }
    }

    /* -------------------------------------------------------------
     * LAYER 6: Change of Character (CHoCH) & Break of Structure (BOS)
     * ------------------------------------------------------------- */
    _renderCHoCHandBOS(ctx, w, h) {
        let items = this.smcData.choch_bos;
        if ((!items || items.length === 0) && this.chart && this.chart.candles && this.chart.candles.length > 10) {
            items = this.computeCHoCHandBOS(this.chart.candles);
        }
        if (!items || items.length === 0) return;

        const rightEdgeX = w - 65;

        for (const item of items) {
            const yPrice = this.chart.priceToCoordinate(item.price);
            if (yPrice === null) continue;

            const xStart = this.chart.timeToCoordinate(item.time_start);
            const xBreak = this.chart.timeToCoordinate(item.time_break);
            if (xStart === null || xBreak === null) continue;

            const isBullish = String(item.bias || item.type || '').toUpperCase().includes('BULLISH');
            const isChoch = String(item.type || '').toUpperCase().includes('CHOCH');
            const color = isBullish ? '#10B981' : '#EF4444';

            // 1. Horizontal Breakout Line
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.5;
            ctx.setLineDash(item.mitigated ? [2, 2] : []);
            ctx.beginPath();
            ctx.moveTo(xStart, yPrice);
            ctx.lineTo(xBreak, yPrice);
            ctx.stroke();

            // Dotted continuation to right if unmitigated
            if (!item.mitigated) {
                ctx.setLineDash([3, 4]);
                ctx.strokeStyle = `rgba(${isBullish ? '16, 185, 129' : '239, 68, 68'}, 0.40)`;
                ctx.beginPath();
                ctx.moveTo(xBreak, yPrice);
                ctx.lineTo(rightEdgeX, yPrice);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // 2. Badge Tag at Breakout Candle
            const label = isChoch
                ? (isBullish ? '▲ CHoCH' : '▼ CHoCH')
                : (isBullish ? '▲ BOS' : '▼ BOS');

            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            const tw = ctx.measureText(label).width;
            const badgeX = xBreak - (tw / 2);
            const badgeY = isBullish ? yPrice - 14 : yPrice + 2;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            ctx.fillRect(badgeX - 4, badgeY, tw + 8, 14);
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.strokeRect(badgeX - 4, badgeY, tw + 8, 14);

            ctx.fillStyle = color;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.fillText(label, badgeX, badgeY + 2);

            // 3. Register Hit Region
            this.hitTestRegions.push({
                type: isChoch ? (isBullish ? 'BULLISH_CHOCH' : 'BEARISH_CHOCH') : (isBullish ? 'BULLISH_BOS' : 'BEARISH_BOS'),
                pattern_type: isChoch ? 'CHOCH' : 'BOS',
                bounds: { x1: Math.min(xStart, badgeX), y1: Math.min(yPrice - 16, badgeY), x2: Math.max(xBreak + 20, badgeX + tw + 10), y2: Math.max(yPrice + 16, badgeY + 16) },
                price: item.price,
                time: item.time_break,
                data: item,
                description: `${isBullish ? 'Bullish' : 'Bearish'} ${isChoch ? 'Change of Character (CHoCH)' : 'Break of Structure (BOS)'} at ${item.price.toFixed(2)}`
            });
        }
    }

    /* -------------------------------------------------------------
     * LAYER 7: Optimal Trade Entry (OTE) Fibonacci Grids
     * ------------------------------------------------------------- */
    _renderOTEGrid(ctx, w, h) {
        const ote = this.smcData.ote;
        if (!ote || !ote.levels) return;

        const levels = ote.levels;
        const yEq = this.chart.priceToCoordinate(levels.eq);
        const y618 = this.chart.priceToCoordinate(levels.fib_618);
        const y705 = this.chart.priceToCoordinate(levels.sweet_spot_705);
        const y786 = this.chart.priceToCoordinate(levels.fib_786);

        if (y618 === null || y786 === null || y705 === null) return;

        const xStart = 30;
        const xEnd = w - 70;

        // 1. Golden Pocket Ribbon (61.8% to 78.6%)
        const ribbonTop = Math.min(y618, y786);
        const ribbonHeight = Math.abs(y786 - y618);

        const gradient = ctx.createLinearGradient(0, ribbonTop, 0, ribbonTop + ribbonHeight);
        gradient.addColorStop(0, 'rgba(245, 158, 11, 0.08)');
        gradient.addColorStop(0.5, 'rgba(245, 158, 11, 0.24)');
        gradient.addColorStop(1, 'rgba(245, 158, 11, 0.08)');

        ctx.fillStyle = gradient;
        ctx.fillRect(xStart, ribbonTop, xEnd - xStart, ribbonHeight);

        // 2. 50% Equilibrium Line
        if (yEq !== null) {
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.50)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(xStart, yEq);
            ctx.lineTo(xEnd, yEq);
            ctx.stroke();
            ctx.setLineDash([]);
            this._drawOTELabel(ctx, `50.0% EQ (${levels.eq.toFixed(2)})`, xEnd - 130, yEq - 3, '#94A3B8');
        }

        // 3. 61.8% Fibonacci Boundary Line
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.75)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.moveTo(xStart, y618);
        ctx.lineTo(xEnd, y618);
        ctx.stroke();
        ctx.setLineDash([]);
        this._drawOTELabel(ctx, `61.8% OTE (${levels.fib_618.toFixed(2)})`, xEnd - 130, y618 - 3, '#3B82F6');

        // 4. 78.6% Fibonacci Boundary Line
        ctx.strokeStyle = 'rgba(236, 72, 153, 0.75)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.moveTo(xStart, y786);
        ctx.lineTo(xEnd, y786);
        ctx.stroke();
        ctx.setLineDash([]);
        this._drawOTELabel(ctx, `78.6% OTE (${levels.fib_786.toFixed(2)})`, xEnd - 130, y786 - 3, '#EC4899');

        // 5. 70.5% Institutional Sweet Spot Golden Line
        ctx.strokeStyle = '#F59E0B';
        ctx.lineWidth = 2;
        ctx.shadowColor = 'rgba(245, 158, 11, 0.60)';
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.moveTo(xStart, y705);
        ctx.lineTo(xEnd, y705);
        ctx.stroke();
        ctx.shadowBlur = 0;

        const sweetSpotText = `★ 70.5% SWEET SPOT (${levels.sweet_spot_705.toFixed(2)})`;
        this._drawOTELabel(ctx, sweetSpotText, xEnd - 180, y705 - 4, '#F59E0B', true);

        // Register Hit Region
        this.hitTestRegions.push({
            type: 'OTE_FIBONACCI',
            pattern_type: 'OTE_FIBONACCI',
            bounds: { x1: xStart, y1: ribbonTop, x2: xEnd, y2: ribbonTop + ribbonHeight },
            price: levels.sweet_spot_705,
            data: levels,
            description: `Optimal Trade Entry (OTE) 70.5% Golden Pocket (${levels.sweet_spot_705.toFixed(2)})`
        });
    }

    _drawOTELabel(ctx, text, x, y, color, isProminent = false) {
        ctx.font = isProminent ? 'bold 10px "JetBrains Mono", monospace' : '9px "JetBrains Mono", monospace';
        const textW = ctx.measureText(text).width;

        ctx.fillStyle = 'rgba(11, 15, 25, 0.90)';
        ctx.fillRect(x - 4, y - 9, textW + 8, 14);
        ctx.strokeStyle = color;
        ctx.lineWidth = isProminent ? 1.5 : 0.8;
        ctx.strokeRect(x - 4, y - 9, textW + 8, 14);

        ctx.fillStyle = color;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, x, y - 2);
    }

    /* -------------------------------------------------------------
     * LAYER 8: Liquidity Sweeps & Stop-Hunt Markers
     * ------------------------------------------------------------- */
    _renderSweeps(ctx, w, h) {
        const sweeps = this.smcData.sweeps || [];

        for (const sw of sweeps) {
            const yLevel = this.chart.priceToCoordinate(sw.swept_level ?? sw.price);
            const yWick = this.chart.priceToCoordinate(sw.rejection_wick ?? sw.price);
            const xPos = this.chart.timeToCoordinate(sw.time) || (w - 120);

            if (yLevel === null || xPos === null || xPos < -50 || xPos > w + 50) continue;

            const isBearish = String(sw.type).toUpperCase().includes('BEARISH') || String(sw.type).toUpperCase().includes('EQH');
            const neonColor = '#00F2FE';

            // 1. Horizontal Dotted Liquidity Line
            ctx.strokeStyle = 'rgba(0, 242, 254, 0.70)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(xPos - 50, yLevel);
            ctx.lineTo(xPos + 50, yLevel);
            ctx.stroke();
            ctx.setLineDash([]);

            // 2. Rejection Wick Range Box
            if (yWick !== null) {
                const wickTop = Math.min(yLevel, yWick);
                const wickH = Math.max(Math.abs(yWick - yLevel), 4);
                ctx.fillStyle = isBearish ? 'rgba(239, 68, 68, 0.35)' : 'rgba(16, 185, 129, 0.35)';
                ctx.fillRect(xPos - 4, wickTop, 8, wickH);
            }

            // 3. Lightning Icon
            const markerY = isBearish ? (yWick !== null ? yWick - 14 : yLevel - 14) : (yWick !== null ? yWick + 14 : yLevel + 14);
            this._drawLightningIcon(ctx, xPos, markerY, neonColor);

            // 4. Sweep HUD Badge
            const badgeText = isBearish ? '⚡ EQH SWEEP (BUY STOPS)' : '⚡ EQL SWEEP (SELL STOPS)';
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            const textW = ctx.measureText(badgeText).width;
            const badgeX = xPos - (textW / 2);
            const badgeY = isBearish ? markerY - 14 : markerY + 16;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.92)';
            ctx.fillRect(badgeX - 4, badgeY - 8, textW + 8, 14);
            ctx.strokeStyle = neonColor;
            ctx.lineWidth = 1;
            ctx.strokeRect(badgeX - 4, badgeY - 8, textW + 8, 14);

            ctx.fillStyle = neonColor;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(badgeText, badgeX, badgeY - 1);

            // 5. Register Hit Region
            this.hitTestRegions.push({
                type: isBearish ? 'EQH_SWEEP' : 'EQL_SWEEP',
                pattern_type: 'LIQUIDITY_SWEEP',
                bounds: { x1: badgeX - 6, y1: Math.min(badgeY - 10, markerY - 8), x2: badgeX + textW + 6, y2: Math.max(badgeY + 16, markerY + 8) },
                price: sw.swept_level ?? sw.price,
                time: sw.time,
                data: sw,
                description: `${isBearish ? 'Equal Highs (EQH) Buy-Side' : 'Equal Lows (EQL) Sell-Side'} Liquidity Sweep`
            });
        }
    }

    _drawLightningIcon(ctx, x, y, color) {
        ctx.save();
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.moveTo(x + 1, y - 7);
        ctx.lineTo(x - 4, y + 1);
        ctx.lineTo(x - 1, y + 1);
        ctx.lineTo(x - 2, y + 7);
        ctx.lineTo(x + 4, y - 1);
        ctx.lineTo(x + 1, y - 1);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    /* -------------------------------------------------------------
     * LAYER 9: Cumulative Volume Delta (CVD) Absorption Divergence Waves
     * ------------------------------------------------------------- */
    _renderCVDWaves(ctx, w, h) {
        const waves = this.smcData.cvd_waves || [];

        for (const wave of waves) {
            const x1 = this.chart.timeToCoordinate(wave.time1);
            const y1 = this.chart.priceToCoordinate(wave.price1);
            const x2 = this.chart.timeToCoordinate(wave.time2);
            const y2 = this.chart.priceToCoordinate(wave.price2);

            if (x1 === null || y1 === null || x2 === null || y2 === null) continue;

            const isBullish = String(wave.type || '').toUpperCase().includes('BULLISH');
            const waveColor = isBullish ? '#00F2FE' : '#EF4444';

            // 1. Glowing Connecting Wave Ray
            ctx.save();
            ctx.strokeStyle = waveColor;
            ctx.lineWidth = 2.0;
            ctx.shadowColor = waveColor;
            ctx.shadowBlur = 8;
            ctx.setLineDash([4, 2]);

            ctx.beginPath();
            ctx.moveTo(x1, y1);
            const cx = (x1 + x2) / 2;
            const cy = ((y1 + y2) / 2) + (isBullish ? 15 : -15);
            ctx.quadraticCurveTo(cx, cy, x2, y2);
            ctx.stroke();
            ctx.restore();

            // 2. Alert Badge at Pivot 2
            const badgeText = isBullish ? '⚡ CVD BULLISH ABSORPTION' : '⚡ CVD BEARISH ABSORPTION';
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            const tw = ctx.measureText(badgeText).width;
            const bx = x2 - (tw / 2);
            const by = isBullish ? y2 + 16 : y2 - 24;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.94)';
            ctx.fillRect(bx - 4, by, tw + 8, 14);
            ctx.strokeStyle = waveColor;
            ctx.lineWidth = 1;
            ctx.strokeRect(bx - 4, by, tw + 8, 14);

            ctx.fillStyle = waveColor;
            ctx.fillText(badgeText, bx, by + 10);

            // 3. Register Hit Region
            this.hitTestRegions.push({
                type: isBullish ? 'BULLISH_CVD_ABSORPTION' : 'BEARISH_CVD_ABSORPTION',
                pattern_type: 'CVD_ABSORPTION',
                bounds: { x1: Math.min(x1, bx - 6), y1: Math.min(y1, by), x2: Math.max(x2, bx + tw + 6), y2: Math.max(y2, by + 16) },
                price: wave.price2,
                time: wave.time2,
                data: wave,
                description: `${isBullish ? 'Bullish' : 'Bearish'} Cumulative Volume Delta (CVD) Absorption Divergence Wave`
            });
        }
    }

    /* -------------------------------------------------------------
     * LAYER 10: RSI Multi-Timeframe Divergence Rays
     * ------------------------------------------------------------- */
    _renderRSIDivergences(ctx, w, h) {
        const divs = this.smcData.rsi_divergences || [];

        for (const div of divs) {
            const x1 = this.chart.timeToCoordinate(div.time1);
            const y1 = this.chart.priceToCoordinate(div.price1);
            const x2 = this.chart.timeToCoordinate(div.time2);
            const y2 = this.chart.priceToCoordinate(div.price2);

            if (x1 === null || y1 === null || x2 === null || y2 === null) continue;

            const isBullish = String(div.type || '').toUpperCase().includes('BULLISH');
            const color = isBullish ? '#10B981' : '#F43F5E';

            // Divergence Ray
            ctx.strokeStyle = color;
            ctx.lineWidth = 1.8;
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.stroke();

            // Tag
            const label = isBullish ? '▲ RSI BULLISH DIV' : '▼ RSI BEARISH DIV';
            ctx.font = 'bold 9px "JetBrains Mono", monospace';
            const tw = ctx.measureText(label).width;
            const bx = x2 + 4;
            const by = y2 - 6;

            ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
            ctx.fillRect(bx, by, tw + 6, 12);
            ctx.strokeStyle = color;
            ctx.strokeRect(bx, by, tw + 6, 12);
            ctx.fillStyle = color;
            ctx.fillText(label, bx + 3, by + 9);

            this.hitTestRegions.push({
                type: isBullish ? 'REGULAR_BULLISH_RSI_DIV' : 'REGULAR_BEARISH_RSI_DIV',
                pattern_type: 'RSI_DIVERGENCE',
                bounds: { x1: Math.min(x1, x2), y1: Math.min(y1, y2) - 10, x2: Math.max(x1, x2 + tw + 10), y2: Math.max(y1, y2) + 10 },
                price: div.price2,
                time: div.time2,
                data: div,
                description: `RSI Divergence (${div.type})`
            });
        }
    }

    /* -------------------------------------------------------------
     * COMPUTATIONAL ALGORITHMS (Used when external data not passed)
     * ------------------------------------------------------------- */
    computeVPVR(candles, numBins = 60, vaPct = 0.70) {
        if (!candles || candles.length === 0) return null;

        let minPrice = Infinity;
        let maxPrice = -Infinity;
        let totalVol = 0;

        for (const c of candles) {
            if (c.low < minPrice) minPrice = c.low;
            if (c.high > maxPrice) maxPrice = c.high;
            totalVol += (c.volume || 1);
        }

        if (minPrice >= maxPrice || totalVol <= 0) return null;

        const binSize = (maxPrice - minPrice) / numBins;
        const bins = [];
        for (let i = 0; i < numBins; i++) {
            const pLow = minPrice + (i * binSize);
            const pHigh = pLow + binSize;
            bins.push({
                bin_index: i,
                price_low: pLow,
                price_high: pHigh,
                price_mid: (pLow + pHigh) / 2,
                volume: 0,
                in_va: false,
                is_poc: false
            });
        }

        // Distribute candle volume across price buckets
        for (const c of candles) {
            const cVol = c.volume || 1;
            const cLow = c.low;
            const cHigh = Math.max(c.high, cLow + 0.00001);

            for (const b of bins) {
                const overlapLow = Math.max(cLow, b.price_low);
                const overlapHigh = Math.min(cHigh, b.price_high);
                if (overlapHigh > overlapLow) {
                    const ratio = (overlapHigh - overlapLow) / (cHigh - cLow);
                    b.volume += (cVol * ratio);
                }
            }
        }

        // Find Point of Control (POC)
        let pocBin = bins[0];
        let maxVol = 0;
        let pocIndex = 0;
        for (let i = 0; i < bins.length; i++) {
            if (bins[i].volume > maxVol) {
                maxVol = bins[i].volume;
                pocBin = bins[i];
                pocIndex = i;
            }
        }
        pocBin.is_poc = true;

        // Compute 70% Value Area (VAH & VAL) expanding outward from POC
        const targetVol = totalVol * vaPct;
        let accumulatedVol = pocBin.volume;
        pocBin.in_va = true;

        let upIdx = pocIndex + 1;
        let downIdx = pocIndex - 1;

        while (accumulatedVol < targetVol && (upIdx < bins.length || downIdx >= 0)) {
            const upVol = (upIdx < bins.length) ? bins[upIdx].volume : -1;
            const downVol = (downIdx >= 0) ? bins[downIdx].volume : -1;

            if (upVol >= downVol && upIdx < bins.length) {
                accumulatedVol += upVol;
                bins[upIdx].in_va = true;
                upIdx++;
            } else if (downIdx >= 0) {
                accumulatedVol += downVol;
                bins[downIdx].in_va = true;
                downIdx--;
            } else {
                break;
            }
        }

        const vaBins = bins.filter(b => b.in_va);
        const val = vaBins.length > 0 ? vaBins[0].price_low : minPrice;
        const vah = vaBins.length > 0 ? vaBins[vaBins.length - 1].price_high : maxPrice;

        return {
            poc: pocBin.price_mid,
            vah: vah,
            val: val,
            max_volume: maxVol,
            total_volume: totalVol,
            bins: bins
        };
    }

    computeAnchoredVWAP(candles, anchorTime) {
        if (!candles || candles.length === 0) return null;

        const filtered = candles.filter(c => c.time >= anchorTime);
        if (filtered.length === 0) return null;

        let cumVol = 0;
        let cumTpv = 0;
        const points = [];

        for (const c of filtered) {
            const tp = (c.high + c.low + c.close) / 3.0;
            const vol = c.volume || 1;
            cumVol += vol;
            cumTpv += (tp * vol);

            const vwap = cumTpv / cumVol;
            points.push({ time: c.time, tp, vol, vwap });
        }

        // Second pass: compute running variance & standard deviation bands
        let cumWeightedDiffSq = 0;
        let runningVol = 0;
        for (const p of points) {
            runningVol += p.vol;
            cumWeightedDiffSq += p.vol * Math.pow(p.tp - p.vwap, 2);
            const variance = cumWeightedDiffSq / runningVol;
            const stdDev = Math.sqrt(Math.max(variance, 0.0000001));

            p.upper1 = p.vwap + (1.0 * stdDev);
            p.lower1 = p.vwap - (1.0 * stdDev);
            p.upper2 = p.vwap + (2.0 * stdDev);
            p.lower2 = p.vwap - (2.0 * stdDev);
            p.upper3 = p.vwap + (3.0 * stdDev);
            p.lower3 = p.vwap - (3.0 * stdDev);
            p.stdDev = stdDev;
        }

        return { anchor_time: anchorTime, points };
    }

    computeCHoCHandBOS(candles, fractalWindow = 3) {
        if (!candles || candles.length < (fractalWindow * 2 + 1)) return [];

        const swings = [];
        const n = candles.length;

        for (let i = fractalWindow; i < n - fractalWindow; i++) {
            const curr = candles[i];
            let isHigh = true;
            let isLow = true;

            for (let j = 1; j <= fractalWindow; j++) {
                if (candles[i - j].high >= curr.high || candles[i + j].high >= curr.high) isHigh = false;
                if (candles[i - j].low <= curr.low || candles[i + j].low <= curr.low) isLow = false;
            }

            if (isHigh) swings.push({ type: 'HIGH', price: curr.high, time: curr.time, index: i });
            if (isLow) swings.push({ type: 'LOW', price: curr.low, time: curr.time, index: i });
        }

        const structures = [];
        let currentTrend = 'BULLISH';
        let lastHigh = null;
        let lastLow = null;

        for (const sw of swings) {
            if (sw.type === 'HIGH') {
                if (lastHigh && sw.price > lastHigh.price) {
                    structures.push({
                        type: currentTrend === 'BULLISH' ? 'BOS' : 'CHOCH',
                        bias: 'BULLISH',
                        price: lastHigh.price,
                        time_start: lastHigh.time,
                        time_break: sw.time,
                        swing_type: 'HIGH',
                        mitigated: false
                    });
                    currentTrend = 'BULLISH';
                }
                lastHigh = sw;
            } else if (sw.type === 'LOW') {
                if (lastLow && sw.price < lastLow.price) {
                    structures.push({
                        type: currentTrend === 'BEARISH' ? 'BOS' : 'CHOCH',
                        bias: 'BEARISH',
                        price: lastLow.price,
                        time_start: lastLow.time,
                        time_break: sw.time,
                        swing_type: 'LOW',
                        mitigated: false
                    });
                    currentTrend = 'BEARISH';
                }
                lastLow = sw;
            }
        }

        return structures;
    }

    computeCVDWaves(candles, cvdSeries) {
        if (!candles || !cvdSeries || candles.length < 5 || cvdSeries.length < 5) return [];
        const waves = [];
        // Detect price pivot vs CVD pivot divergences
        for (let i = 2; i < candles.length - 2; i++) {
            const c1 = candles[i - 2];
            const c2 = candles[i];
            const cvd1 = cvdSeries[i - 2]?.cvd ?? 0;
            const cvd2 = cvdSeries[i]?.cvd ?? 0;

            // Bullish Absorption: Price lower low, CVD higher low
            if (c2.low < c1.low && cvd2 > cvd1) {
                waves.push({
                    type: 'BULLISH_ABSORPTION',
                    time1: c1.time,
                    price1: c1.low,
                    cvd1: cvd1,
                    time2: c2.time,
                    price2: c2.low,
                    cvd2: cvd2
                });
            }
            // Bearish Absorption: Price higher high, CVD lower high
            else if (c2.high > c1.high && cvd2 < cvd1) {
                waves.push({
                    type: 'BEARISH_ABSORPTION',
                    time1: c1.time,
                    price1: c1.high,
                    cvd1: cvd1,
                    time2: c2.time,
                    price2: c2.high,
                    cvd2: cvd2
                });
            }
        }
        return waves;
    }

    createControlsHUD() {
        const hud = document.createElement('div');
        hud.className = 'smc-controls-hud';
        hud.style.position = 'absolute';
        hud.style.top = '10px';
        hud.style.left = '10px';
        hud.style.zIndex = '10';
        hud.style.display = 'flex';
        hud.style.flexWrap = 'wrap';
        hud.style.gap = '6px';
        hud.style.background = 'rgba(15, 23, 42, 0.88)';
        hud.style.padding = '4px 8px';
        hud.style.borderRadius = '6px';
        hud.style.border = '1px solid rgba(255, 255, 255, 0.1)';
        hud.style.fontSize = '11px';
        hud.style.fontFamily = '"JetBrains Mono", monospace';
        hud.style.color = '#94A3B8';

        const layersConfig = [
            { key: 'fvg', label: 'FVG' },
            { key: 'fvgCe', label: '50% CE' },
            { key: 'ob', label: 'OB' },
            { key: 'chochBos', label: 'CHoCH/BOS' },
            { key: 'vpvr', label: 'VPVR' },
            { key: 'vwap', label: 'VWAP' },
            { key: 'cvdWaves', label: 'CVD Waves' },
            { key: 'rsiDiv', label: 'RSI Div' },
            { key: 'ote', label: 'OTE' },
            { key: 'sweeps', label: 'Sweeps' },
            { key: 'killzones', label: 'Killzones' }
        ];

        for (const item of layersConfig) {
            const btn = document.createElement('button');
            btn.className = `smc-toggle-btn ${this.layers[item.key] ? 'active' : ''}`;
            btn.textContent = item.label;
            btn.style.background = this.layers[item.key] ? 'rgba(0, 242, 254, 0.2)' : 'transparent';
            btn.style.border = `1px solid ${this.layers[item.key] ? '#00F2FE' : 'rgba(255, 255, 255, 0.15)'}`;
            btn.style.color = this.layers[item.key] ? '#00F2FE' : '#94A3B8';
            btn.style.padding = '2px 6px';
            btn.style.borderRadius = '4px';
            btn.style.cursor = 'pointer';

            btn.addEventListener('click', () => {
                const active = this.toggleLayer(item.key);
                btn.style.background = active ? 'rgba(0, 242, 254, 0.2)' : 'transparent';
                btn.style.border = `1px solid ${active ? '#00F2FE' : 'rgba(255, 255, 255, 0.15)'}`;
                btn.style.color = active ? '#00F2FE' : '#94A3B8';
            });
            hud.appendChild(btn);
        }

        this.container.appendChild(hud);
        this.hudElement = hud;
        return hud;
    }

    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        if (this._clickHandler && this.container) {
            this.container.removeEventListener('click', this._clickHandler);
        }
        if (this.hudElement && this.hudElement.parentNode) {
            this.hudElement.parentNode.removeChild(this.hudElement);
        }
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
    }
}

// Universal Module Definition
if (typeof window !== 'undefined') {
    window.SMCOverlaysRenderer = SMCOverlaysRenderer;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SMCOverlaysRenderer
    };
}
