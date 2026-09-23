/**
 * smc_overlays.js — Institutional Smart Money Concepts (SMC) Canvas Rendering Engine (Milestone M3)
 * 
 * Synchronizes transparent HTML5 Canvas layer over ChartEngine to render:
 *   1. Fair Value Gaps (FVG) with 50% Consequent Encroachment (CE) dashed midlines & mitigation tracking.
 *   2. Institutional Order Blocks (OB) Demand & Supply zones with touch counters (TAPS).
 *   3. Optimal Trade Entry (OTE) 62% - 79% Fibonacci grids highlighting 70.5% Institutional Sweet Spot.
 *   4. Liquidity Sweeps & Stop-Hunt markers with neon lightning ⚡ HUD badges.
 *   5. Interbank IPDA Session Killzones (London Open, NY AM, NY PM, Asian Range).
 *   6. Dynamic Layer Visibility Toggles & Opacity Controls.
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
            autoAttachControls: false
        }, options);

        // SMC State Data Store
        this.smcData = {
            symbol: 'XAUUSD',
            timeframe: 'M15',
            fvgs: [],
            order_blocks: [],
            ote: null,
            sweeps: [],
            killzones: []
        };

        // Layer Visibility Toggles
        this.layers = {
            fvg: true,
            fvgCe: true,
            ob: true,
            ote: true,
            sweeps: true,
            killzones: true
        };
        this.globalOpacity = this.options.globalOpacity;

        // Overlay Canvas Setup
        this.canvas = document.createElement('canvas');
        this.canvas.className = 'smc-canvas-overlay';
        this.canvas.style.position = 'absolute';
        this.canvas.style.left = '0';
        this.canvas.style.top = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none'; // Pass mouse events through to chart engine
        this.canvas.style.zIndex = '2';
        this.container.appendChild(this.canvas);

        this.ctx = this.canvas.getContext('2d');
        this.dpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;
        this.renderPending = false;

        this._initResizeObserver();
        this._bindChartEvents();
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

        // Clear transparent canvas
        ctx.clearRect(0, 0, w, h);

        ctx.save();
        ctx.globalAlpha = this.globalOpacity;

        // Layer 1: Interbank IPDA Session Killzones (Background Shading)
        if (this.layers.killzones) {
            this._renderKillzones(ctx, w, h);
        }

        // Layer 2: Fair Value Gaps (FVG) with 50% CE Lines
        if (this.layers.fvg) {
            this._renderFVGs(ctx, w, h);
        }

        // Layer 3: Institutional Order Blocks (OB)
        if (this.layers.ob) {
            this._renderOrderBlocks(ctx, w, h);
        }

        // Layer 4: Optimal Trade Entry (OTE) Fibonacci Grids
        if (this.layers.ote) {
            this._renderOTEGrid(ctx, w, h);
        }

        // Layer 5: Liquidity Sweeps & Stop-Hunt Markers
        if (this.layers.sweeps) {
            this._renderSweeps(ctx, w, h);
        }

        ctx.restore();
    }

    _renderKillzones(ctx, w, h) {
        const killzones = this.smcData.killzones || [];
        const range = this.chart.getVisibleRange ? this.chart.getVisibleRange() : { from: null, to: null };

        // Standard IPDA Killzone definition time bounds
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

                // Background column
                ctx.fillStyle = kz.color;
                ctx.fillRect(xStart, 0, colW, h);

                // Border lines
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

                // Killzone top label
                if (colW > 35) {
                    ctx.font = '8px "JetBrains Mono", monospace';
                    ctx.fillStyle = kz.stroke;
                    ctx.textAlign = 'left';
                    ctx.fillText(kz.label, xStart + 4, 14);
                }
            }
        }
    }

    _renderFVGs(ctx, w, h) {
        const fvgs = this.smcData.fvgs || [];
        const rightEdgeX = w - 65; // Align with price scale axis padding

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
                if (rawXEnd !== null) {
                    xEnd = rawXEnd;
                }
            }

            if (xEnd < 0 || xStart > w) continue;

            const boxY = Math.min(yTop, yBottom);
            const boxHeight = Math.max(Math.abs(yBottom - yTop), 2);
            const boxWidth = Math.max(xEnd - xStart, 20);

            const isBullish = String(fvg.type).toUpperCase().includes('BULLISH');
            const baseColor = isBullish ? '16, 185, 129' : '239, 68, 68';

            // 1. Shaded Box Fill
            ctx.fillStyle = fvg.mitigated
                ? `rgba(${baseColor}, 0.04)`
                : `rgba(${baseColor}, 0.14)`;
            ctx.fillRect(xStart, boxY, boxWidth, boxHeight);

            // 2. Box Border
            ctx.strokeStyle = fvg.mitigated
                ? `rgba(${baseColor}, 0.20)`
                : `rgba(${baseColor}, 0.55)`;
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

                // 50% CE Price Tag Pill
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
        }
    }

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
                if (rawXEnd !== null) {
                    xEnd = rawXEnd;
                }
            }

            if (xEnd < 0 || xStart > w) continue;

            const boxY = Math.min(yTop, yBottom);
            const boxHeight = Math.max(Math.abs(yBottom - yTop), 3);
            const boxWidth = Math.max(xEnd - xStart, 25);

            const isDemand = String(ob.type).toUpperCase().includes('BULLISH');
            const baseColor = isDemand ? '16, 185, 129' : '239, 68, 68';
            const solidColor = isDemand ? '#10B981' : '#EF4444';

            // 1. Order Block Background Fill
            ctx.fillStyle = ob.mitigated
                ? `rgba(${baseColor}, 0.05)`
                : `rgba(${baseColor}, 0.16)`;
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
        }
    }

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

        // 1. Golden Pocket Ribbon (Gradient from 61.8% to 78.6%)
        const ribbonTop = Math.min(y618, y786);
        const ribbonHeight = Math.abs(y786 - y618);

        const gradient = ctx.createLinearGradient(0, ribbonTop, 0, ribbonTop + ribbonHeight);
        gradient.addColorStop(0, 'rgba(245, 158, 11, 0.08)');
        gradient.addColorStop(0.5, 'rgba(245, 158, 11, 0.24)'); // Peak golden glow at 70.5%
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
        ctx.strokeStyle = 'rgba(59, 130, 246, 0.75)'; // Blue
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.moveTo(xStart, y618);
        ctx.lineTo(xEnd, y618);
        ctx.stroke();
        ctx.setLineDash([]);
        this._drawOTELabel(ctx, `61.8% OTE (${levels.fib_618.toFixed(2)})`, xEnd - 130, y618 - 3, '#3B82F6');

        // 4. 78.6% Fibonacci Boundary Line
        ctx.strokeStyle = 'rgba(236, 72, 153, 0.75)'; // Pink
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 2]);
        ctx.beginPath();
        ctx.moveTo(xStart, y786);
        ctx.lineTo(xEnd, y786);
        ctx.stroke();
        ctx.setLineDash([]);
        this._drawOTELabel(ctx, `78.6% OTE (${levels.fib_786.toFixed(2)})`, xEnd - 130, y786 - 3, '#EC4899');

        // 5. 70.5% Institutional Sweet Spot Golden Line
        ctx.strokeStyle = '#F59E0B'; // Amber Gold
        ctx.lineWidth = 2;
        ctx.shadowColor = 'rgba(245, 158, 11, 0.60)';
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.moveTo(xStart, y705);
        ctx.lineTo(xEnd, y705);
        ctx.stroke();
        ctx.shadowBlur = 0; // Reset shadow

        // 70.5% Sweet Spot Badge
        const sweetSpotText = `★ 70.5% SWEET SPOT (${levels.sweet_spot_705.toFixed(2)})`;
        this._drawOTELabel(ctx, sweetSpotText, xEnd - 180, y705 - 4, '#F59E0B', true);
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

    createControlsHUD() {
        const hud = document.createElement('div');
        hud.className = 'smc-controls-hud';
        hud.style.position = 'absolute';
        hud.style.top = '10px';
        hud.style.left = '10px';
        hud.style.zIndex = '10';
        hud.style.display = 'flex';
        hud.style.gap = '6px';
        hud.style.background = 'rgba(15, 23, 42, 0.85)';
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
