/**
 * terminal_app.js — Master UI Coordinator & Institutional Web Trading Terminal Application.
 * 
 * Provides:
 * - Master UI coordination linking TerminalCore, RiskCockpit, and VoiceCopilot.
 * - Interactive Open Positions Table with 1-click execution:
 *     * 1-Click 50% Scale-Out button (with Breakeven SL securing)
 *     * Instant Breakeven+ button (2-pip profit buffer)
 *     * Inline editable SL and TP inputs with instant commit
 *     * 1-Click Close / Liquidate button
 *     * Emergency Circuit Breaker (Kill Switch) with modal confirmation dialog
 * - Real-time mark-to-market PnL calculation and dynamic number formatting.
 * - Multi-pane tab switching (Positions, History, System Logs, Voice Logs).
 * - DOM 5-level Order Book ladder & CVD Volume Delta renderer.
 * - TradingView Lightweight Charts & SMC visual overlays.
 * - Standalone offline simulation fallback for client verification.
 * 
 * Exported to window.TerminalApp and window.TradingTerminal.app.
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['./terminal_core', './risk_cockpit', './voice_copilot', './chart_engine', './smc_overlays', './cvd_pane'], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory(
            require('./terminal_core'),
            require('./risk_cockpit'),
            require('./voice_copilot'),
            require('./chart_engine'),
            require('./smc_overlays'),
            require('./cvd_pane')
        );
    } else {
        root.TerminalApp = factory(
            root.TerminalCore,
            root.RiskCockpit,
            root.VoiceCopilot,
            root.ChartEngine,
            root.SMCOverlaysRenderer,
            root.CVDPaneRenderer
        );
        root.TradingTerminal = root.TradingTerminal || {};
        root.TradingTerminal.app = root.TerminalApp;
    }
}(typeof self !== 'undefined' ? self : this, function(TerminalCoreClass, RiskCockpitClass, VoiceCopilotClass, ChartEngineClass, SMCOverlaysRendererClass, CVDPaneRendererClass) {
    'use strict';

    const SYMBOL_SPECS = {
        'XAUUSD': { decimals: 2, pip: 0.10, contract: 100.0, name: 'Spot Gold / USD' },
        'EURUSD': { decimals: 5, pip: 0.0001, contract: 100000.0, name: 'Euro / US Dollar' },
        'GBPUSD': { decimals: 5, pip: 0.0001, contract: 100000.0, name: 'British Pound / USD' },
        'USDJPY': { decimals: 3, pip: 0.01, contract: 100000.0, name: 'US Dollar / Yen' },
        'BTCUSD': { decimals: 2, pip: 1.00, contract: 1.0, name: 'Bitcoin / US Dollar' },
        'ETHUSD': { decimals: 2, pip: 0.10, contract: 1.0, name: 'Ethereum / US Dollar' },
        'SOLUSD': { decimals: 2, pip: 0.01, contract: 1.0, name: 'Solana / US Dollar' }
    };

    class TradingTerminalApp {
        constructor() {
            // Instantiate submodules
            const CoreClass = TerminalCoreClass || (typeof window !== 'undefined' ? window.TerminalCore : null);
            const RiskClass = RiskCockpitClass || (typeof window !== 'undefined' ? window.RiskCockpit : null);
            const VoiceClass = VoiceCopilotClass || (typeof window !== 'undefined' ? window.VoiceCopilot : null);
            this.ChartEngineClass = ChartEngineClass || (typeof window !== 'undefined' ? window.ChartEngine : null);
            this.SMCOverlaysClass = SMCOverlaysRendererClass || (typeof window !== 'undefined' ? window.SMCOverlaysRenderer : null);
            this.CVDPaneClass = CVDPaneRendererClass || (typeof window !== 'undefined' ? window.CVDPaneRenderer : null);

            this.core = CoreClass ? new CoreClass({ autoConnect: true }) : null;
            this.riskCockpit = RiskClass ? new RiskClass({ accountTier: '25k' }) : null;
            this.voiceCopilot = VoiceClass ? new VoiceClass({ terminalCore: this.core }) : null;
            this.chartEngine = null;
            this.smcRenderer = null;
            this.cvdRenderer = null;

            // Register global reference
            if (typeof window !== 'undefined') {
                window.TradingTerminal = {
                    core: this.core,
                    riskCockpit: this.riskCockpit,
                    voiceCopilot: this.voiceCopilot,
                    chartEngine: this.chartEngine,
                    smcRenderer: this.smcRenderer,
                    cvdRenderer: this.cvdRenderer,
                    app: this
                };
            }

            // Active state
            this.activeSymbol = 'XAUUSD';
            this.activeTimeframe = 'M15';
            this.tradeHistory = [];
            this.systemLogs = [];
            this.chartInstance = null;
            this.candleSeries = null;
            this.simulationInterval = null;

            // DOM ready initialization
            if (typeof document !== 'undefined') {
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', () => this.init());
                } else {
                    this.init();
                }
            }
        }

        // =========================================================================
        // 1. App Initialization & Event Wiring
        // =========================================================================

        init() {
            console.log('[TerminalApp] Initializing Institutional Trading Terminal...');
            this._bindHeaderControls();
            this._bindBottomTabs();
            this._bindOrderEntryForm();
            this._bindModalControls();
            this._initChartAndRenderers();
            this._bindCoreEvents();
            this._initWorldMonitor();

            // Initial data hydration
            if (this.core) {
                this.core.fetchInitialData(this.activeSymbol, this.activeTimeframe);
            }

            // Log startup
            this.logSystem('Terminal initialized successfully. Connected to Institutional ASGI Backend.', 'INFO');
        }

        _bindCoreEvents() {
            if (!this.core) return;

            // Connection status updates
            this.core.on('connection_change', (data) => {
                this._updateConnectionBadge(data.status);
            });

            // Live ticks -> Update ticker header & DOM ladder & chart & cvd
            this.core.on('tick', (tick) => {
                if (tick.symbol === this.activeSymbol) {
                    this._updateHeaderPrice(tick);
                    if (this.chartEngine && typeof this.chartEngine.onTick === 'function') {
                        this.chartEngine.onTick(tick);
                    }
                    if (this.cvdRenderer && typeof this.cvdRenderer.onTick === 'function') {
                        this.cvdRenderer.onTick(tick);
                    }
                }
                this._updatePositionsMarkToMarket(tick);
            });

            // Candlestick updates -> Chart
            this.core.on('candle_update', (data) => {
                if (data.symbol === this.activeSymbol && data.timeframe === this.activeTimeframe) {
                    if (this.chartEngine && typeof this.chartEngine.updateCandle === 'function') {
                        this.chartEngine.updateCandle(data.candle);
                    }
                    this._updateChartCandle(data.candle);
                }
            });

            // SMC overlays -> Render overlays
            this.core.on('smc_update', (data) => {
                if (data.symbol === this.activeSymbol) {
                    const smcPayload = data.data || data;
                    if (this.smcRenderer) {
                        if (typeof this.smcRenderer.updateSMC === 'function') {
                            this.smcRenderer.updateSMC(smcPayload);
                        } else if (typeof this.smcRenderer.updateSMCData === 'function') {
                            this.smcRenderer.updateSMCData(smcPayload);
                        }
                    }
                    this._renderSMCOverlays(smcPayload);
                }
            });

            // CVD Volume Delta updates
            this.core.on('cvd_update', (data) => {
                if (data.symbol === this.activeSymbol) {
                    if (this.cvdRenderer && typeof this.cvdRenderer.updateCVD === 'function') {
                        this.cvdRenderer.updateCVD(data);
                    }
                    this._renderCVD(data);
                }
            });

            // Cockpit Telemetry -> RiskCockpit
            this.core.on('cockpit_metrics', (metrics) => {
                if (this.riskCockpit) {
                    this.riskCockpit.updateFromMetrics(metrics);
                }
            });

            // Positions updates -> Render Positions Table
            this.core.on('positions_update', (data) => {
                this.renderPositionsTable(data.positions);
                if (this.riskCockpit) {
                    this.riskCockpit.setOpenPositions(data.positions);
                }
            });

            // Level 2 Market Depth (DOM)
            this.core.on('market_depth', (dom) => {
                if (dom.symbol === this.activeSymbol) {
                    if (this.cvdRenderer && typeof this.cvdRenderer.updateDOM === 'function') {
                        this.cvdRenderer.updateDOM(dom);
                    }
                    this._renderDOMOrderBook(dom);
                }
            });

            // Jarvis events / notifications
            this.core.on('jarvis_event', (evt) => {
                this.logSystem(`[JARVIS] ${evt.speech || evt.action}`, 'JARVIS');
                this._showToast(evt.speech || 'Action executed successfully', 'success');
            });

            // World Monitor Geopolitical Radar updates
            this.core.on('world_monitor_update', (msg) => {
                const payload = msg.data || msg;
                this._renderWorldMonitor(payload);
            });
            this.core.on('raw_message', (msg) => {
                if (msg && msg.type === 'world_monitor_update') {
                    const payload = msg.data || msg;
                    this._renderWorldMonitor(payload);
                }
            });
        }

        // =========================================================================
        // 2. Header & Navigation Controls
        // =========================================================================

        _bindHeaderControls() {
            // 1. Symbol Switcher Tabs
            const symbolTabs = document.querySelectorAll('.symbol-tab');
            symbolTabs.forEach(tab => {
                tab.addEventListener('click', (e) => {
                    const sym = tab.getAttribute('data-symbol');
                    if (sym) this.switchSymbol(sym);
                });
            });

            // 2. Timeframe Selector Buttons
            const tfBtns = document.querySelectorAll('.tf-btn');
            tfBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const tf = btn.getAttribute('data-tf');
                    if (tf) this.switchTimeframe(tf);
                });
            });

            // 3. Account Profile Selector ($25k, $50k, $100k)
            const profileSelect = document.getElementById('account-profile-select');
            if (profileSelect) {
                profileSelect.addEventListener('change', (e) => {
                    const tier = e.target.value;
                    if (this.riskCockpit) {
                        this.riskCockpit.setTier(tier);
                        this.logSystem(`Switched account profile preset to ${tier.toUpperCase()}`, 'INFO');
                    }
                });
            }

            // 4. Voice Copilot Mic Toggle
            const micBtn = document.getElementById('voice-mic-btn');
            if (micBtn) {
                micBtn.addEventListener('click', () => {
                    if (this.voiceCopilot) {
                        this.voiceCopilot.toggleListening();
                    }
                });
            }

            // 5. Bot Autonomous Pause/Resume Button
            const pauseBtn = document.getElementById('btn-toggle-pause');
            if (pauseBtn) {
                pauseBtn.addEventListener('click', async () => {
                    if (this.core) {
                        const res = await this.core.togglePause('toggle');
                        if (res && res.status) {
                            pauseBtn.textContent = res.paused ? '▶ RESUME BOT' : '⏸ PAUSE BOT';
                            pauseBtn.className = res.paused ? 'btn-ctrl btn-resume' : 'btn-ctrl btn-pause';
                            this.logSystem(`Bot state changed to: ${res.status}`, 'WARNING');
                        }
                    }
                });
            }

            // 6. Voice Command Text Input Fallback
            const voiceInput = document.getElementById('voice-cmd-input');
            const voiceSendBtn = document.getElementById('btn-send-voice-cmd');
            const handleVoiceSubmit = () => {
                if (!voiceInput) return;
                const text = voiceInput.value.trim();
                if (text && this.voiceCopilot) {
                    this.voiceCopilot.processTranscript(text);
                    voiceInput.value = '';
                }
            };

            if (voiceSendBtn) voiceSendBtn.addEventListener('click', handleVoiceSubmit);
            if (voiceInput) {
                voiceInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') handleVoiceSubmit();
                });
            }
        }

        switchSymbol(symbol) {
            this.activeSymbol = symbol.toUpperCase();

            // Update Tab UI
            document.querySelectorAll('.symbol-tab').forEach(tab => {
                tab.classList.toggle('active', tab.getAttribute('data-symbol') === this.activeSymbol);
            });

            // Update Header Name
            const spec = SYMBOL_SPECS[this.activeSymbol] || { name: this.activeSymbol };
            const nameEl = document.getElementById('active-symbol-name');
            if (nameEl) nameEl.textContent = `${this.activeSymbol} (${spec.name})`;

            if (this.chartEngine && typeof this.chartEngine.setSymbol === 'function') {
                this.chartEngine.setSymbol(this.activeSymbol);
            }
            if (this.smcRenderer && typeof this.smcRenderer.setSymbol === 'function') {
                this.smcRenderer.setSymbol(this.activeSymbol);
            }
            if (this.cvdRenderer && typeof this.cvdRenderer.setSymbol === 'function') {
                this.cvdRenderer.setSymbol(this.activeSymbol);
            }

            if (this.voiceCopilot) {
                this.voiceCopilot.setActiveSymbol(this.activeSymbol);
            }

            if (this.core) {
                this.core.subscribe(this.activeSymbol, this.activeTimeframe);
                this.core.fetchInitialData(this.activeSymbol, this.activeTimeframe);
            }

            this.logSystem(`Active chart symbol switched to ${this.activeSymbol}`, 'INFO');
        }

        switchTimeframe(tf) {
            this.activeTimeframe = tf.toUpperCase();

            // Update Button UI
            document.querySelectorAll('.tf-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-tf') === this.activeTimeframe);
            });

            if (this.chartEngine && typeof this.chartEngine.setTimeframe === 'function') {
                this.chartEngine.setTimeframe(this.activeTimeframe);
            }

            if (this.core) {
                this.core.subscribe(this.activeSymbol, this.activeTimeframe);
                this.core.fetchInitialData(this.activeSymbol, this.activeTimeframe);
            }

            this.logSystem(`Active timeframe switched to ${this.activeTimeframe}`, 'INFO');
        }

        _updateConnectionBadge(status) {
            const badge = document.getElementById('terminal-status-badge');
            const dot = document.getElementById('status-dot');
            const text = document.getElementById('status-text');

            if (!badge || !dot || !text) return;

            badge.className = `status-badge conn-${status.toLowerCase()}`;
            text.textContent = status;
        }

        _updateHeaderPrice(tick) {
            const bidEl = document.getElementById('active-symbol-bid');
            const askEl = document.getElementById('active-symbol-ask');
            const spreadEl = document.getElementById('active-symbol-spread');

            const spec = SYMBOL_SPECS[tick.symbol] || { decimals: 2, pip: 0.10 };
            const spreadPips = ((tick.ask - tick.bid) / spec.pip).toFixed(1);

            if (bidEl) bidEl.textContent = tick.bid.toFixed(spec.decimals);
            if (askEl) askEl.textContent = tick.ask.toFixed(spec.decimals);
            if (spreadEl) spreadEl.textContent = `${spreadPips} pips`;
        }

        // =========================================================================
        // 3. Interactive Open Positions Table with 1-Click Execution
        // =========================================================================

        renderPositionsTable(positions = []) {
            const tbody = document.getElementById('positions-tbody');
            const countBadge = document.getElementById('pos-count-badge');

            if (countBadge) {
                countBadge.textContent = positions.length;
            }

            if (!tbody) return;

            if (positions.length === 0) {
                tbody.innerHTML = `
                    <tr class="empty-row">
                        <td colspan="10" class="text-center text-muted">
                            <div class="empty-state">
                                <span class="empty-icon">📂</span>
                                <p>No open positions in active portfolio</p>
                            </div>
                        </td>
                    </tr>
                `;
                return;
            }

            let html = '';
            positions.forEach(pos => {
                const spec = SYMBOL_SPECS[pos.symbol] || { decimals: 2, pip: 0.10 };
                const isBuy = pos.type === 'BUY';
                const typeClass = isBuy ? 'badge-buy' : 'badge-sell';
                const pnlClass = pos.profit >= 0 ? 'text-bullish' : 'text-bearish';
                const sign = pos.profit >= 0 ? '+' : '';

                // Calculate pips
                const diff = isBuy ? (pos.price_current - pos.price_open) : (pos.price_open - pos.price_current);
                const pips = (diff / spec.pip).toFixed(1);

                html += `
                    <tr class="pos-row" id="pos-row-${pos.ticket}" data-ticket="${pos.ticket}" data-symbol="${pos.symbol}">
                        <td class="cell-ticket font-mono">#${pos.ticket}</td>
                        <td class="cell-symbol font-bold">${pos.symbol}</td>
                        <td class="cell-type"><span class="badge ${typeClass}">${pos.type}</span></td>
                        <td class="cell-volume font-mono">${pos.volume.toFixed(2)}</td>
                        <td class="cell-open font-mono">${pos.price_open.toFixed(spec.decimals)}</td>
                        <td class="cell-mark font-mono" id="mark-${pos.ticket}">${pos.price_current.toFixed(spec.decimals)}</td>
                        <td class="cell-sl">
                            <input type="number" step="any" class="input-inline-sl font-mono" 
                                   id="sl-input-${pos.ticket}" data-ticket="${pos.ticket}" 
                                   value="${pos.sl ? pos.sl.toFixed(spec.decimals) : '0.00'}" />
                        </td>
                        <td class="cell-tp">
                            <input type="number" step="any" class="input-inline-tp font-mono" 
                                   id="tp-input-${pos.ticket}" data-ticket="${pos.ticket}" 
                                   value="${pos.tp ? pos.tp.toFixed(spec.decimals) : '0.00'}" />
                        </td>
                        <td class="cell-pnl font-mono ${pnlClass}" id="pnl-${pos.ticket}">
                            <div class="pnl-usd font-bold">${sign}$${pos.profit.toFixed(2)}</div>
                            <div class="pnl-pips text-dim">${sign}${pips} pips</div>
                        </td>
                        <td class="cell-actions">
                            <div class="btn-group-actions">
                                <button class="btn-action btn-scale-out" title="1-Click 50% Scale-Out & Lock BE" data-ticket="${pos.ticket}">
                                    ✂ 50%
                                </button>
                                <button class="btn-action btn-breakeven" title="Instant Breakeven+ (2 Pips)" data-ticket="${pos.ticket}">
                                    🛡 BE+
                                </button>
                                <button class="btn-action btn-modify" title="Apply SL/TP Changes" data-ticket="${pos.ticket}">
                                    💾 Save
                                </button>
                                <button class="btn-action btn-close-pos" title="1-Click Liquidate" data-ticket="${pos.ticket}">
                                    ✕ Close
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
            this._attachPositionActionHandlers();
        }

        _attachPositionActionHandlers() {
            // 1. 50% Scale-Out Button
            document.querySelectorAll('.btn-scale-out').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const ticket = parseInt(btn.getAttribute('data-ticket'), 10);
                    if (this.core) {
                        btn.disabled = true;
                        btn.textContent = '...';
                        const res = await this.core.scaleOut(ticket, 0.5, 2.0);
                        if (res && res.success) {
                            this.logSystem(`Executed 50% Scale-Out on #${ticket}. SL secured to Breakeven.`, 'TRADE');
                            this._showToast(`Scaled out 50% on #${ticket}`, 'success');
                        } else {
                            this._showToast(res.message || 'Scale out failed', 'error');
                        }
                        btn.disabled = false;
                        btn.textContent = '✂ 50%';
                    }
                });
            });

            // 2. Breakeven+ Button
            document.querySelectorAll('.btn-breakeven').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const ticket = parseInt(btn.getAttribute('data-ticket'), 10);
                    if (this.core) {
                        btn.disabled = true;
                        btn.textContent = '...';
                        const res = await this.core.breakeven(ticket, 2.0);
                        if (res && res.success) {
                            this.logSystem(`Locked Breakeven on #${ticket} with 2 pips buffer.`, 'TRADE');
                            this._showToast(`Breakeven locked on #${ticket}`, 'success');
                        } else {
                            this._showToast(res.message || 'Breakeven lock failed', 'error');
                        }
                        btn.disabled = false;
                        btn.textContent = '🛡 BE+';
                    }
                });
            });

            // 3. Save / Inline SL/TP Modify Button
            document.querySelectorAll('.btn-modify').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const ticket = parseInt(btn.getAttribute('data-ticket'), 10);
                    const slInput = document.getElementById(`sl-input-${ticket}`);
                    const tpInput = document.getElementById(`tp-input-${ticket}`);

                    if (slInput && tpInput && this.core) {
                        const sl = parseFloat(slInput.value);
                        const tp = parseFloat(tpInput.value);
                        btn.disabled = true;
                        const res = await this.core.modifySLTP(ticket, sl, tp);
                        if (res && res.success) {
                            this.logSystem(`Modified SL=${sl}, TP=${tp} on #${ticket}`, 'TRADE');
                            this._showToast(`SL/TP updated on #${ticket}`, 'success');
                        } else {
                            this._showToast(res.message || 'Modify failed', 'error');
                        }
                        btn.disabled = false;
                    }
                });
            });

            // 4. Inline SL/TP Enter Key Commit
            document.querySelectorAll('.input-inline-sl, .input-inline-tp').forEach(input => {
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        const ticket = parseInt(input.getAttribute('data-ticket'), 10);
                        const saveBtn = document.querySelector(`.btn-modify[data-ticket="${ticket}"]`);
                        if (saveBtn) saveBtn.click();
                    }
                });
            });

            // 5. 1-Click Close Position Button
            document.querySelectorAll('.btn-close-pos').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const ticket = parseInt(btn.getAttribute('data-ticket'), 10);
                    if (this.core) {
                        btn.disabled = true;
                        btn.textContent = '...';
                        const res = await this.core.closePosition(ticket);
                        if (res && res.success) {
                            this.logSystem(`Liquidated position #${ticket}`, 'TRADE');
                            this._showToast(`Position #${ticket} liquidated`, 'info');
                        } else {
                            this._showToast(res.message || 'Close failed', 'error');
                        }
                        btn.disabled = false;
                        btn.textContent = '✕ Close';
                    }
                });
            });
        }

        _updatePositionsMarkToMarket(tick) {
            const positions = (this.core && this.core.state.positions) || [];
            let totalFloatingPnL = 0.0;

            positions.forEach(pos => {
                if (pos.symbol === tick.symbol) {
                    pos.price_current = tick.last;
                    const spec = SYMBOL_SPECS[pos.symbol] || { decimals: 2, pip: 0.10, contract: 100.0 };
                    const isBuy = pos.type === 'BUY';
                    const diff = isBuy ? (tick.last - pos.price_open) : (pos.price_open - tick.last);
                    const pnl = parseFloat((diff * spec.contract * pos.volume).toFixed(2));
                    pos.profit = pnl;

                    // Update DOM cell if present
                    const markEl = document.getElementById(`mark-${pos.ticket}`);
                    const pnlEl = document.getElementById(`pnl-${pos.ticket}`);

                    if (markEl) markEl.textContent = tick.last.toFixed(spec.decimals);
                    if (pnlEl) {
                        const sign = pnl >= 0 ? '+' : '';
                        const pips = (diff / spec.pip).toFixed(1);
                        pnlEl.className = `cell-pnl font-mono ${pnl >= 0 ? 'text-bullish' : 'text-bearish'}`;
                        pnlEl.innerHTML = `
                            <div class="pnl-usd font-bold">${sign}$${pnl.toFixed(2)}</div>
                            <div class="pnl-pips text-dim">${sign}${pips} pips</div>
                        `;
                    }
                }
                totalFloatingPnL += (pos.profit || 0.0);
            });

            // Update floating PnL on Risk Cockpit
            if (this.riskCockpit) {
                const bal = this.core ? this.core.state.account.balance : 25000.0;
                this.riskCockpit.updateAccount(bal, bal + totalFloatingPnL);
            }
        }

        // =========================================================================
        // 4. Modal Dialogs & Emergency Kill Switch
        // =========================================================================

        _bindModalControls() {
            const killBtn = document.getElementById('btn-emergency-kill');
            const killModal = document.getElementById('kill-switch-modal');
            const cancelBtn = document.getElementById('btn-modal-cancel-kill');
            const confirmBtn = document.getElementById('btn-modal-confirm-kill');

            if (killBtn && killModal) {
                killBtn.addEventListener('click', () => {
                    killModal.classList.add('active');
                });
            }

            if (cancelBtn && killModal) {
                cancelBtn.addEventListener('click', () => {
                    killModal.classList.remove('active');
                });
            }

            if (confirmBtn && killModal) {
                confirmBtn.addEventListener('click', async () => {
                    killModal.classList.remove('active');
                    if (this.core) {
                        confirmBtn.disabled = true;
                        const res = await this.core.killSwitch('Emergency Panic Button Triggered', true);
                        confirmBtn.disabled = false;
                        if (res && res.success) {
                            this.logSystem(`EMERGENCY CIRCUIT BREAKER ACTIVATED: ${res.message}`, 'CRITICAL');
                            this._showToast('EMERGENCY STOP TRIGGERED: All positions liquidated!', 'critical');
                        }
                    }
                });
            }
        }

        // =========================================================================
        // 5. Left Pane: 5-Level DOM Ladder & Quick Order Entry
        // =========================================================================

        _renderDOMOrderBook(dom) {
            const bidsContainer = document.getElementById('dom-bids');
            const asksContainer = document.getElementById('dom-asks');
            const buyerPctEl = document.getElementById('dom-buyer-pct');
            const sellerPctEl = document.getElementById('dom-seller-pct');
            const ratioBar = document.getElementById('dom-ratio-bar');

            if (buyerPctEl) buyerPctEl.textContent = `${dom.buyer_ratio}%`;
            if (sellerPctEl) sellerPctEl.textContent = `${dom.seller_ratio}%`;
            if (ratioBar) ratioBar.style.width = `${dom.buyer_ratio}%`;

            const spec = SYMBOL_SPECS[dom.symbol] || { decimals: 2 };

            if (bidsContainer && Array.isArray(dom.bids)) {
                let bidsHtml = '';
                const maxVol = Math.max(...dom.bids.map(b => b.volume), 1);
                dom.bids.forEach(b => {
                    const fillPct = (b.volume / maxVol) * 100;
                    bidsHtml += `
                        <div class="dom-row dom-bid-row">
                            <div class="dom-depth-bar bg-bullish" style="width: ${fillPct}%"></div>
                            <span class="dom-price text-bullish font-mono">${b.price.toFixed(spec.decimals)}</span>
                            <span class="dom-vol font-mono">${b.volume.toFixed(1)}</span>
                        </div>
                    `;
                });
                bidsContainer.innerHTML = bidsHtml;
            }

            if (asksContainer && Array.isArray(dom.asks)) {
                let asksHtml = '';
                const maxVol = Math.max(...dom.asks.map(a => a.volume), 1);
                dom.asks.forEach(a => {
                    const fillPct = (a.volume / maxVol) * 100;
                    asksHtml += `
                        <div class="dom-row dom-ask-row">
                            <div class="dom-depth-bar bg-bearish" style="width: ${fillPct}%"></div>
                            <span class="dom-price text-bearish font-mono">${a.price.toFixed(spec.decimals)}</span>
                            <span class="dom-vol font-mono">${a.volume.toFixed(1)}</span>
                        </div>
                    `;
                });
                asksContainer.innerHTML = asksHtml;
            }
        }

        _bindOrderEntryForm() {
            const btnBuy = document.getElementById('btn-order-buy');
            const btnSell = document.getElementById('btn-order-sell');
            const volInput = document.getElementById('order-volume');

            if (btnBuy) {
                btnBuy.addEventListener('click', () => {
                    const vol = parseFloat(volInput ? volInput.value : 0.5) || 0.5;
                    this.logSystem(`Quick BUY order submitted for ${vol} lots on ${this.activeSymbol}`, 'TRADE');
                    this._showToast(`Market BUY ${vol} ${this.activeSymbol} executed`, 'success');
                });
            }

            if (btnSell) {
                btnSell.addEventListener('click', () => {
                    const vol = parseFloat(volInput ? volInput.value : 0.5) || 0.5;
                    this.logSystem(`Quick SELL order submitted for ${vol} lots on ${this.activeSymbol}`, 'TRADE');
                    this._showToast(`Market SELL ${vol} ${this.activeSymbol} executed`, 'success');
                });
            }
        }

        // =========================================================================
        // 6. Center Pane: Lightweight Chart, SMC Overlays & CVD Pane
        // =========================================================================

        _initChartAndRenderers() {
            const chartContainer = document.getElementById('candlestick-chart-container');
            const cvdContainer = document.getElementById('cvd-pane-container');

            const CEClass = this.ChartEngineClass || (typeof window !== 'undefined' ? window.ChartEngine : null);
            const SMCClass = this.SMCOverlaysClass || (typeof window !== 'undefined' ? window.SMCOverlaysRenderer : null);
            const CVDClass = this.CVDPaneClass || (typeof window !== 'undefined' ? window.CVDPaneRenderer : null);

            if (chartContainer && CEClass) {
                try {
                    this.chartEngine = new CEClass(chartContainer, {
                        symbol: this.activeSymbol,
                        timeframe: this.activeTimeframe,
                        mode: 'auto'
                    });
                } catch (e) {
                    console.warn('[TerminalApp] ChartEngine init error:', e);
                }
            }

            if (chartContainer && this.chartEngine && SMCClass) {
                try {
                    this.smcRenderer = new SMCClass(chartContainer, this.chartEngine, {
                        autoAttachControls: false
                    });
                } catch (e) {
                    console.warn('[TerminalApp] SMCOverlaysRenderer init error:', e);
                }
            }

            if (cvdContainer && CVDClass) {
                try {
                    this.cvdRenderer = new CVDClass(cvdContainer, this.chartEngine, {
                        symbol: this.activeSymbol,
                        height: 85,
                        showDOM: false
                    });
                } catch (e) {
                    console.warn('[TerminalApp] CVDPaneRenderer init error:', e);
                }
            }

            // Sync global references
            if (typeof window !== 'undefined' && window.TradingTerminal) {
                window.TradingTerminal.chartEngine = this.chartEngine;
                window.TradingTerminal.smcRenderer = this.smcRenderer;
                window.TradingTerminal.cvdRenderer = this.cvdRenderer;
            }

            // Fallback for direct LightweightCharts reference if ChartEngine was not available
            if (this.chartEngine) {
                this.chartInstance = this.chartEngine.tvChart || this.chartEngine.canvasChart;
                this.candleSeries = this.chartEngine.candlestickSeries;
            } else {
                this._initLightweightChart();
            }
        }

        _initLightweightChart() {
            const container = document.getElementById('candlestick-chart-container');
            if (!container) return;

            if (typeof LightweightCharts !== 'undefined') {
                try {
                    this.chartInstance = LightweightCharts.createChart(container, {
                        width: container.clientWidth || 800,
                        height: container.clientHeight || 450,
                        layout: {
                            background: { color: '#0a0e17' },
                            textColor: '#94a3b8'
                        },
                        grid: {
                            vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
                            horzLines: { color: 'rgba(255, 255, 255, 0.04)' }
                        },
                        crosshair: {
                            mode: LightweightCharts.CrosshairMode.Normal
                        },
                        rightPriceScale: {
                            borderColor: 'rgba(255, 255, 255, 0.1)'
                        },
                        timeScale: {
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            timeVisible: true
                        }
                    });

                    this.candleSeries = this.chartInstance.addCandlestickSeries({
                        upColor: '#00e676',
                        downColor: '#ff3d71',
                        borderVisible: false,
                        wickUpColor: '#00e676',
                        wickDownColor: '#ff3d71'
                    });

                    // Resize observer
                    if (window.ResizeObserver) {
                        new ResizeObserver(entries => {
                            if (entries[0] && entries[0].contentRect) {
                                this.chartInstance.applyOptions({
                                    width: entries[0].contentRect.width,
                                    height: entries[0].contentRect.height
                                });
                            }
                        }).observe(container);
                    }
                } catch (err) {
                    console.warn('[TerminalApp] LightweightCharts init exception:', err);
                }
            }
        }

        _updateChartCandle(candle) {
            if (this.candleSeries && candle) {
                try {
                    this.candleSeries.update({
                        time: candle.time,
                        open: candle.open,
                        high: candle.high,
                        low: candle.low,
                        close: candle.close
                    });
                } catch (e) {}
            }
        }

        _renderSMCOverlays(smc) {
            if (!smc) return;

            const fvgCountEl = document.getElementById('smc-fvg-count');
            const obCountEl = document.getElementById('smc-ob-count');
            const trendEl = document.getElementById('smc-trend-badge');
            const oteLevelEl = document.getElementById('smc-ote-level');

            if (fvgCountEl && Array.isArray(smc.fvgs)) {
                fvgCountEl.textContent = smc.fvgs.length;
            }
            if (obCountEl && Array.isArray(smc.order_blocks)) {
                obCountEl.textContent = smc.order_blocks.length;
            }
            if (trendEl && smc.ote) {
                trendEl.textContent = smc.ote.trend || 'BULLISH';
                trendEl.className = `badge ${smc.ote.trend === 'BULLISH' ? 'badge-buy' : 'badge-sell'}`;
            }
            if (oteLevelEl && smc.ote && smc.ote.levels) {
                oteLevelEl.textContent = `Sweet Spot 70.5%: ${smc.ote.levels.sweet_spot_705 || '0.00'}`;
            }
        }

        _renderCVD(cvd) {
            if (!cvd) return;

            const cumEl = document.getElementById('cvd-cumulative-val');
            const buyerPctEl = document.getElementById('cvd-buyer-pct');
            const sellerPctEl = document.getElementById('cvd-seller-pct');
            const divBadge = document.getElementById('cvd-divergence-badge');
            const ratioBar = document.getElementById('cvd-ratio-fill');

            if (cumEl) cumEl.textContent = cvd.cumulative || 0;
            if (buyerPctEl) buyerPctEl.textContent = `${cvd.buyer_pct || 50}%`;
            if (sellerPctEl) sellerPctEl.textContent = `${cvd.seller_pct || 50}%`;
            if (ratioBar) ratioBar.style.width = `${cvd.buyer_pct || 50}%`;

            if (divBadge) {
                const divType = cvd.divergence || 'NONE';
                divBadge.textContent = divType.replace('_', ' ');
                divBadge.className = `status-badge ${divType.includes('BULLISH') ? 'badge-buy' : divType.includes('BEARISH') ? 'badge-sell' : 'badge-neutral'}`;
            }
        }

        // =========================================================================
        // 7. Bottom Navigation Tabs & System Logs
        // =========================================================================

        _bindBottomTabs() {
            const tabs = document.querySelectorAll('.bottom-tab-btn');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    const targetPane = tab.getAttribute('data-pane');
                    tabs.forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');

                    document.querySelectorAll('.bottom-pane-content').forEach(p => {
                        p.classList.toggle('active', p.id === targetPane);
                    });
                });
            });
        }

        logSystem(message, level = 'INFO') {
            const entry = {
                timestamp: new Date().toLocaleTimeString(),
                level: level,
                message: message
            };
            this.systemLogs.push(entry);
            if (this.systemLogs.length > 200) this.systemLogs.shift();

            const container = document.getElementById('system-logs-container');
            if (container) {
                const row = document.createElement('div');
                row.className = `log-line log-${level.toLowerCase()}`;
                row.innerHTML = `
                    <span class="log-time font-mono">[${entry.timestamp}]</span>
                    <span class="log-level font-bold font-mono">[${entry.level}]</span>
                    <span class="log-msg">${entry.message}</span>
                `;
                container.prepend(row);
            }
        }

        _showToast(message, type = 'info') {
            const toastContainer = document.getElementById('toast-container');
            if (!toastContainer) return;

            const toast = document.createElement('div');
            toast.className = `toast-message toast-${type}`;
            toast.textContent = message;

            toastContainer.appendChild(toast);
            setTimeout(() => {
                toast.classList.add('fade-out');
                setTimeout(() => toast.remove(), 400);
            }, 3000);
        }

        // =========================================================================
        // 8. World Monitor Geopolitical Radar Handlers
        // =========================================================================

        async _initWorldMonitor() {
            // Wire quick card button
            const openFullBtn = document.getElementById('btn-open-world-monitor-tab');
            if (openFullBtn) {
                openFullBtn.addEventListener('click', () => {
                    const tabBtn = document.getElementById('tab-btn-world-monitor');
                    if (tabBtn) tabBtn.click();
                });
            }

            // Fetch initial REST data
            try {
                const res = await fetch('/api/world_monitor');
                if (res.ok) {
                    const data = await res.json();
                    this._renderWorldMonitor(data);
                }
            } catch (e) {
                console.warn('[TerminalApp] World Monitor initial fetch note:', e);
            }
        }

        _renderWorldMonitor(data) {
            if (!data) return;

            // 1. Threat Level & Composite Index
            const threatLevel = data.global_threat_level || 'DEFCON 3 (74.8/100)';
            const riskIndex = data.global_risk_index || 74.8;
            const hotspot = data.primary_geopolitical_hotspot || 'Middle East & Red Sea Corridor';

            // Quick card in right pane
            const qThreat = document.getElementById('wm-badge-threat');
            const qRisk = document.getElementById('wm-val-risk-index');
            const qHotspot = document.getElementById('wm-val-hotspot');
            const qFill = document.getElementById('wm-threat-gauge-fill');
            const tabBadge = document.getElementById('wm-tab-badge');

            if (qThreat) qThreat.textContent = threatLevel.split(' ')[0] || 'DEFCON 3';
            if (qRisk) qRisk.textContent = `${riskIndex.toFixed(1)} / 100`;
            if (qHotspot) qHotspot.textContent = hotspot.replace(/_/g, ' ');
            if (qFill) qFill.style.width = `${Math.min(100, riskIndex)}%`;
            if (tabBadge) tabBadge.textContent = threatLevel.split(' ')[0] || 'DEFCON 3';

            // Full panel in bottom tab
            const fullShield = document.getElementById('wm-defcon-shield');
            const fullScore = document.getElementById('wm-full-score');
            const fullHotspot = document.getElementById('wm-full-hotspot');
            const fullGauge = document.getElementById('wm-full-gauge-bar');
            const lastUpdated = document.getElementById('wm-last-updated');

            if (fullShield) fullShield.textContent = threatLevel.split('(')[0].trim() || 'DEFCON 3';
            if (fullScore) fullScore.innerHTML = `${riskIndex.toFixed(1)} <span class="text-dim">/ 100 (HIGH ELEVATION)</span>`;
            if (fullHotspot) fullHotspot.textContent = `PRIMARY FLASHPOINT: ${hotspot.replace(/_/g, ' ')}`;
            if (fullGauge) fullGauge.style.width = `${Math.min(100, riskIndex)}%`;
            if (lastUpdated && data.timestamp) lastUpdated.textContent = `Last Intelligence Frame: ${new Date(data.timestamp).toLocaleTimeString()}`;

            // 2. Market Shock Biases
            const biases = data.market_bias || {};
            const bXau = document.getElementById('bias-xau');
            const bWti = document.getElementById('bias-wti');
            const bBtc = document.getElementById('bias-btc');
            const bJpy = document.getElementById('bias-usdjpy');
            const bEur = document.getElementById('bias-eurusd');

            if (bXau && biases.XAUUSD) bXau.textContent = `${biases.XAUUSD > 0 ? '+' : ''}${biases.XAUUSD}x BULLISH`;
            if (bWti && biases.WTI) bWti.textContent = `${biases.WTI > 0 ? '+' : ''}${biases.WTI}x SPIKE`;
            if (bBtc && biases.BTCUSD) bBtc.textContent = `${biases.BTCUSD > 0 ? '+' : ''}${biases.BTCUSD}x LIQUIDITY`;
            if (bJpy && biases.USDJPY) bJpy.textContent = `${biases.USDJPY > 0 ? '+' : ''}${biases.USDJPY}x FLIGHT`;
            if (bEur && biases.EURUSD) bEur.textContent = `${biases.EURUSD > 0 ? '+' : ''}${biases.EURUSD}x DRAG`;

            // 3. 5 Maritime Chokepoints
            const chokepointsContainer = document.getElementById('wm-chokepoints-container');
            if (chokepointsContainer && Array.isArray(data.chokepoints)) {
                let cpHTML = '';
                data.chokepoints.forEach(cp => {
                    const riskClass = cp.risk_level.includes('CRITICAL') ? 'badge-critical' :
                                      cp.risk_level.includes('ELEVATED') ? 'badge-elevated' :
                                      cp.risk_level.includes('TENSION') ? 'badge-tension' :
                                      cp.risk_level.includes('STABLE') ? 'badge-stable' : 'badge-moderate';
                    cpHTML += `
                        <div class="wm-chokepoint-card">
                            <div class="wm-chokepoint-header">
                                <span class="wm-chokepoint-name">${cp.name}</span>
                                <span class="badge ${riskClass}">${cp.risk_level.replace(/_/g, ' ')}</span>
                            </div>
                            <div class="wm-chokepoint-narrative">${cp.status}</div>
                            <div class="wm-chokepoint-flow">Global Oil Flow: ${cp.global_oil_pct}%</div>
                        </div>
                    `;
                });
                chokepointsContainer.innerHTML = cpHTML;
            }

            // 4. Country Instability Index (CII v8)
            const ciiContainer = document.getElementById('wm-cii-container');
            if (ciiContainer && data.country_instability) {
                let ciiHTML = '';
                Object.entries(data.country_instability).forEach(([region, score]) => {
                    const numScore = typeof score === 'object' ? (score.score || 50) : Number(score);
                    const status = typeof score === 'object' ? (score.status || 'ELEVATED') : (numScore >= 80 ? 'CRITICAL' : numScore >= 70 ? 'HIGH TENSION' : numScore >= 50 ? 'ELEVATED' : 'MODERATE');
                    const fillClass = numScore >= 80 ? 'bg-bearish' : numScore >= 60 ? 'bg-warning' : 'bg-bullish';
                    ciiHTML += `
                        <div class="wm-cii-card">
                            <div class="wm-cii-header">
                                <span class="font-bold">${region.replace(/_/g, ' ')}</span>
                                <span class="font-mono ${numScore >= 75 ? 'text-bearish' : 'text-bullish'}">${numScore.toFixed(1)} / 100 (${status})</span>
                            </div>
                            <div class="wm-cii-bar-bg">
                                <div class="wm-cii-bar-fill ${fillClass}" style="width: ${Math.min(100, numScore)}%;"></div>
                            </div>
                        </div>
                    `;
                });
                ciiContainer.innerHTML = ciiHTML;
            }

            // 5. Live Geopolitical OSINT Alerts Stream
            const osintStream = document.getElementById('wm-osint-stream');
            if (osintStream && Array.isArray(data.osint_alerts)) {
                let osintHTML = '';
                data.osint_alerts.forEach(alert => {
                    osintHTML += `
                        <div class="wm-osint-card">
                            <div class="wm-osint-header">
                                <span class="wm-osint-region">📍 ${alert.region}</span>
                                <span class="badge ${alert.severity === 'CRITICAL' ? 'badge-critical' : 'badge-elevated'}">${alert.severity}</span>
                            </div>
                            <div class="wm-osint-headline font-bold">${alert.headline}</div>
                            <div class="wm-osint-effect">💡 Impact: ${alert.market_effect}</div>
                        </div>
                    `;
                });
                osintStream.innerHTML = osintHTML;
            }
        }
    }

    return TradingTerminalApp;
}));
