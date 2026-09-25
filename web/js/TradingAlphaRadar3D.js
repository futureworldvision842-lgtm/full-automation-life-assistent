/**
 * TradingAlphaRadar3D.js — 3D Spatial Quantitative Trading & Meme Coin Alpha Radar
 * =================================================================================
 * High-performance WebGL / Three.js 3D visualizer for J.A.R.V.I.S. Command Empire:
 * 1. Interactive 3D Level-2 Orderbook Depth (Bids & Asks Stairs, Whale Wall Highlights).
 * 2. 3D Cumulative Volume Delta (CVD) Absorption Ribbon & Divergence Waves.
 * 3. 3D Dynamic Liquidity Heatmap Terrain (Price x Time x Resting Liquidity Density).
 * 4. Multi-Asset Navigation: Gold (XAUUSD), EURUSD, Bitcoin (BTC), and Solana (SOL).
 * 5. Dedicated Solana Pump.fun & Raydium Meme Coin Alpha Radar HUD.
 * 6. Live AI-Trader Consensus Stream (Bullish Advocate, Bearish Challenger, Aladdin Risk Officer).
 * 7. FundingPips #40000294403 Deterministic Risk Enforcement (<=0.75% / $750 cap, +1.0R BE auto-lock, 1-tap Panic Close-All).
 *
 * Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['three'], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('three'));
  } else {
    root.TradingAlphaRadar3D = factory(root.THREE);
  }
})(typeof self !== 'undefined' ? self : this, function (THREE) {
  'use strict';

  class TradingAlphaRadar3D {
    /**
     * @param {string|HTMLElement} container - DOM element or selector to mount the visualizer
     * @param {Object} options - Configuration overrides
     */
    constructor(container, options = {}) {
      this.container = typeof container === 'string' ? document.getElementById(container) : container;
      if (!this.container) {
        console.warn('[TradingAlphaRadar3D] Container not found, creating off-screen container.');
        this.container = document.createElement('div');
      }

      this.options = Object.assign({
        symbol: 'XAUUSD',
        apiBase: '',
        refreshInterval: 2500,
        enableControls: true,
        theme: 'cyberpunk', // 'cyberpunk' | 'matrix' | 'stealth'
      }, options);

      this.currentSymbol = this.options.symbol.toUpperCase();
      this.orderbookData = null;
      this.heatmapData = null;
      this.pumpRadarData = null;
      this.consensusData = null;
      this.riskStatusData = null;

      this.scene = null;
      this.camera = null;
      this.renderer = null;
      this.raycaster = null;
      this.mouse = new THREE.Vector2();
      this.animationFrameId = null;
      this.pollTimer = null;
      this.ws = null;

      // 3D Object Groups
      this.groupOrderbook = new THREE.Group();
      this.groupCvd = new THREE.Group();
      this.groupHeatmap = new THREE.Group();
      this.groupWhales = new THREE.Group();
      this.groupGrid = new THREE.Group();

      // Layer Visibility Flags
      this.layers = {
        orderbook: true,
        cvd: true,
        heatmap: true,
        whales: true,
      };

      // Camera State
      this.isMouseDown = false;
      this.prevMousePos = { x: 0, y: 0 };
      this.spherical = { radius: 45, theta: Math.PI / 4, phi: Math.PI / 3 };

      this._initDOM();
      this._initThree();
      this._buildEnvironment();
      this._attachEvents();
      this.fetchData();
      this._startPolling();
      this._initWebSocket();
    }

    /* =========================================================================
     * DOM & UI CONSTRUCTION
     * ========================================================================= */
    _initDOM() {
      this.container.classList.add('trading-radar-3d-root');
      this.container.style.position = 'relative';
      this.container.style.width = this.container.style.width || '100%';
      this.container.style.height = this.container.style.height || '600px';
      this.container.style.overflow = 'hidden';
      this.container.style.background = 'radial-gradient(ellipse at center, #070e17 0%, #03060a 100%)';
      this.container.style.fontFamily = "'Courier New', Courier, monospace";
      this.container.style.color = '#00f3ff';

      // Canvas element
      this.canvas = document.createElement('canvas');
      this.canvas.style.width = '100%';
      this.canvas.style.height = '100%';
      this.canvas.style.display = 'block';
      this.container.appendChild(this.canvas);

      // Top HUD Bar
      this.hudTop = document.createElement('div');
      this.hudTop.className = 'radar-hud-top';
      this.hudTop.style.cssText = `
        position: absolute; top: 12px; left: 14px; right: 14px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none; z-index: 10;
      `;
      this.hudTop.innerHTML = `
        <div style="pointer-events: auto; display: flex; align-items: center; gap: 8px;">
          <div style="font-weight: 900; font-size: 15px; letter-spacing: 1.5px; text-shadow: 0 0 10px #00f3ff;">
            ⚡ 3D ORDERBOOK & ALPHA RADAR
          </div>
          <div class="asset-selector" style="display: flex; gap: 4px; margin-left: 12px;">
            ${['XAUUSD', 'EURUSD', 'BTC', 'SOL'].map(s => `
              <button data-sym="${s}" class="asset-btn ${s === this.currentSymbol ? 'active' : ''}" style="
                background: ${s === this.currentSymbol ? 'rgba(0,243,255,0.25)' : 'rgba(7,14,23,0.7)'};
                color: ${s === this.currentSymbol ? '#00f3ff' : '#6688aa'};
                border: 1px solid ${s === this.currentSymbol ? '#00f3ff' : '#224466'};
                padding: 4px 10px; font-size: 11px; font-weight: bold; cursor: pointer; border-radius: 3px;
                transition: all 0.2s;
              ">${s === 'XAUUSD' ? 'GOLD / XAU' : s}</button>
            `).join('')}
          </div>
        </div>

        <div style="pointer-events: auto; display: flex; align-items: center; gap: 10px;">
          <div id="risk-governance-badge" style="
            background: rgba(16,30,22,0.85); border: 1px solid #00ffaa;
            padding: 4px 10px; border-radius: 3px; font-size: 11px; color: #00ffaa;
          ">
            🛡️ FUNDINGPIPS #40000294403: <span id="risk-status-val">0.75% ($750) CAP LOCKED</span>
          </div>
          <button id="btn-panic-close" style="
            background: rgba(255,20,50,0.25); color: #ff3355; border: 1px solid #ff3355;
            padding: 5px 12px; font-weight: bold; font-size: 11px; cursor: pointer;
            border-radius: 3px; box-shadow: 0 0 8px rgba(255,20,50,0.4); transition: all 0.2s;
          ">🚨 1-TAP PANIC CLOSE-ALL</button>
        </div>
      `;
      this.container.appendChild(this.hudTop);

      // Left Floating Overlay (Microstructure & Consensus Dossier)
      this.hudLeft = document.createElement('div');
      this.hudLeft.className = 'radar-hud-left';
      this.hudLeft.style.cssText = `
        position: absolute; top: 60px; left: 14px; width: 280px;
        background: rgba(7, 14, 23, 0.88); border: 1px solid #1a365d;
        backdrop-filter: blur(8px); border-radius: 4px; padding: 12px;
        font-size: 11px; line-height: 1.5; z-index: 10;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6); pointer-events: auto;
      `;
      this.hudLeft.innerHTML = `
        <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #1e3a5f; padding-bottom: 4px; margin-bottom: 8px;">
          <span style="font-weight: bold; color: #fff;">MICROSTRUCTURE TELEMETRY</span>
          <span id="active-sym-tag" style="color: #00f3ff; font-weight: bold;">${this.currentSymbol}</span>
        </div>
        <div id="telemetry-content">
          <div>• Mid Price: <span id="val-mid" style="color: #fff;">--</span></div>
          <div>• Spread: <span id="val-spread" style="color: #00ffaa;">--</span></div>
          <div>• Imbalance Ratio: <span id="val-imbalance" style="color: #ffaa00;">--</span></div>
          <div>• CVD Net Delta: <span id="val-cvd" style="color: #00f3ff;">--</span></div>
          <div>• Orderbook Bias: <span id="val-bias" style="color: #00ffaa; font-weight: bold;">--</span></div>
        </div>

        <div style="margin-top: 10px; border-top: 1px solid #1e3a5f; padding-top: 8px;">
          <div style="font-weight: bold; color: #fff; margin-bottom: 4px;">🏛️ CONSENSUS CHAMBER</div>
          <div id="council-content">
            <div>• Verdict: <span id="council-verdict" style="color: #00ffaa; font-weight: bold;">SYNCING...</span></div>
            <div>• Closed-Bar Evidence: <span id="council-evidence" style="color: #00f3ff;">--%</span></div>
            <div>• Geopolitical Factor: <span id="council-geo" style="color: #ffbb00;">--</span></div>
            <div id="council-agents" style="margin-top: 4px; font-size: 10px; color: #88aacc;"></div>
          </div>
        </div>
      `;
      this.container.appendChild(this.hudLeft);

      // Right Floating Overlay (Meme Coin Alpha Radar)
      this.hudRight = document.createElement('div');
      this.hudRight.className = 'radar-hud-right';
      this.hudRight.style.cssText = `
        position: absolute; top: 60px; right: 14px; width: 310px;
        background: rgba(7, 14, 23, 0.88); border: 1px solid #1a365d;
        backdrop-filter: blur(8px); border-radius: 4px; padding: 12px;
        font-size: 11px; line-height: 1.4; z-index: 10;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6); pointer-events: auto;
      `;
      this.hudRight.innerHTML = `
        <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #1e3a5f; padding-bottom: 4px; margin-bottom: 8px;">
          <span style="font-weight: bold; color: #ff007f;">⚡ MEME COIN ALPHA RADAR</span>
          <span style="color: #00ffaa; font-size: 10px;">SOLANA / PUMP.FUN</span>
        </div>
        <div id="pump-radar-list" style="max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;">
          <div style="color: #6688aa; font-style: italic;">Scanning Solana bonding curves... ⏳</div>
        </div>
      `;
      this.container.appendChild(this.hudRight);

      // Bottom Layer Toggles & View Controls
      this.hudBottom = document.createElement('div');
      this.hudBottom.className = 'radar-hud-bottom';
      this.hudBottom.style.cssText = `
        position: absolute; bottom: 12px; left: 14px; right: 14px;
        display: flex; justify-content: space-between; align-items: center;
        pointer-events: none; z-index: 10; font-size: 11px;
      `;
      this.hudBottom.innerHTML = `
        <div style="pointer-events: auto; display: flex; gap: 6px;">
          <button data-layer="orderbook" class="layer-btn active" style="background: rgba(0,255,170,0.2); color: #00ffaa; border: 1px solid #00ffaa; padding: 3px 8px; border-radius: 3px; cursor: pointer;">[x] 3D Depth Stairs</button>
          <button data-layer="cvd" class="layer-btn active" style="background: rgba(0,243,255,0.2); color: #00f3ff; border: 1px solid #00f3ff; padding: 3px 8px; border-radius: 3px; cursor: pointer;">[x] CVD Ribbon</button>
          <button data-layer="heatmap" class="layer-btn active" style="background: rgba(255,170,0,0.2); color: #ffaa00; border: 1px solid #ffaa00; padding: 3px 8px; border-radius: 3px; cursor: pointer;">[x] Liquidity Heatmap</button>
          <button data-layer="whales" class="layer-btn active" style="background: rgba(255,0,128,0.2); color: #ff007f; border: 1px solid #ff007f; padding: 3px 8px; border-radius: 3px; cursor: pointer;">[x] Whale Walls</button>
        </div>
        <div style="pointer-events: auto; color: #557799; font-size: 10px;">
          [Drag] Orbit Camera • [Right-Drag] Pan • [Scroll] Zoom
        </div>
      `;
      this.container.appendChild(this.hudBottom);

      // Hover Tooltip
      this.tooltip = document.createElement('div');
      this.tooltip.className = 'radar-tooltip';
      this.tooltip.style.cssText = `
        position: absolute; display: none; pointer-events: none;
        background: rgba(3, 7, 14, 0.92); border: 1px solid #00f3ff;
        color: #fff; padding: 6px 10px; font-size: 11px; border-radius: 3px;
        box-shadow: 0 2px 10px rgba(0,243,255,0.3); z-index: 20;
      `;
      this.container.appendChild(this.tooltip);
    }

    /* =========================================================================
     * THREE.JS SCENE SETUP
     * ========================================================================= */
    _initThree() {
      const width = this.container.clientWidth || 800;
      const height = this.container.clientHeight || 600;

      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.FogExp2(0x03060a, 0.012);

      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
      this._updateCameraPosition();

      this.renderer = new THREE.WebGLRenderer({
        canvas: this.canvas,
        antialias: true,
        alpha: true,
      });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      this.raycaster = new THREE.Raycaster();

      // Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
      this.scene.add(ambientLight);

      const dirLight = new THREE.DirectionalLight(0x00f3ff, 1.2);
      dirLight.position.set(20, 40, 20);
      this.scene.add(dirLight);

      const pointLight = new THREE.PointLight(0xff007f, 1.5, 60);
      pointLight.position.set(-20, 15, -10);
      this.scene.add(pointLight);

      // Add groups to scene
      this.scene.add(this.groupGrid);
      this.scene.add(this.groupOrderbook);
      this.scene.add(this.groupCvd);
      this.scene.add(this.groupHeatmap);
      this.scene.add(this.groupWhales);

      this._animate = this._animate.bind(this);
      this._animate();
    }

    _buildEnvironment() {
      // 3D Cyberpunk Floor Grid
      const size = 60;
      const divisions = 30;
      const gridHelper = new THREE.GridHelper(size, divisions, 0x00f3ff, 0x112233);
      gridHelper.position.y = -5;
      this.groupGrid.add(gridHelper);

      // Center Reference Ring
      const ringGeo = new THREE.RingGeometry(1.8, 2.0, 32);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0x00f3ff, side: THREE.DoubleSide });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      ring.position.y = -4.9;
      this.groupGrid.add(ring);
    }

    _updateCameraPosition() {
      const { radius, theta, phi } = this.spherical;
      this.camera.position.x = radius * Math.sin(phi) * Math.sin(theta);
      this.camera.position.y = radius * Math.cos(phi);
      this.camera.position.z = radius * Math.sin(phi) * Math.cos(theta);
      this.camera.lookAt(0, 0, 0);
    }

    /* =========================================================================
     * EVENT HANDLERS
     * ========================================================================= */
    _attachEvents() {
      window.addEventListener('resize', () => this._onResize());

      // Orbit controls via mouse drag
      this.canvas.addEventListener('mousedown', (e) => {
        this.isMouseDown = true;
        this.prevMousePos = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener('mouseup', () => {
        this.isMouseDown = false;
      });

      this.canvas.addEventListener('mousemove', (e) => {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

        if (this.isMouseDown) {
          const deltaX = e.clientX - this.prevMousePos.x;
          const deltaY = e.clientY - this.prevMousePos.y;
          this.prevMousePos = { x: e.clientX, y: e.clientY };

          this.spherical.theta -= deltaX * 0.008;
          this.spherical.phi -= deltaY * 0.008;
          this.spherical.phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, this.spherical.phi));
          this._updateCameraPosition();
        } else {
          this._handleHover(e);
        }
      });

      this.canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        this.spherical.radius += e.deltaY * 0.04;
        this.spherical.radius = Math.max(15, Math.min(90, this.spherical.radius));
        this._updateCameraPosition();
      });

      // Asset Switcher buttons
      this.hudTop.querySelectorAll('.asset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const sym = e.target.getAttribute('data-sym');
          this.switchSymbol(sym);
        });
      });

      // Layer Toggles
      this.hudBottom.querySelectorAll('.layer-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const layerKey = e.target.getAttribute('data-layer');
          this.layers[layerKey] = !this.layers[layerKey];
          e.target.classList.toggle('active', this.layers[layerKey]);
          e.target.style.opacity = this.layers[layerKey] ? '1.0' : '0.4';
          this._applyLayerVisibility();
        });
      });

      // 1-Tap Panic Close Button
      const panicBtn = this.hudTop.querySelector('#btn-panic-close');
      if (panicBtn) {
        panicBtn.addEventListener('click', () => this.emergencyPanicClose());
      }
    }

    _applyLayerVisibility() {
      this.groupOrderbook.visible = this.layers.orderbook;
      this.groupCvd.visible = this.layers.cvd;
      this.groupHeatmap.visible = this.layers.heatmap;
      this.groupWhales.visible = this.layers.whales;
    }

    _handleHover(e) {
      if (!this.camera || !this.raycaster) return;
      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.groupOrderbook.children, true);

      if (intersects.length > 0) {
        const obj = intersects[0].object;
        if (obj.userData && obj.userData.price) {
          const data = obj.userData;
          this.tooltip.style.display = 'block';
          this.tooltip.style.left = `${e.clientX - this.container.getBoundingClientRect().left + 15}px`;
          this.tooltip.style.top = `${e.clientY - this.container.getBoundingClientRect().top + 15}px`;
          this.tooltip.innerHTML = `
            <div style="color: ${data.side === 'BUY' ? '#00ffaa' : '#ff3355'}; font-weight: bold;">
              ${data.side} LEVEL ${data.level}
            </div>
            <div>Price: $${data.price}</div>
            <div>Volume: ${data.volume}</div>
            <div>Cum Vol: ${data.cum_volume}</div>
            ${data.is_whale ? `<div style="color: #ff007f; font-weight: bold;">🐋 WHALE WALL</div>` : ''}
          `;
          return;
        }
      }
      this.tooltip.style.display = 'none';
    }

    _onResize() {
      if (!this.container || !this.renderer || !this.camera) return;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    }

    /* =========================================================================
     * DATA FETCHING & SYNCHRONIZATION
     * ========================================================================= */
    async fetchData() {
      try {
        await Promise.all([
          this.fetchOrderbook(),
          this.fetchHeatmap(),
          this.fetchPumpRadar(),
          this.fetchConsensus(),
          this.fetchRiskStatus(),
        ]);
      } catch (err) {
        console.error('[TradingAlphaRadar3D] Data fetch error:', err);
      }
    }

    async fetchOrderbook() {
      const sym = this.currentSymbol;
      const res = await fetch(`${this.options.apiBase}/api/trading/orderbook/${sym}`);
      if (res.ok) {
        this.orderbookData = await res.json();
        this.renderOrderbook3D(this.orderbookData);
        this._updateMicrostructureHUD(this.orderbookData);
      }
    }

    async fetchHeatmap() {
      const sym = this.currentSymbol;
      const res = await fetch(`${this.options.apiBase}/api/trading/heatmap/${sym}`);
      if (res.ok) {
        this.heatmapData = await res.json();
        this.renderHeatmap3D(this.heatmapData);
      }
    }

    async fetchPumpRadar() {
      const res = await fetch(`${this.options.apiBase}/api/trading/pump_radar`);
      if (res.ok) {
        this.pumpRadarData = await res.json();
        this._updatePumpRadarHUD(this.pumpRadarData);
      }
    }

    async fetchConsensus() {
      const sym = this.currentSymbol;
      const res = await fetch(`${this.options.apiBase}/api/trading/council/${sym}`);
      if (res.ok) {
        this.consensusData = await res.json();
        this._updateConsensusHUD(this.consensusData);
      }
    }

    async fetchRiskStatus() {
      const res = await fetch(`${this.options.apiBase}/api/trading/risk_status`);
      if (res.ok) {
        this.riskStatusData = await res.json();
        this._updateRiskHUD(this.riskStatusData);
      }
    }

    _startPolling() {
      if (this.pollTimer) clearInterval(this.pollTimer);
      this.pollTimer = setInterval(() => {
        this.fetchData();
      }, this.options.refreshInterval);
    }

    _initWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/trading/consensus`;
      try {
        this.ws = new WebSocket(wsUrl);
        this.ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'CONSENSUS_UPDATE' && msg.symbol === this.currentSymbol) {
              this._updateConsensusHUD(msg.data);
            }
          } catch (e) {
            // ignore
          }
        };
        this.ws.onerror = () => {};
      } catch (e) {
        // Fallback to polling
      }
    }

    switchSymbol(sym) {
      if (this.currentSymbol === sym) return;
      this.currentSymbol = sym.toUpperCase();
      this.hudTop.querySelectorAll('.asset-btn').forEach(btn => {
        const bSym = btn.getAttribute('data-sym');
        const isActive = bSym === this.currentSymbol;
        btn.classList.toggle('active', isActive);
        btn.style.background = isActive ? 'rgba(0,243,255,0.25)' : 'rgba(7,14,23,0.7)';
        btn.style.color = isActive ? '#00f3ff' : '#6688aa';
        btn.style.borderColor = isActive ? '#00f3ff' : '#224466';
      });
      const tag = this.hudLeft.querySelector('#active-sym-tag');
      if (tag) tag.textContent = this.currentSymbol;

      this.fetchData();
    }

    async emergencyPanicClose() {
      if (!confirm(`CONFIRM EMERGENCY PANIC CLOSE-ALL?\nFlatten all open positions and cancel orders immediately on FundingPips #40000294403?`)) {
        return;
      }
      try {
        const res = await fetch(`${this.options.apiBase}/api/trading/close_all`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        const data = await res.json();
        alert(data.message || '🚨 All positions closed.');
        this.fetchData();
      } catch (err) {
        alert('Panic close request failed: ' + err);
      }
    }

    /* =========================================================================
     * 3D RENDERING PIPELINES
     * ========================================================================= */
    renderOrderbook3D(data) {
      // Clear previous orderbook & CVD meshes
      while (this.groupOrderbook.children.length > 0) {
        const obj = this.groupOrderbook.children.pop();
        if (obj.geometry) obj.geometry.dispose();
      }
      while (this.groupCvd.children.length > 0) {
        const obj = this.groupCvd.children.pop();
        if (obj.geometry) obj.geometry.dispose();
      }
      while (this.groupWhales.children.length > 0) {
        const obj = this.groupWhales.children.pop();
        if (obj.geometry) obj.geometry.dispose();
      }

      if (!data || !data.bids || !data.asks) return;

      const bids = data.bids;
      const asks = data.asks;
      const maxCumVol = Math.max(
        bids[bids.length - 1]?.cum_volume || 1000,
        asks[asks.length - 1]?.cum_volume || 1000
      );

      const barWidth = 0.8;
      const barDepth = 1.2;

      // Render Bids (Green stairs extending to the left)
      bids.forEach((bid, i) => {
        const height = Math.max(0.4, (bid.cum_volume / maxCumVol) * 16);
        const geo = new THREE.BoxGeometry(barWidth, height, barDepth);
        const color = bid.is_whale_wall ? 0x00ffaa : 0x00aa66;
        const mat = new THREE.MeshPhongMaterial({
          color: color,
          transparent: true,
          opacity: 0.85,
          shininess: 80,
          emissive: bid.is_whale_wall ? 0x004422 : 0x001100,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(-1.0 - (i * (barWidth + 0.15)), height / 2 - 5, 0);
        mesh.userData = {
          side: 'BUY',
          level: bid.level,
          price: bid.price,
          volume: bid.volume,
          cum_volume: bid.cum_volume,
          is_whale: bid.is_whale_wall,
        };
        this.groupOrderbook.add(mesh);

        // Highlight whale wall with glowing outer beacon ring
        if (bid.is_whale_wall) {
          const beaconGeo = new THREE.CylinderGeometry(0.6, 0.6, 0.2, 16);
          const beaconMat = new THREE.MeshBasicMaterial({ color: 0x00ffaa, wireframe: true });
          const beacon = new THREE.Mesh(beaconGeo, beaconMat);
          beacon.position.set(mesh.position.x, height - 4.8, 0);
          this.groupWhales.add(beacon);
        }
      });

      // Render Asks (Red stairs extending to the right)
      asks.forEach((ask, i) => {
        const height = Math.max(0.4, (ask.cum_volume / maxCumVol) * 16);
        const geo = new THREE.BoxGeometry(barWidth, height, barDepth);
        const color = ask.is_whale_wall ? 0xff2255 : 0xaa2233;
        const mat = new THREE.MeshPhongMaterial({
          color: color,
          transparent: true,
          opacity: 0.85,
          shininess: 80,
          emissive: ask.is_whale_wall ? 0x440011 : 0x110000,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(1.0 + (i * (barWidth + 0.15)), height / 2 - 5, 0);
        mesh.userData = {
          side: 'SELL',
          level: ask.level,
          price: ask.price,
          volume: ask.volume,
          cum_volume: ask.cum_volume,
          is_whale: ask.is_whale_wall,
        };
        this.groupOrderbook.add(mesh);

        if (ask.is_whale_wall) {
          const beaconGeo = new THREE.CylinderGeometry(0.6, 0.6, 0.2, 16);
          const beaconMat = new THREE.MeshBasicMaterial({ color: 0xff2255, wireframe: true });
          const beacon = new THREE.Mesh(beaconGeo, beaconMat);
          beacon.position.set(mesh.position.x, height - 4.8, 0);
          this.groupWhales.add(beacon);
        }
      });

      // Render CVD 3D Absorption Wave (spline floating above the depth)
      if (data.cvd_absorption && data.cvd_absorption.curve) {
        const curvePoints = [];
        const curveData = data.cvd_absorption.curve;
        curveData.forEach((pt, idx) => {
          const x = -15 + (idx * 1.5);
          const y = (pt.cumulative_cvd / 200.0) * 3.0 + 3.0;
          const z = 4.0;
          curvePoints.push(new THREE.Vector3(x, y, z));
        });

        const curve = new THREE.CatmullRomCurve3(curvePoints);
        const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.15, 8, false);
        const isBullish = (data.cvd_absorption.net_delta || 0) >= 0;
        const tubeMat = new THREE.MeshBasicMaterial({
          color: isBullish ? 0x00f3ff : 0xff007f,
          wireframe: false,
        });
        const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
        this.groupCvd.add(tubeMesh);
      }
    }

    renderHeatmap3D(data) {
      while (this.groupHeatmap.children.length > 0) {
        const obj = this.groupHeatmap.children.pop();
        if (obj.geometry) obj.geometry.dispose();
      }

      if (!data || !data.heatmap_matrix_3d) return;

      const matrix = data.heatmap_matrix_3d; // [time_slice][price_idx]
      const times = matrix.length;
      const prices = matrix[0]?.length || 0;
      if (times === 0 || prices === 0) return;

      const planeWidth = 24;
      const planeDepth = 16;
      const geo = new THREE.PlaneGeometry(planeWidth, planeDepth, prices - 1, times - 1);
      geo.rotateX(-Math.PI / 2);

      const pos = geo.attributes.position;
      const colors = new Float32Array(pos.count * 3);

      let idx = 0;
      for (let t = 0; t < times; t++) {
        for (let p = 0; p < prices; p++) {
          const intensity = matrix[t][p] / 100.0; // 0.0 to 1.0
          // Displace vertex height based on intensity
          pos.setY(idx, -5 + (intensity * 4.5));

          // Color gradient: Cyan (low) -> Amber (mid) -> Magenta (hot iceberg)
          let r, g, b;
          if (intensity < 0.5) {
            const f = intensity * 2.0;
            r = 0.0;
            g = 0.5 + 0.5 * f;
            b = 1.0 - 0.5 * f;
          } else {
            const f = (intensity - 0.5) * 2.0;
            r = 0.8 + 0.2 * f;
            g = 0.2 + 0.4 * (1 - f);
            b = 0.4 + 0.6 * f;
          }
          colors[idx * 3] = r;
          colors[idx * 3 + 1] = g;
          colors[idx * 3 + 2] = b;
          idx++;
        }
      }

      geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      geo.computeVertexNormals();

      const mat = new THREE.MeshPhongMaterial({
        vertexColors: true,
        wireframe: true,
        transparent: true,
        opacity: 0.65,
      });

      const terrainMesh = new THREE.Mesh(geo, mat);
      terrainMesh.position.set(0, 0, -8);
      this.groupHeatmap.add(terrainMesh);
    }

    _animate() {
      this.animationFrameId = requestAnimationFrame(this._animate);

      // Subtle ambient rotation of whale wall beacons
      this.groupWhales.children.forEach(b => {
        b.rotation.y += 0.02;
      });

      if (this.renderer && this.scene && this.camera) {
        this.renderer.render(this.scene, this.camera);
      }
    }

    /* =========================================================================
     * HUD DATA BINDING
     * ========================================================================= */
    _updateMicrostructureHUD(data) {
      if (!data) return;
      const elMid = this.hudLeft.querySelector('#val-mid');
      const elSpread = this.hudLeft.querySelector('#val-spread');
      const elImbalance = this.hudLeft.querySelector('#val-imbalance');
      const elCvd = this.hudLeft.querySelector('#val-cvd');
      const elBias = this.hudLeft.querySelector('#val-bias');

      if (elMid) elMid.textContent = `$${data.mid_price}`;
      if (elSpread) elSpread.textContent = `${data.spread} (${data.spread_bps} bps)`;
      if (elImbalance) elImbalance.textContent = `${data.imbalance_ratio}x (${data.imbalance_pct}%)`;
      if (elCvd && data.cvd_absorption) elCvd.textContent = `${data.cvd_absorption.net_delta > 0 ? '+' : ''}${data.cvd_absorption.net_delta} [${data.cvd_absorption.absorption_type}]`;
      if (elBias) {
        elBias.textContent = data.bias;
        elBias.style.color = data.bias.includes('BULLISH') ? '#00ffaa' : (data.bias.includes('BEARISH') ? '#ff3355' : '#ffaa00');
      }
    }

    _updateConsensusHUD(data) {
      if (!data) return;
      const elVerdict = this.hudLeft.querySelector('#council-verdict');
      const elEvidence = this.hudLeft.querySelector('#council-evidence');
      const elGeo = this.hudLeft.querySelector('#council-geo');
      const elAgents = this.hudLeft.querySelector('#council-agents');

      if (elVerdict) {
        elVerdict.textContent = data.council_verdict || (data.approved ? 'CONCURRENCE_BUY' : 'VETOED');
        elVerdict.style.color = data.approved ? '#00ffaa' : '#ff3355';
      }
      if (elEvidence) {
        elEvidence.textContent = `${data.closed_bar_evidence_score || 88.0}% (Closed-Bar Weighted)`;
      }
      if (elGeo && data.geopolitical_news_impact) {
        elGeo.textContent = `${data.geopolitical_news_impact.correlation_bias} (DEFCON ${data.geopolitical_news_impact.defcon_level || 2})`;
      }
      if (elAgents && data.agents) {
        elAgents.innerHTML = Object.entries(data.agents).map(([name, ag]) => `
          <div><span style="color:#fff;">${name}:</span> <span style="color:${ag.vote === 'BUY' ? '#00ffaa' : (ag.vote === 'PASS' ? '#00f3ff' : '#ff3355')}; font-weight:bold;">${ag.vote}</span> - ${ag.rationale.substring(0, 48)}...</div>
        `).join('');
      }
    }

    _updatePumpRadarHUD(data) {
      if (!data || !data.tokens) return;
      const container = this.hudRight.querySelector('#pump-radar-list');
      if (!container) return;

      container.innerHTML = data.tokens.map(token => {
        const isHot = token.alpha_conviction_score >= 80;
        const progressColor = token.bonding_curve_pct > 80 ? '#00ffaa' : (token.bonding_curve_pct > 50 ? '#00f3ff' : '#ffaa00');
        return `
          <div style="
            background: rgba(14,24,38,0.75); border: 1px solid ${isHot ? '#00ffaa' : '#1e3a5f'};
            padding: 8px; border-radius: 4px; box-shadow: ${isHot ? '0 0 8px rgba(0,255,170,0.3)' : 'none'};
          ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: bold; color: #fff;">$${token.symbol}</span>
              <span style="color: ${progressColor}; font-weight: bold;">${token.bonding_curve_pct}% Curve</span>
            </div>
            <div style="font-size: 10px; color: #88aacc; margin-top: 2px;">
              ${token.name} • MC: $${token.market_cap_usd || (token.price_usd * 1000000000).toFixed(0)}
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px; font-size: 10px;">
              <span>Vol Accel: <b style="color:#00f3ff;">${token.vol_accel}x</b></span>
              <span>Whale Buys: <b style="color:#ff007f;">${token.whale_buys_count || 0}</b></span>
              <span>Alpha: <b style="color:#00ffaa;">${token.alpha_conviction_score}/100</b></span>
            </div>
            <div style="margin-top: 4px; font-size: 9px; color: ${token.dev_holding_pct > 10 ? '#ff3355' : '#00ffaa'};">
              Dev: ${token.dev_holding_pct}% | LP: ${token.lp_locked_pct}% Locked | Mint Revoked: ${token.mint_revoked ? 'YES' : 'NO'}
            </div>
          </div>
        `;
      }).join('');
    }

    _updateRiskHUD(data) {
      if (!data) return;
      const el = this.hudTop.querySelector('#risk-status-val');
      if (el) {
        el.textContent = `${data.max_risk_pct}% ($${data.max_risk_cap_usd}) CAP LOCKED | +${data.dynamic_breakeven_r_trigger}R BE`;
      }
    }

    destroy() {
      if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);
      if (this.pollTimer) clearInterval(this.pollTimer);
      if (this.ws) this.ws.close();
      if (this.renderer) this.renderer.dispose();
      this.container.innerHTML = '';
    }
  }

  return TradingAlphaRadar3D;
});
