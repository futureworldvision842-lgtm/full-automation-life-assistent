/**
 * cvd_pane.js — Institutional Cumulative Volume Delta (CVD) & Market Depth Sub-Pane (Milestone M3)
 * 
 * Synchronized lower analytics sub-pane rendering:
 *   1. Tick-by-tick Lee-Ready (1991) CVD histogram bars (emerald/rose) & glowing cyan cumulative curve (#00F2FE).
 *   2. Dynamic Buyer/Seller volume ratio gauge with surge detection.
 *   3. Real-time absorption divergence alert banner (Bullish/Bearish Absorption).
 *   4. 5-Level Depth of Market (DOM) order book ladder with spread counter and imbalance quotient.
 */

// Lee-Ready Tick Classifier (Standalone client-side quantitative classifier)
function classifyLeeReadyTick(price, bid, ask, lastPrice, lastDirection) {
    const mid = (bid + ask) / 2.0;
    if (price > mid) return 1;
    if (price < mid) return -1;
    if (lastPrice !== null && lastPrice !== undefined) {
        if (price > lastPrice) return 1;
        if (price < lastPrice) return -1;
    }
    return lastDirection ?? 1;
}

// Order Imbalance Quotient
function computeDOMImbalance(bids, asks) {
    const totalBid = bids.reduce((acc, b) => acc + (Number(b.volume ?? b[1]) || 0), 0);
    const totalAsk = asks.reduce((acc, a) => acc + (Number(a.volume ?? a[1]) || 0), 0);
    const total = Math.max(totalBid + totalAsk, 1.0);
    return {
        totalBid,
        totalAsk,
        quotient: Number((totalBid / total).toFixed(4)),
        bidPct: Number(((totalBid / total) * 100).toFixed(1)),
        askPct: Number(((totalAsk / total) * 100).toFixed(1))
    };
}

class CVDPaneRenderer {
    constructor(containerElement, chartEngineInstance = null, options = {}) {
        this.container = typeof containerElement === 'string' ? document.getElementById(containerElement) : containerElement;
        if (!this.container) {
            throw new Error(`CVDPaneRenderer: Container element '${containerElement}' not found.`);
        }

        this.chart = chartEngineInstance;
        this.options = Object.assign({
            symbol: 'XAUUSD',
            height: 200,
            showDOM: true,
            apiBaseUrl: ''
        }, options);

        this.symbol = this.options.symbol.toUpperCase();
        this.cvdHistory = [];
        this.currentRatio = { buyer: 50.0, seller: 50.0 };
        this.divergence = { active: false, type: 'NONE', description: 'Synchronized order flow.' };
        this.domData = { bids: [], asks: [], spread_pips: 0.0, buyer_ratio: 50.0, seller_ratio: 50.0 };

        // Internal Lee-Ready state
        this.lastPrice = null;
        this.lastDirection = 1;
        this.cumulativeCVD = 0;

        // Subscriptions
        this.crosshair = { visible: false, x: -1, y: -1, point: null };

        this._buildDOMStructure();
        this._initCanvas();
        this._bindEvents();
    }

