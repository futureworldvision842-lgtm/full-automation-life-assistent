/**
 * terminal_core.js — Institutional Duplex Starlette WebSocket & EventBus Client.
 * 
 * Provides:
 * - Full-duplex WebSocket connection to /ws/terminal with auto-reconnect & exponential backoff (1s -> 15s).
 * - Heartbeat keepalive ping/pong mechanism.
 * - Pub/Sub EventBus (on, off, once, emit) decoupling chart, risk, DOM, positions, and voice panes.
 * - In-memory central state cache (quotes, candles, SMC, CVD, positions, risk metrics).
 * - 1-Click execution command dispatchers with dual WebSocket + REST API fallback.
 * 
 * Exported to window.TerminalCore and window.TradingTerminal.core.
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.TerminalCore = factory();
        root.TradingTerminal = root.TradingTerminal || {};
        root.TradingTerminal.core = root.TerminalCore;
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    // EventBus implementation
    class EventBus {
        constructor() {
            this.events = {};
        }

        on(event, handler) {
            if (!this.events[event]) this.events[event] = [];
            this.events[event].push(handler);
            return () => this.off(event, handler);
        }

        off(event, handler) {
            if (!this.events[event]) return;
            if (!handler) {
                delete this.events[event];
                return;
            }
            this.events[event] = this.events[event].filter(h => h !== handler);
        }

        once(event, handler) {
            const wrapped = (...args) => {
                this.off(event, wrapped);
                handler(...args);
            };
            return this.on(event, wrapped);
        }

        emit(event, data) {
            if (!this.events[event]) return;
            const listeners = this.events[event].slice();
            for (let i = 0; i < listeners.length; i++) {
                try {
                    listeners[i](data);
                } catch (err) {
                    console.error(`Error in EventBus listener for '${event}':`, err);
                }
            }
        }
    }

    class TerminalCoreEngine {
        constructor(config = {}) {
            this.events = new EventBus();

            // Configuration
            this.baseUrl = config.baseUrl || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000');
            this.wsUrl = config.wsUrl || this._resolveWsUrl('/ws/terminal');
            this.autoConnect = config.autoConnect !== false;
            this.maxReconnectDelay = config.maxReconnectDelay || 15000;
            this.heartbeatInterval = config.heartbeatInterval || 15000;

            // Connection state
            this.ws = null;
            this.status = 'DISCONNECTED'; // DISCONNECTED | CONNECTING | CONNECTED | RECONNECTING
            this.reconnectAttempts = 0;
            this.reconnectTimer = null;
            this.heartbeatTimer = null;

            // Active parameters
            this.activeSymbol = config.symbol || 'XAUUSD';
            this.activeTimeframe = config.timeframe || 'M15';

            // Central In-Memory State Cache
            this.state = {
                status: 'RUNNING',
                simulation_mode: true,
                mt5_connected: false,
                account: {
                    tier: '25k',
                    balance: 25000.0,
                    equity: 25000.0,
                    currency: 'USD'
                },
                quotes: {
                    XAUUSD: { bid: 2650.38, ask: 2650.62, last: 2650.50, spread: 0.25 },
                    EURUSD: { bid: 1.08492, ask: 1.08508, last: 1.08500, spread: 0.00016 },
                    GBPUSD: { bid: 1.29491, ask: 1.29509, last: 1.29500, spread: 0.00018 },
                    USDJPY: { bid: 153.492, ask: 153.508, last: 153.500, spread: 0.016 }
                },
                candles: {},       // key: "SYMBOL_TIMEFRAME" -> [ {time, open, high, low, close, volume} ]
                smc: {},           // key: "SYMBOL_TIMEFRAME" -> { fvgs, order_blocks, ote, sweeps, killzones }
                cvd: {},           // key: "SYMBOL" -> { cvd_history, current_ratio, divergence }
                positions: [],     // [ {ticket, symbol, type, volume, price_open, price_current, sl, tp, profit} ]
                riskMetrics: null, // Full Aladdin & Prop Firm payload
                marketDepth: {}    // key: "SYMBOL" -> { bids, asks, buyer_ratio, seller_ratio }
            };

            if (this.autoConnect && typeof window !== 'undefined') {
                this.connect();
            }
        }

        // =========================================================================
        // 1. WebSocket Lifecycle & Connection Management
        // =========================================================================

        _resolveWsUrl(path) {
            if (typeof window === 'undefined') return `ws://localhost:8000${path}`;
            const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host || 'localhost:8000';
            return `${proto}//${host}${path}`;
        }

        connect() {
            if (this.ws && (this.ws.readyState === 0 || this.ws.readyState === 1)) {
                return; // Already connecting or open
            }

            this._clearTimers();
            this._setStatus(this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING');

            try {
                if (typeof WebSocket === 'undefined') {
                    console.warn('WebSocket API unavailable in current environment.');
                    this._setStatus('DISCONNECTED');
                    return;
                }

                this.ws = new WebSocket(this.wsUrl);
                this.ws.onopen = this._onOpen.bind(this);
                this.ws.onmessage = this._onMessage.bind(this);
                this.ws.onerror = this._onError.bind(this);
                this.ws.onclose = this._onClose.bind(this);
            } catch (err) {
                console.error('TerminalCore WebSocket instantiation failed:', err);
                this._scheduleReconnect();
            }
        }

        disconnect() {
            this._clearTimers();
            if (this.ws) {
                this.ws.onopen = null;
                this.ws.onmessage = null;
                this.ws.onerror = null;
                this.ws.onclose = null;
                try {
                    this.ws.close();
                } catch (e) {}
                this.ws = null;
            }
            this._setStatus('DISCONNECTED');
        }

        _onOpen() {
            console.log(`[TerminalCore] WebSocket connected to ${this.wsUrl}`);
            this.reconnectAttempts = 0;
            this._setStatus('CONNECTED');
            this._startHeartbeat();

            // Send initial subscription
            this.subscribe(this.activeSymbol, this.activeTimeframe);

            // Emit connected event
            this.events.emit('connected', { url: this.wsUrl, timestamp: Date.now() });
        }

        _onMessage(evt) {
            try {
                const msg = JSON.parse(evt.data);
                this._handleIncomingMessage(msg);
            } catch (err) {
                console.warn('[TerminalCore] Non-JSON WebSocket message received:', evt.data);
            }
        }

        _onError(err) {
            console.warn('[TerminalCore] WebSocket error encountered:', err);
            this.events.emit('ws_error', err);
        }

        _onClose(evt) {
            console.log(`[TerminalCore] WebSocket closed (code: ${evt.code}, reason: ${evt.reason})`);
            this._clearTimers();
            this._setStatus('DISCONNECTED');
            this.events.emit('disconnected', { code: evt.code, reason: evt.reason });
            this._scheduleReconnect();
        }

        _scheduleReconnect() {
            if (this.reconnectTimer) return;
            this.reconnectAttempts++;
            // Exponential backoff with jitter: 1s, 2s, 4s, 8s up to maxReconnectDelay
            const baseDelay = Math.min(1000 * Math.pow(2, this.reconnectAttempts - 1), this.maxReconnectDelay);
            const jitter = Math.floor(Math.random() * 500);
            const delay = baseDelay + jitter;

            console.log(`[TerminalCore] Reconnecting in ${delay}ms (attempt #${this.reconnectAttempts})...`);
            this._setStatus('RECONNECTING');

            this.reconnectTimer = setTimeout(() => {
                this.reconnectTimer = null;
                this.connect();
            }, delay);
        }

        _startHeartbeat() {
            this._clearHeartbeat();
            this.heartbeatTimer = setInterval(() => {
                if (this.ws && this.ws.readyState === 1) {
                    try {
                        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
                    } catch (e) {}
                }
            }, this.heartbeatInterval);
        }

        _clearHeartbeat() {
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
                this.heartbeatTimer = null;
            }
        }

        _clearTimers() {
            this._clearHeartbeat();
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        }

        _setStatus(newStatus) {
            if (this.status === newStatus) return;
            this.status = newStatus;
            this.events.emit('connection_change', {
                status: this.status,
                reconnectAttempts: this.reconnectAttempts,
                timestamp: Date.now()
            });
        }

        // =========================================================================
        // 2. Incoming Message Dispatcher & Central State Updates
        // =========================================================================

        _handleIncomingMessage(msg) {
            if (!msg || !msg.type) return;

            switch (msg.type) {
                case 'tick':
                    this._updateTick(msg);
                    break;
                case 'candle_update':
                    this._updateCandle(msg);
                    break;
                case 'smc_update':
                    this._updateSMC(msg);
                    break;
                case 'cvd_update':
                    this._updateCVD(msg);
                    break;
                case 'cockpit_metrics':
                    this._updateCockpit(msg);
                    break;
                case 'positions_update':
                    this._updatePositions(msg);
                    break;
                case 'jarvis_event':
                    this.events.emit('jarvis_event', msg);
                    break;
                case 'command_result':
                    this.events.emit('command_result', msg);
                    break;
                case 'market_depth':
                    this._updateMarketDepth(msg);
                    break;
                case 'pong':
                    // Keepalive pong received
                    break;
                default:
                    this.events.emit('raw_message', msg);
                    break;
            }
        }

        _updateTick(msg) {
            const sym = msg.symbol;
            if (!sym) return;

            this.state.quotes[sym] = {
                bid: msg.bid,
                ask: msg.ask,
                last: msg.last,
                time: msg.time,
                volume: msg.volume
            };

            this.events.emit('tick', msg);
        }

        _updateCandle(msg) {
            const sym = msg.symbol;
            const tf = msg.timeframe;
            const key = `${sym}_${tf}`;

            if (!this.state.candles[key]) {
                this.state.candles[key] = [];
            }

            const candles = this.state.candles[key];
            const incoming = msg.candle;

            if (candles.length > 0) {
                const last = candles[candles.length - 1];
                if (last.time === incoming.time) {
                    candles[candles.length - 1] = incoming;
                } else if (incoming.time > last.time) {
                    candles.push(incoming);
                    if (candles.length > 500) candles.shift();
                }
            } else {
                candles.push(incoming);
            }

            this.events.emit('candle_update', msg);
        }

        _updateSMC(msg) {
            const sym = msg.symbol;
            const tf = msg.data && msg.data.timeframe ? msg.data.timeframe : this.activeTimeframe;
            const key = `${sym}_${tf}`;
            this.state.smc[key] = msg.data;
            this.events.emit('smc_update', msg);
        }

        _updateCVD(msg) {
            const sym = msg.symbol;
            this.state.cvd[sym] = msg;
            this.events.emit('cvd_update', msg);
        }

        _updateCockpit(msg) {
            const data = msg.data || msg;
            this.state.riskMetrics = data;
            if (data.balance) this.state.account.balance = data.balance;
            if (data.equity) this.state.account.equity = data.equity;
            if (data.open_positions) this.state.positions = data.open_positions;
            this.events.emit('cockpit_metrics', data);
        }

        _updatePositions(msg) {
            this.state.positions = Array.isArray(msg.positions) ? msg.positions : [];
            this.events.emit('positions_update', { positions: this.state.positions });
        }

        _updateMarketDepth(msg) {
            const sym = msg.symbol;
            this.state.marketDepth[sym] = msg;
            this.events.emit('market_depth', msg);
        }

        // =========================================================================
        // 3. Execution Commands (WebSocket + REST Fallback)
        // =========================================================================

        /**
         * 1-Click Scale-Out (50% or custom ratio) and securing SL to Breakeven.
         */
        async scaleOut(ticket, ratio = 0.5, bufferPips = 2.0) {
            const payload = {
                ticket: parseInt(ticket, 10),
                ratio: parseFloat(ratio),
                buffer_pips: parseFloat(bufferPips)
            };

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'command',
                    action: 'scale_out',
                    ticket: payload.ticket,
                    ratio: payload.ratio,
                    buffer_pips: payload.buffer_pips
                }));
            }

            // Always also trigger REST for guarantee & response
            try {
                const res = await this._post('/api/execution/scale-out', payload);
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST scale-out fallback error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * 1-Click Lock Breakeven with pip buffer.
         */
        async breakeven(ticket, bufferPips = 2.0) {
            const payload = {
                ticket: parseInt(ticket, 10),
                buffer_pips: parseFloat(bufferPips)
            };

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'command',
                    action: 'breakeven',
                    ticket: payload.ticket,
                    buffer_pips: payload.buffer_pips
                }));
            }

            try {
                const res = await this._post('/api/execution/breakeven', payload);
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST breakeven fallback error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * 1-Click Modify SL / TP price levels.
         */
        async modifySLTP(ticket, sl, tp) {
            const payload = {
                ticket: parseInt(ticket, 10),
                sl: parseFloat(sl),
                tp: parseFloat(tp)
            };

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'command',
                    action: 'modify_sltp',
                    ticket: payload.ticket,
                    sl: payload.sl,
                    tp: payload.tp
                }));
            }

            try {
                const res = await this._post('/api/execution/modify-sltp', payload);
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST modify SL/TP fallback error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * 1-Click Liquidate Single Position.
         */
        async closePosition(ticket) {
            const payload = {
                ticket: parseInt(ticket, 10)
            };

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'command',
                    action: 'close_position',
                    ticket: payload.ticket
                }));
            }

            try {
                const res = await this._post('/api/execution/close-position', payload);
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST close position fallback error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * Emergency Circuit Breaker (Kill Switch).
         */
        async killSwitch(reason = 'Emergency User Panic Button', cancelPending = true) {
            const payload = {
                reason: reason,
                cancel_pending: !!cancelPending
            };

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'command',
                    action: 'kill_switch',
                    reason: payload.reason,
                    cancel_pending: payload.cancel_pending
                }));
            }

            try {
                const res = await this._post('/api/control/kill-switch', payload);
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST kill switch fallback error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * Toggle bot autonomous loop pause/resume.
         */
        async togglePause(action = 'toggle') {
            try {
                const res = await this._post('/api/control/toggle-pause', { action });
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST toggle pause error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * Dispatches natural language voice transcript.
         */
        async sendVoiceTranscript(transcript, activeSymbol = this.activeSymbol) {
            const payload = {
                transcript: transcript,
                active_symbol: activeSymbol,
                source: 'web_speech_api'
            };

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'voice_intent',
                    transcript: transcript,
                    active_symbol: activeSymbol
                }));
            }

            try {
                const res = await this._post('/api/voice/command', payload);
                return res;
            } catch (err) {
                console.warn('[TerminalCore] REST voice command error:', err);
                return { success: false, message: err.message };
            }
        }

        /**
         * Subscribes to symbol & timeframe over WebSocket.
         */
        subscribe(symbol, timeframe) {
            this.activeSymbol = (symbol || this.activeSymbol).toUpperCase();
            this.activeTimeframe = (timeframe || this.activeTimeframe).toUpperCase();

            if (this.ws && this.ws.readyState === 1) {
                this.ws.send(JSON.stringify({
                    type: 'subscribe',
                    symbol: this.activeSymbol,
                    timeframe: this.activeTimeframe
                }));
            }
        }

        // =========================================================================
        // 4. REST Data Fetchers & Initial Hydration
        // =========================================================================

        async fetchInitialData(symbol = this.activeSymbol, timeframe = this.activeTimeframe) {
            const sym = symbol.toUpperCase();
            const tf = timeframe.toUpperCase();

            try {
                const [statusRes, candlesRes, smcRes, cvdRes, riskRes] = await Promise.allSettled([
                    this._get('/api/status'),
                    this._get(`/api/candles?symbol=${sym}&timeframe=${tf}&limit=300`),
                    this._get(`/api/smc?symbol=${sym}&timeframe=${tf}`),
                    this._get(`/api/cvd?symbol=${sym}&limit=100`),
                    this._get('/api/risk/metrics')
                ]);

                if (statusRes.status === 'fulfilled' && statusRes.value) {
                    this.state.status = statusRes.value.status;
                    this.state.simulation_mode = statusRes.value.simulation_mode;
                    this.state.mt5_connected = statusRes.value.mt5_connected;
                    if (statusRes.value.account) this.state.account = statusRes.value.account;
                    if (statusRes.value.quotes) this.state.quotes = statusRes.value.quotes;
                    this.events.emit('status_loaded', statusRes.value);
                }

                if (candlesRes.status === 'fulfilled' && candlesRes.value) {
                    const key = `${sym}_${tf}`;
                    this.state.candles[key] = candlesRes.value.candles || [];
                    this.events.emit('candles_loaded', candlesRes.value);
                }

                if (smcRes.status === 'fulfilled' && smcRes.value) {
                    const key = `${sym}_${tf}`;
                    this.state.smc[key] = smcRes.value;
                    this.events.emit('smc_loaded', smcRes.value);
                }

                if (cvdRes.status === 'fulfilled' && cvdRes.value) {
                    this.state.cvd[sym] = cvdRes.value;
                    this.events.emit('cvd_loaded', cvdRes.value);
                }

                if (riskRes.status === 'fulfilled' && riskRes.value) {
                    this.state.riskMetrics = riskRes.value;
                    this.events.emit('cockpit_metrics', riskRes.value);
                    if (riskRes.value.open_positions) {
                        this.state.positions = riskRes.value.open_positions;
                        this.events.emit('positions_update', { positions: this.state.positions });
                    }
                }

                return { success: true };
            } catch (err) {
                console.error('[TerminalCore] Failed to fetch initial data:', err);
                return { success: false, error: err };
            }
        }

        // =========================================================================
        // 5. REST Network Helpers
        // =========================================================================

        async _get(path) {
            const url = `${this.baseUrl}${path}`;
            const res = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' } });
            if (!res.ok) throw new Error(`HTTP GET ${path} failed: ${res.status}`);
            return await res.json();
        }

        async _post(path, body) {
            const url = `${this.baseUrl}${path}`;
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify(body)
            });
            if (!res.ok) {
                const errJson = await res.json().catch(() => ({}));
                throw new Error(errJson.detail || `HTTP POST ${path} failed: ${res.status}`);
            }
            return await res.json();
        }

        // =========================================================================
        // 6. Event Subscription Delegates
        // =========================================================================

        on(event, handler) {
            return this.events.on(event, handler);
        }

        off(event, handler) {
            return this.events.off(event, handler);
        }

        once(event, handler) {
            return this.events.once(event, handler);
        }

        emit(event, data) {
            return this.events.emit(event, data);
        }
    }

    return TerminalCoreEngine;
}));