    _buildDOMStructure() {
        this.container.innerHTML = '';
        this.container.classList.add('cvd-pane-wrapper');
        this.container.style.display = 'flex';
        this.container.style.flexDirection = 'column';
        this.container.style.width = '100%';
        this.container.style.height = `${this.options.height}px`;
        this.container.style.background = '#0B0F19';
        this.container.style.borderTop = '1px solid rgba(255, 255, 255, 0.08)';
        this.container.style.boxSizing = 'border-box';
        this.container.style.position = 'relative';

        // 1. CVD Header & Ratio Toolbar
        this.headerEl = document.createElement('div');
        this.headerEl.className = 'cvd-header-toolbar';
        this.headerEl.style.display = 'flex';
        this.headerEl.style.alignItems = 'center';
        this.headerEl.style.justifyContent = 'space-between';
        this.headerEl.style.padding = '4px 12px';
        this.headerEl.style.background = 'rgba(15, 23, 42, 0.95)';
        this.headerEl.style.borderBottom = '1px solid rgba(255, 255, 255, 0.05)';
        this.headerEl.style.fontSize = '11px';
        this.headerEl.style.fontFamily = '"JetBrains Mono", monospace';
        this.headerEl.style.color = '#94A3B8';

        this.headerEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="color: #00F2FE; font-weight: bold;">📊 CVD & ORDER FLOW</span>
                <span id="cvd-cum-val" style="color: #F8FAFC;">CVD: +0</span>
                <span id="cvd-delta-val" style="color: #10B981;">(Δ: +0)</span>
            </div>
            <!-- Buyer/Seller Split Ratio Bar -->
            <div style="display: flex; align-items: center; gap: 8px; flex: 1; max-width: 320px; margin: 0 16px;">
                <span id="cvd-buyer-pct" style="color: #10B981; font-weight: bold; min-width: 45px;">50.0%</span>
                <div style="flex: 1; height: 6px; background: rgba(239, 68, 68, 0.7); border-radius: 3px; overflow: hidden; display: flex;">
                    <div id="cvd-ratio-fill" style="width: 50%; height: 100%; background: #10B981; transition: width 0.2s ease;"></div>
                </div>
                <span id="cvd-seller-pct" style="color: #EF4444; font-weight: bold; min-width: 45px; text-align: right;">50.0%</span>
            </div>
            <!-- Divergence / Surge Alert Badge -->
            <div id="cvd-alert-badge" style="display: none; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 10px;">
                ⚡ ABSORPTION DETECTED
            </div>
        `;
        this.container.appendChild(this.headerEl);

        // 2. Main Content Grid (Canvas on Left, DOM Ladder on Right)
        this.contentGrid = document.createElement('div');
        this.contentGrid.style.display = 'flex';
        this.contentGrid.style.flex = '1';
        this.contentGrid.style.position = 'relative';
        this.contentGrid.style.overflow = 'hidden';

        // Canvas container for CVD
        this.canvasContainer = document.createElement('div');
        this.canvasContainer.style.flex = '1';
        this.canvasContainer.style.position = 'relative';
        this.canvasContainer.style.height = '100%';
        this.contentGrid.appendChild(this.canvasContainer);

        // 5-Level DOM Panel Container
        this.domPanel = document.createElement('div');
        this.domPanel.className = 'cvd-dom-panel';
        this.domPanel.style.width = '240px';
        this.domPanel.style.height = '100%';
        this.domPanel.style.background = 'rgba(11, 15, 25, 0.95)';
        this.domPanel.style.borderLeft = '1px solid rgba(255, 255, 255, 0.08)';
        this.domPanel.style.padding = '4px 8px';
        this.domPanel.style.boxSizing = 'border-box';
        this.domPanel.style.fontSize = '10px';
        this.domPanel.style.fontFamily = '"JetBrains Mono", monospace';
        this.domPanel.style.overflowY = 'auto';

        this.domPanel.innerHTML = `
            <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 2px; margin-bottom: 4px;">
                <span style="color: #64748B;">LEVEL 2 DOM</span>
                <span id="dom-spread-badge" style="color: #F59E0B;">SPREAD: 0.0 pips</span>
            </div>
            <div id="dom-ladder-body">
                <div style="text-align: center; color: #64748B; padding: 12px 0;">Connecting DOM feed...</div>
            </div>
            <div style="margin-top: 4px; padding-top: 3px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; color: #64748B;">
                <span>IMBALANCE:</span>
                <span id="dom-imbalance-val" style="color: #00F2FE; font-weight: bold;">0.50</span>
            </div>
        `;
        this.contentGrid.appendChild(this.domPanel);

        this.container.appendChild(this.contentGrid);
    }

    _initCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.className = 'cvd-chart-canvas';
        this.canvas.style.position = 'absolute';
        this.canvas.style.left = '0';
        this.canvas.style.top = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvasContainer.appendChild(this.canvas);

        this.ctx = this.canvas.getContext('2d');
        this.dpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;

        this._initResizeObserver();
    }

    _initResizeObserver() {
        if (typeof ResizeObserver !== 'undefined') {
            this.resizeObserver = new ResizeObserver(() => this.handleResize());
            this.resizeObserver.observe(this.canvasContainer);
        }
        this.handleResize();
    }

    handleResize() {
        const rect = this.canvasContainer.getBoundingClientRect ? this.canvasContainer.getBoundingClientRect() : { width: 600, height: 160 };
        this.dpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;
        this.width = rect.width || 600;
        this.height = rect.height || 160;

        this.canvas.width = Math.round(this.width * this.dpr);
        this.canvas.height = Math.round(this.height * this.dpr);

        if (this.ctx) {
            this.ctx.setTransform(1, 0, 0, 1, 0, 0);
            this.ctx.scale(this.dpr, this.dpr);
        }

        this.requestRender();
    }

    _bindEvents() {
        if (this.chart && typeof this.chart.subscribeVisibleRangeChanged === 'function') {
            this.chart.subscribeVisibleRangeChanged(() => this.requestRender());
        }
        if (this.chart && typeof this.chart.subscribeCrosshairMove === 'function') {
            this.chart.subscribeCrosshairMove((param) => {
                this.crosshair = param || { visible: false };
                this.requestRender();
            });
        }
    }

    setData(data) {
        if (!data) return;
        if (Array.isArray(data)) {
            this.cvdHistory = data;
        } else if (data.cvd_history) {
            this.cvdHistory = data.cvd_history;
            if (data.current_ratio) this.currentRatio = data.current_ratio;
            if (data.divergence) this.divergence = data.divergence;
        }

        if (this.cvdHistory.length > 0) {
            const last = this.cvdHistory[this.cvdHistory.length - 1];
            this.cumulativeCVD = last.cumulative ?? 0;
        }

        this._updateHeaderMetrics();
        this.requestRender();
    }

    updateCVD(updatePacket) {
        if (!updatePacket) return;
        const delta = Number(updatePacket.tick_delta ?? updatePacket.delta ?? 0);
        const cumulative = Number(updatePacket.cumulative ?? (this.cumulativeCVD + delta));
        const buyerPct = Number(updatePacket.buyer_pct ?? updatePacket.buyer_ratio ?? this.currentRatio.buyer);
        const sellerPct = Number(updatePacket.seller_pct ?? updatePacket.seller_ratio ?? (100.0 - buyerPct));

        this.cumulativeCVD = cumulative;
        this.currentRatio = { buyer: buyerPct, seller: sellerPct };

        const nowSec = Math.floor(Date.now() / 1000);
        const newPoint = {
            time: Number(updatePacket.time || nowSec),
            delta: delta,
            cumulative: cumulative,
            buyer_ratio: buyerPct,
            volume: Math.abs(delta)
        };

        this.cvdHistory.push(newPoint);
        if (this.cvdHistory.length > 200) this.cvdHistory.shift();

        if (updatePacket.divergence) {
            const divType = String(updatePacket.divergence).toUpperCase();
            this.divergence = {
                active: divType !== 'NONE' && divType !== '',
                type: divType,
                description: `Absorption signal: ${divType}`
            };
        }

        this._updateHeaderMetrics();
        this.requestRender();
    }

    updateDOM(domPacket) {
        if (!domPacket) return;
        this.domData = domPacket;
        this._renderDOMTable();
    }

    onTick(tick) {
        if (!tick || tick.symbol !== this.symbol) return;
        const curP = Number(tick.last ?? tick.bid ?? 0);
        const bid = Number(tick.bid ?? curP);
        const ask = Number(tick.ask ?? curP);
        const vol = Number(tick.volume || 1);

        const direction = classifyLeeReadyTick(curP, bid, ask, this.lastPrice, this.lastDirection);
        this.lastDirection = direction;
        this.lastPrice = curP;

        const delta = direction * vol;
        this.cumulativeCVD += delta;

        // Shift ratio incrementally
        const weight = 0.05;
        const targetPct = direction > 0 ? 100 : 0;
        this.currentRatio.buyer = Math.round(((1 - weight) * this.currentRatio.buyer + weight * targetPct) * 10) / 10;
        this.currentRatio.seller = Math.round((100.0 - this.currentRatio.buyer) * 10) / 10;

        const nowSec = Math.floor(Date.now() / 1000);
        this.cvdHistory.push({
            time: nowSec,
            delta: delta,
            cumulative: this.cumulativeCVD,
            buyer_ratio: this.currentRatio.buyer,
            volume: vol
        });
        if (this.cvdHistory.length > 200) this.cvdHistory.shift();

        this._updateHeaderMetrics();
        this.requestRender();
    }

    _updateHeaderMetrics() {
        const cumEl = document.getElementById('cvd-cum-val');
        const deltaEl = document.getElementById('cvd-delta-val');
        const buyPctEl = document.getElementById('cvd-buyer-pct');
        const sellPctEl = document.getElementById('cvd-seller-pct');
        const ratioFillEl = document.getElementById('cvd-ratio-fill');
        const alertBadge = document.getElementById('cvd-alert-badge');

        if (cumEl) {
            cumEl.textContent = `CVD: ${this.cumulativeCVD >= 0 ? '+' : ''}${this.cumulativeCVD}`;
            cumEl.style.color = this.cumulativeCVD >= 0 ? '#10B981' : '#EF4444';
        }

        if (deltaEl && this.cvdHistory.length > 0) {
            const last = this.cvdHistory[this.cvdHistory.length - 1];
            const d = last.delta || 0;
            deltaEl.textContent = `(Δ: ${d >= 0 ? '+' : ''}${d})`;
            deltaEl.style.color = d >= 0 ? '#10B981' : '#EF4444';
        }

        if (buyPctEl && sellPctEl && ratioFillEl) {
            buyPctEl.textContent = `${this.currentRatio.buyer.toFixed(1)}%`;
            sellPctEl.textContent = `${this.currentRatio.seller.toFixed(1)}%`;
            ratioFillEl.style.width = `${Math.min(100, Math.max(0, this.currentRatio.buyer))}%`;
        }

        if (alertBadge) {
            if (this.divergence && this.divergence.active && this.divergence.type !== 'NONE') {
                alertBadge.style.display = 'block';
                const isBull = this.divergence.type.includes('BULLISH');
                alertBadge.style.background = isBull ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)';
                alertBadge.style.border = `1px solid ${isBull ? '#10B981' : '#EF4444'}`;
                alertBadge.style.color = isBull ? '#10B981' : '#EF4444';
                alertBadge.textContent = `⚡ ${this.divergence.type.replace('_', ' ')}`;
            } else if (this.currentRatio.buyer >= 65.0) {
                alertBadge.style.display = 'block';
                alertBadge.style.background = 'rgba(16, 185, 129, 0.2)';
                alertBadge.style.border = '1px solid #10B981';
                alertBadge.style.color = '#10B981';
                alertBadge.textContent = '🟢 BUY VOLUME SURGE';
            } else if (this.currentRatio.buyer <= 35.0) {
                alertBadge.style.display = 'block';
                alertBadge.style.background = 'rgba(239, 68, 68, 0.2)';
                alertBadge.style.border = '1px solid #EF4444';
                alertBadge.style.color = '#EF4444';
                alertBadge.textContent = '🔴 SELL VOLUME SURGE';
            } else {
                alertBadge.style.display = 'none';
            }
        }
    }

    _renderDOMTable() {
        const bodyEl = document.getElementById('dom-ladder-body');
        const spreadEl = document.getElementById('dom-spread-badge');
        const imbalanceEl = document.getElementById('dom-imbalance-val');
        if (!bodyEl) return;

        const bids = this.domData.bids || [];
        const asks = this.domData.asks || [];
        const spreadPips = this.domData.spread_pips ?? 0.0;

        if (spreadEl) spreadEl.textContent = `SPREAD: ${spreadPips.toFixed(1)} pips`;

        // Calculate max volume for relative depth bars
        let maxVol = 1.0;
        for (const b of bids) maxVol = Math.max(maxVol, Number(b.volume ?? b[1]) || 0);
        for (const a of asks) maxVol = Math.max(maxVol, Number(a.volume ?? a[1]) || 0);

        const imbalance = computeDOMImbalance(bids, asks);
        if (imbalanceEl) {
            imbalanceEl.textContent = `${imbalance.quotient.toFixed(2)} (${imbalance.bidPct}% Bids)`;
            imbalanceEl.style.color = imbalance.quotient >= 0.60 ? '#10B981' : (imbalance.quotient <= 0.40 ? '#EF4444' : '#00F2FE');
        }

        let html = '<div style="display: flex; flex-direction: column; gap: 2px;">';

        // Render Asks (Reverse so highest ask is at top)
        const sortedAsks = [...asks].slice(0, 5).reverse();
        for (const a of sortedAsks) {
            const p = Number(a.price ?? a[0]);
            const v = Number(a.volume ?? a[1]);
            const barW = Math.round((v / maxVol) * 100);
            html += `
                <div style="position: relative; display: flex; justify-content: space-between; padding: 1px 4px; background: rgba(239, 68, 68, 0.08); border-radius: 2px;">
                    <div style="position: absolute; right: 0; top: 0; bottom: 0; width: ${barW}%; background: rgba(239, 68, 68, 0.25); z-index: 0;"></div>
                    <span style="color: #EF4444; z-index: 1; font-weight: bold;">${p.toFixed(2)}</span>
                    <span style="color: #94A3B8; z-index: 1;">${v.toFixed(1)}</span>
                </div>
            `;
        }

        // Spread separator line
        html += `<div style="height: 1px; background: rgba(245, 158, 11, 0.4); margin: 2px 0;"></div>`;

        // Render Bids (Top bid first)
        const sortedBids = [...bids].slice(0, 5);
        for (const b of sortedBids) {
            const p = Number(b.price ?? b[0]);
            const v = Number(b.volume ?? b[1]);
            const barW = Math.round((v / maxVol) * 100);
            html += `
                <div style="position: relative; display: flex; justify-content: space-between; padding: 1px 4px; background: rgba(16, 185, 129, 0.08); border-radius: 2px;">
                    <div style="position: absolute; left: 0; top: 0; bottom: 0; width: ${barW}%; background: rgba(16, 185, 129, 0.25); z-index: 0;"></div>
                    <span style="color: #10B981; z-index: 1; font-weight: bold;">${p.toFixed(2)}</span>
                    <span style="color: #94A3B8; z-index: 1;">${v.toFixed(1)}</span>
                </div>
            `;
        }

        html += '</div>';
        bodyEl.innerHTML = html;
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
        if (!this.ctx || !this.width || !this.height) return;

        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;

        // Clear canvas
        ctx.fillStyle = '#0B0F19';
        ctx.fillRect(0, 0, w, h);

        if (this.cvdHistory.length === 0) {
            ctx.fillStyle = '#64748B';
            ctx.font = '11px "JetBrains Mono", monospace';
            ctx.textAlign = 'center';
            ctx.fillText('Accumulating real-time CVD stream...', w / 2, h / 2);
            return;
        }

        // Determine scaling ranges
        let maxDelta = 1;
        let minCVD = Infinity;
        let maxCVD = -Infinity;

        for (const pt of this.cvdHistory) {
            const d = Math.abs(pt.delta || 0);
            if (d > maxDelta) maxDelta = d;
            const c = pt.cumulative || 0;
            if (c < minCVD) minCVD = c;
            if (c > maxCVD) maxCVD = c;
        }

        if (minCVD === maxCVD) {
            minCVD -= 10;
            maxCVD += 10;
        }

        const cvdRange = Math.max(maxCVD - minCVD, 1);
        const topPad = 12;
        const bottomPad = 16;
        const plotH = h - topPad - bottomPad;

        const cvdToY = (val) => topPad + ((maxCVD - val) / cvdRange) * plotH;
        const zeroY = cvdToY(0);

        // 1. Zero Baseline
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.4)';
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(0, zeroY);
        ctx.lineTo(w, zeroY);
        ctx.stroke();
        ctx.setLineDash([]);

        // 2. Bar X Positioning (Horizontal Alignment)
        const barCount = this.cvdHistory.length;
        const barSpacing = Math.max(3, w / Math.max(barCount, 30));
        const barWidth = Math.max(2, Math.floor(barSpacing * 0.65));

        // 3. Render Delta Histogram Bars
        for (let i = 0; i < barCount; i++) {
            const pt = this.cvdHistory[i];
            let xCenter = 0;

            if (this.chart && typeof this.chart.timeToCoordinate === 'function') {
                const chartX = this.chart.timeToCoordinate(pt.time);
                xCenter = chartX !== null ? chartX : (i * barSpacing);
            } else {
                xCenter = (i * barSpacing) + (barSpacing / 2);
            }

            if (xCenter < -10 || xCenter > w + 10) continue;

            const isUp = (pt.delta || 0) >= 0;
            const barH = Math.max(2, Math.min(plotH / 2, (Math.abs(pt.delta || 0) / maxDelta) * (plotH * 0.45)));
            const barTop = isUp ? (zeroY - barH) : zeroY;

            ctx.fillStyle = isUp ? 'rgba(16, 185, 129, 0.75)' : 'rgba(239, 68, 68, 0.75)';
            ctx.fillRect(Math.round(xCenter - barWidth / 2), Math.round(barTop), barWidth, Math.round(barH));
        }

        // 4. Render Glowing Cyan Cumulative CVD Line & Area Gradient
        ctx.beginPath();
        let firstX = 0;
        let firstY = zeroY;
        let lastX = 0;

        for (let i = 0; i < barCount; i++) {
            const pt = this.cvdHistory[i];
            let x = 0;

            if (this.chart && typeof this.chart.timeToCoordinate === 'function') {
                const chartX = this.chart.timeToCoordinate(pt.time);
                x = chartX !== null ? chartX : (i * barSpacing);
            } else {
                x = (i * barSpacing) + (barSpacing / 2);
            }

            const y = cvdToY(pt.cumulative || 0);

            if (i === 0) {
                ctx.moveTo(x, y);
                firstX = x;
                firstY = y;
            } else {
                ctx.lineTo(x, y);
            }
            lastX = x;
        }

        // Glowing Line Stroke
        ctx.strokeStyle = '#00F2FE';
        ctx.lineWidth = 2;
        ctx.shadowColor = 'rgba(0, 242, 254, 0.6)';
        ctx.shadowBlur = 6;
        ctx.stroke();
        ctx.shadowBlur = 0; // Reset

        // Gradient Area Fill under CVD line
        ctx.lineTo(lastX, h - bottomPad);
        ctx.lineTo(firstX, h - bottomPad);
        ctx.closePath();

        const areaGrad = ctx.createLinearGradient(0, topPad, 0, h - bottomPad);
        areaGrad.addColorStop(0, 'rgba(0, 242, 254, 0.18)');
        areaGrad.addColorStop(1, 'rgba(0, 242, 254, 0.0)');
        ctx.fillStyle = areaGrad;
        ctx.fill();

        // 5. Crosshair Sync Line
        if (this.crosshair.visible && this.crosshair.x >= 0 && this.crosshair.x <= w) {
            ctx.strokeStyle = 'rgba(0, 242, 254, 0.5)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(this.crosshair.x, 0);
            ctx.lineTo(this.crosshair.x, h);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        this.container.innerHTML = '';
    }
}

// Universal Module Definition
if (typeof window !== 'undefined') {
    window.CVDPaneRenderer = CVDPaneRenderer;
    window.classifyLeeReadyTick = classifyLeeReadyTick;
    window.computeDOMImbalance = computeDOMImbalance;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CVDPaneRenderer,
        classifyLeeReadyTick,
        computeDOMImbalance
    };
}
