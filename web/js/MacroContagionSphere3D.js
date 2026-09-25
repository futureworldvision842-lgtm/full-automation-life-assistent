/**
 * MacroContagionSphere3D.js — Interactive 3D Macro Contagion & Geopolitical Network Graph
 * =======================================================================================
 * Institutional WebGL Visualizer for J.A.R.V.I.S. Command Center
 * 
 * Capabilities:
 *   1. 3D Planetary Command Globe:
 *      - Procedural cybernetic Earth texture, lat/lon graticules, atmospheric Fresnel glow,
 *        sunlight, and ambient starfield.
 *   2. Macro Driver & Target Asset Nodes:
 *      - Macro Drivers (DXY, US10Y, Crude Oil) positioned in elevated orbital arc.
 *      - Target Assets (Gold/XAUUSD, EURUSD, USDJPY, GBPUSD, BTC, SOL) in receiving orbit.
 *      - Glowing cores, pulsating halos, and billboard canvas labels showing price & delta.
 *   3. Animated 3D CatmullRom Particle Splines:
 *      - 3D parametric curves connecting drivers and hotspots to target assets.
 *      - Dynamic particle flow velocity proportional to volatility/beta.
 *      - Directional flow from shock origins to receivers.
 *      - Coloration mapped to correlation sign & magnitude:
 *        * Cyan (#00f3ff): Positive tailwind / inverse dollar relief.
 *        * Crimson (#ff3355): Negative drag / direct yield/rate pressure.
 *        * Amber (#ffaa00): Geopolitical shock / commodity inflation spike.
 *   4. Geopolitical Hotspot Overlays:
 *      - Accurate spherical coordinates for Bab-el-Mandeb, Hormuz, Taiwan Strait, Eastern Europe.
 *      - Pulsing concentric rings and shockwave ripples.
 *   5. Interactive Click Handlers & Smooth Camera Fly-To:
 *      - Raycasting click detection on hotspots and nodes.
 *      - Smooth camera interpolation fly-to transition.
 *      - Dispatches 'jarvis:hotspot:selected' and 'jarvis:node:selected' CustomEvents.
 *      - Listens for 'jarvis:macro:shockwave' to inject dynamic shockwaves.
 *      - Glassmorphism Tactical Entity Dossier modal with historical precedent tables.
 *   6. Forward Catalyst Timeline HUD Overlay:
 *      - Interactive timeline rendering upcoming high-impact catalysts (FOMC, CPI, NFP, speeches).
 *      - 15-minute news blackout buffer warning indicators.
 *      - Clickable historical price reaction precedents.
 *   7. Full WebGL Lifecycle & Memory Hygiene:
 *      - Comprehensive destroy() method disposing geometries, materials, and textures.
 * =======================================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.MacroContagionSphere3D = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Fallback default dataset if backend API is not yet loaded
  const DEFAULT_HOTSPOTS = {
    red_sea: {
      hotspot_id: 'red_sea',
      name: 'Bab el-Mandeb / Red Sea Chokepoint',
      region: 'Middle East / Horn of Africa',
      latitude: 12.78,
      longitude: 43.33,
      threat_level: 'CRITICAL_WARZONE',
      disruption_pct: 66.1,
      baseline_mbd: 6.2,
      current_mbd: 2.1,
      status_narrative: 'Houthi anti-ship missile interdictions active; commercial container fleet rerouting via Cape of Good Hope (+10-14 days transit).',
      reroute_recommendation: 'Cape of Good Hope rerouting required. War-risk freight premiums +350%.',
      commodity_multipliers: { XAUUSD: 1.40, WTI: 1.35, EURUSD: -0.60, INFLATION_SURGE: 1.30 },
      historical_dossier: [
        {
          date: '2023-12-15',
          title: 'Red Sea Commercial Fleet Interdictions',
          description: 'Anti-ship ballistic missile strikes halt container lines (Maersk, Hapag-Lloyd).',
          crude_oil_impulse: '+4.8% surge in 48h ($73.80 -> $77.35)',
          gold_impulse: '+$36.50/oz safe haven expansion to $2,042',
          dxy_reaction: '-0.35% intraday churn',
          risk_crypto_reaction: 'BTC held steady (+0.8%), altcoins rangebound'
        },
        {
          date: '2024-01-12',
          title: 'Operation Poseidon Archer Strikes',
          description: 'Joint naval aviation strikes on Yemen coastal radar and launch sites.',
          crude_oil_impulse: '+3.2% gap open ($78.20 -> $80.70)',
          gold_impulse: '+$22.00/oz immediate rally',
          dxy_reaction: '+0.20% safe-haven USD bid',
          risk_crypto_reaction: 'Crypto flash liquidation dip (-1.8%) then V-reversal'
        }
      ],
      volatility_forecast: {
        expected_oil_range_usd: [77.20, 81.50],
        expected_gold_range_usd: [2635.0, 2678.0],
        implied_risk_premium: '+$4.20/bbl'
      }
    },
    hormuz_strait: {
      hotspot_id: 'hormuz_strait',
      name: 'Strait of Hormuz Chokepoint',
      region: 'Persian Gulf / Arabian Sea',
      latitude: 26.56,
      longitude: 56.25,
      threat_level: 'CRITICAL_WARZONE',
      disruption_pct: 31.0,
      baseline_mbd: 21.0,
      current_mbd: 14.5,
      status_narrative: 'IRGC fast attack craft patrols active in traffic separation scheme; tanker boarding risk at DEFCON 1.',
      reroute_recommendation: 'Zero viable maritime bypass exists for bulk volume. Strict military escort protocol.',
      commodity_multipliers: { XAUUSD: 1.45, WTI: 1.50, BRENT: 1.52, DXY: -0.40, EURUSD: -0.65, BTCUSD: -1.25 },
      historical_dossier: [
        {
          date: '2024-04-13',
          title: 'MSC Aries Seizure & Gulf Aerial Escalation',
          description: 'Special forces heliborne boarding of container vessel MSC Aries in the Strait of Hormuz.',
          crude_oil_impulse: '+6.2% 24h surge testing $90.50/bbl',
          gold_impulse: '+$52.00/oz vertical push to then-record $2,431.50',
          dxy_reaction: '+0.40% flight to dollar safety',
          risk_crypto_reaction: 'BTC flash crash -4.5% ($67,500 -> $64,400) on weekend liquidation cascade'
        },
        {
          date: '2019-09-14',
          title: 'Abqaiq-Khurais Drone Swarm Attack',
          description: 'Precision strike halting 5.7 mbd of crude processing (over 50% of Saudi output).',
          crude_oil_impulse: '+14.6% single-day spike (largest percentage jump in 30 years)',
          gold_impulse: '+$19.50/oz gap open',
          dxy_reaction: '+0.15% modest gain',
          risk_crypto_reaction: 'Equities slid -1.2%, crypto neutral'
        }
      ],
      volatility_forecast: {
        expected_oil_range_usd: [76.50, 83.20],
        expected_gold_range_usd: [2640.0, 2690.0],
        implied_risk_premium: '+$6.80/bbl'
      }
    },
    taiwan_strait: {
      hotspot_id: 'taiwan_strait',
      name: 'Taiwan Strait & Luzon Strait',
      region: 'East Asia / Western Pacific',
      latitude: 24.25,
      longitude: 119.50,
      threat_level: 'HIGH_TENSION',
      disruption_pct: 12.0,
      baseline_mbd: 0.0,
      current_mbd: 0.0,
      status_narrative: 'PLA carrier strike group & air incursions across median line; live-fire maritime exclusion zones declared.',
      reroute_recommendation: 'Commercial shipping rerouting east of Taiwan via Philippine Sea during live-fire drills.',
      commodity_multipliers: { XAUUSD: 1.50, USDJPY: -0.80, BTCUSD: 1.30, SEMI_TECH_SHOCK: 1.75 },
      historical_dossier: [
        {
          date: '2022-08-04',
          title: 'Joint Blockade Exercises & Missile Overflights',
          description: 'Live-fire military maneuvers surrounding Taiwan with ballistic missiles overflying Taipei airspace.',
          crude_oil_impulse: 'Neutral to +0.8%',
          gold_impulse: '+$18.00/oz safe haven buying',
          dxy_reaction: '+0.25% dollar dominance',
          risk_crypto_reaction: 'Semiconductor stocks (SOX) -2.8%, BTC rallied +2.1% on sovereign seizure hedge'
        },
        {
          date: '2024-05-23',
          title: 'Joint Sword-2024A Encirclement Drills',
          description: 'Comprehensive naval and air encirclement simulations across northern and southern sectors.',
          crude_oil_impulse: 'Flat (+0.2%)',
          gold_impulse: '+$14.20/oz intraday spike',
          dxy_reaction: 'Unchanged',
          risk_crypto_reaction: 'Taiwan Dollar (TWD) -0.3%, crypto unaffected'
        }
      ],
      volatility_forecast: {
        expected_tech_volatility_pct: '+3.4%',
        expected_gold_range_usd: [2645.0, 2685.0],
        implied_risk_premium: '+$28.00/oz'
      }
    },
    eastern_europe: {
      hotspot_id: 'eastern_europe',
      name: 'Eastern Europe / Black Sea / Suwalki Gap',
      region: 'Eastern Europe / Black Sea',
      latitude: 48.01,
      longitude: 37.80,
      threat_level: 'HIGH_TENSION',
      disruption_pct: 57.1,
      baseline_mbd: 2.8,
      current_mbd: 1.2,
      status_narrative: 'Maritime drone warfare in Black Sea ports; forward military deployments along Suwalki Gap corridor.',
      reroute_recommendation: 'Black Sea maritime shipping requires special war-risk grain insurance.',
      commodity_multipliers: { XAUUSD: 1.35, WTI: 1.30, NAT_GAS_EU: 1.85, EURUSD: -0.70, WHEAT_AGRI: 1.45 },
      historical_dossier: [
        {
          date: '2022-02-24',
          title: 'Eastern European Armed Conflict Outbreak',
          description: 'Large-scale military mobilization across borders triggering resource export sanctions.',
          crude_oil_impulse: '+8.5% intraday surge past $100/bbl (peaked at $130)',
          gold_impulse: '+$65.00/oz explosion testing $1,974/oz',
          dxy_reaction: '+0.90% massive global liquidity flight to US Dollar',
          risk_crypto_reaction: 'Initial crypto sell-off (-8.0%) followed by massive global adoption surge (+15% in 7d)'
        },
        {
          date: '2023-07-17',
          title: 'Black Sea Grain Initiative Suspension',
          description: 'Termination of safe corridor agreements and drone strikes on Danube port grain elevators.',
          crude_oil_impulse: '+2.1% supportive pressure',
          gold_impulse: '+$12.00/oz modest gain',
          dxy_reaction: '+0.15%',
          risk_crypto_reaction: 'Wheat futures spiked +8.2%, EURUSD dropped -45 pips'
        }
      ],
      volatility_forecast: {
        expected_gas_spike_pct: '+5.2%',
        expected_gold_range_usd: [2638.0, 2675.0],
        implied_risk_premium: '+$22.00/oz'
      }
    }
  };

  const DEFAULT_CATALYSTS = [
    {
      id: 'CAT-FED-001',
      title: 'FOMC Interest Rate Decision & Powell Briefing',
      time_label: 'in 14.5 hours',
      impact: 'HIGH',
      institution: 'Federal Reserve',
      consensus: '4.75% (-25 bps cut)',
      blackout_buffer: true,
      precedent: '2024-09-18: 50 bps cut triggered Gold +$28, DXY -0.55%, BTC +3.4%.'
    },
    {
      id: 'CAT-CPI-002',
      title: 'US Consumer Price Index (CPI YoY / MoM)',
      time_label: 'in 38.0 hours',
      impact: 'HIGH',
      institution: 'US BLS',
      consensus: '2.3% YoY / 0.2% MoM',
      blackout_buffer: false,
      precedent: '2024-06-12: Cool CPI surprise (3.3%) caused DXY -0.85%, Gold +$32.'
    },
    {
      id: 'CAT-NFP-003',
      title: 'US Non-Farm Payrolls & Unemployment Rate',
      time_label: 'in 3.5 days',
      impact: 'HIGH',
      institution: 'US Labor Dept',
      consensus: '+145K jobs / 4.2% Unemp',
      blackout_buffer: false,
      precedent: '2024-09-06: Below-consensus NFP pushed US10Y down 7 bps, Gold +$18.'
    },
    {
      id: 'CAT-BOJ-005',
      title: 'Bank of Japan Policy Meeting & Ueda Briefing',
      time_label: 'in 6.5 days',
      impact: 'HIGH',
      institution: 'Bank of Japan',
      consensus: '0.25% Policy Rate Hold',
      blackout_buffer: false,
      precedent: '2024-07-31: Surprise hike triggered 800 pip USDJPY drop & carry unwind.'
    }
  ];

  /**
   * Helper: Convert lat/lon to 3D Cartesian coordinates on sphere of radius r.
   */
  function latLonToVector3(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);
    return { x, y, z };
  }

  // ==========================================================================
  // Class: MacroContagionSphere3D
  // ==========================================================================

  class MacroContagionSphere3D {
    constructor(container, options = {}) {
      if (!container) {
        throw new Error('MacroContagionSphere3D requires a valid DOM container element or selector.');
      }
      this.container = typeof container === 'string' ? document.querySelector(container) : container;
      if (!this.container) {
        throw new Error(`MacroContagionSphere3D container element not found: ${container}`);
      }

      this.options = Object.assign({
        width: this.container.clientWidth || 800,
        height: this.container.clientHeight || 600,
        autoRotate: true,
        autoRotateSpeed: 0.0018,
        sphereRadius: 1.0,
        onHotspotSelect: null,
        onNodeSelect: null,
        telemetryData: null
      }, options);

      this.THREE = window.THREE || null;
      if (!this.THREE) {
        console.warn('Three.js (window.THREE) is not loaded yet. MacroContagionSphere3D will initialize DOM HUD and await WebGL.');
      }

      // State containers
      this.isDisposed = false;
      this.animFrameId = null;
      this.hotspots = Object.assign({}, DEFAULT_HOTSPOTS);
      this.catalysts = DEFAULT_CATALYSTS.slice();
      this.nodes = [];
      this.splines = [];
      this.pulseRings = [];
      this.shockwaves = [];
      this.interactiveObjects = [];

      // Camera tween state
      this.targetCameraPos = null;
      this.targetLookAt = null;
      this.currentLookAt = { x: 0, y: 0, z: 0 };
      this.isInteracting = false;

      // Mouse tracking for raycasting & rotation
      this.mouse = { x: 0, y: 0 };
      this.pointerDown = false;
      this.previousPointerPos = { x: 0, y: 0 };

      // Initialize
      this._initDOMStructure();
      if (this.THREE) {
        this._initWebGLScene();
        this._buildPlanetaryGlobe();
        this._buildHotspotMarkers();
        this._buildNetworkNodes();
        this._buildContagionSplines();
        this._setupEventListeners();
        this._startAnimationLoop();
      }

      // Bind global event ingress
      this._boundShockwaveHandler = (e) => this.injectShockwave(e.detail);
      window.addEventListener('jarvis:macro:shockwave', this._boundShockwaveHandler);
    }

    // ------------------------------------------------------------------------
    // DOM & HUD Setup
    // ------------------------------------------------------------------------

    _initDOMStructure() {
      // Ensure container has relative positioning
      this.container.style.position = 'relative';
      this.container.style.overflow = 'hidden';
      this.container.style.backgroundColor = '#030712';
      this.container.style.userSelect = 'none';

      // HUD Overlay Layer
      this.hudOverlay = document.createElement('div');
      this.hudOverlay.className = 'macro-sphere-hud-overlay';
      this.hudOverlay.style.position = 'absolute';
      this.hudOverlay.style.inset = '0';
      this.hudOverlay.style.pointerEvents = 'none';
      this.hudOverlay.style.zIndex = '10';
      this.container.appendChild(this.hudOverlay);

      // Top Status Bar
      const topBar = document.createElement('div');
      topBar.style.position = 'absolute';
      topBar.style.top = '12px';
      topBar.style.left = '16px';
      topBar.style.right = '16px';
      topBar.style.display = 'flex';
      topBar.style.justifyContent = 'space-between';
      topBar.style.alignItems = 'center';
      topBar.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#00f3ff; box-shadow:0 0 8px #00f3ff; animation:pulse 2s infinite;"></span>
          <span style="font-family:monospace; font-size:11px; font-weight:700; color:#00f3ff; letter-spacing:1px;">J.A.R.V.I.S. 3D MACRO CONTAGION SPHERE</span>
          <span style="font-family:monospace; font-size:10px; color:#64748b; background:rgba(30,41,59,0.7); padding:2px 6px; border-radius:4px; border:1px solid rgba(100,116,139,0.3);">WORLD MONITOR ENGINE</span>
        </div>
        <div style="display:flex; gap:8px;">
          <button id="btnShockDxy" style="pointer-events:auto; background:rgba(0,243,255,0.12); color:#00f3ff; border:1px solid rgba(0,243,255,0.4); font-family:monospace; font-size:10px; padding:3px 8px; border-radius:4px; cursor:pointer;">⚡ SHOCK DXY +1.5%</button>
          <button id="btnShockOil" style="pointer-events:auto; background:rgba(255,170,0,0.12); color:#ffaa00; border:1px solid rgba(255,170,0,0.4); font-family:monospace; font-size:10px; padding:3px 8px; border-radius:4px; cursor:pointer;">🔥 SHOCK OIL +5%</button>
          <button id="btnResetView" style="pointer-events:auto; background:rgba(30,41,59,0.8); color:#94a3b8; border:1px solid rgba(100,116,139,0.3); font-family:monospace; font-size:10px; padding:3px 8px; border-radius:4px; cursor:pointer;">↺ RESET VIEW</button>
        </div>
      `;
      this.hudOverlay.appendChild(topBar);

      // Wire quick shock buttons
      const btnDxy = topBar.querySelector('#btnShockDxy');
      const btnOil = topBar.querySelector('#btnShockOil');
      const btnReset = topBar.querySelector('#btnResetView');
      if (btnDxy) btnDxy.addEventListener('click', () => this.injectShockwave({ driver: 'DXY', delta_pct: 1.5 }));
      if (btnOil) btnOil.addEventListener('click', () => this.injectShockwave({ driver: 'OIL', delta_pct: 5.0 }));
      if (btnReset) btnReset.addEventListener('click', () => this.resetCameraView());

      // Forward Catalyst Timeline Overlay Component
      this._buildCatalystTimelineOverlay();

      // Tactical Dossier Slide-Over Modal
      this._buildTacticalDossierModal();
    }

    _buildCatalystTimelineOverlay() {
      this.catalystContainer = document.createElement('div');
      this.catalystContainer.style.position = 'absolute';
      this.catalystContainer.style.bottom = '12px';
      this.catalystContainer.style.left = '16px';
      this.catalystContainer.style.right = '16px';
      this.catalystContainer.style.background = 'rgba(11, 15, 25, 0.88)';
      this.catalystContainer.style.backdropFilter = 'blur(10px)';
      this.catalystContainer.style.webkitBackdropFilter = 'blur(10px)';
      this.catalystContainer.style.border = '1px solid rgba(0, 243, 255, 0.25)';
      this.catalystContainer.style.borderRadius = '8px';
      this.catalystContainer.style.padding = '8px 12px';
      this.catalystContainer.style.pointerEvents = 'auto';

      let itemsHtml = this.catalysts.map((c, i) => `
        <div class="catalyst-item" data-idx="${i}" style="flex:1; min-width:180px; background:rgba(30,41,59,0.4); border:1px solid rgba(100,116,139,0.25); border-radius:6px; padding:6px 8px; cursor:pointer; transition:all 0.2s ease;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;">
            <span style="font-family:monospace; font-size:9px; color:#00f3ff; font-weight:700;">${c.institution}</span>
            <span style="font-family:monospace; font-size:9px; color:${c.blackout_buffer ? '#f59e0b' : '#38bdf8'}; background:${c.blackout_buffer ? 'rgba(245,158,11,0.2)' : 'rgba(56,189,248,0.1)'}; padding:1px 4px; border-radius:3px;">
              ${c.blackout_buffer ? '⚠ BLACKOUT' : c.time_label}
            </span>
          </div>
          <div style="font-size:11px; font-weight:600; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.title}</div>
          <div style="font-family:monospace; font-size:9px; color:#94a3b8; margin-top:2px;">Exp: <span style="color:#e2e8f0;">${c.consensus}</span></div>
        </div>
      `).join('');

      this.catalystContainer.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="color:#38bdf8; font-size:11px;">⚡</span>
            <span style="font-family:monospace; font-size:10px; font-weight:700; color:#e2e8f0; letter-spacing:0.5px;">FORWARD CATALYST TIMELINE</span>
            <span style="font-family:monospace; font-size:9px; color:#f59e0b; background:rgba(245,158,11,0.15); padding:1px 5px; border-radius:3px; border:1px solid rgba(245,158,11,0.3);">15M BLACKOUT ACTIVE</span>
          </div>
          <span style="font-family:monospace; font-size:9px; color:#64748b;">CLICK CATALYST FOR HISTORICAL PRECEDENTS</span>
        </div>
        <div style="display:flex; gap:8px; overflow-x:auto; padding-bottom:2px;">
          ${itemsHtml}
        </div>
      `;

      this.hudOverlay.appendChild(this.catalystContainer);

      // Event delegation for catalyst precedent popover
      this.catalystContainer.addEventListener('click', (e) => {
        const item = e.target.closest('.catalyst-item');
        if (!item) return;
        const idx = parseInt(item.dataset.idx, 10);
        const cat = this.catalysts[idx];
        if (cat) this._showCatalystPrecedent(cat);
      });
    }

    _showCatalystPrecedent(cat) {
      alert(`[J.A.R.V.I.S. CATALYST PRECEDENT]\n\nEvent: ${cat.title}\nInstitution: ${cat.institution}\nScheduled: ${cat.time_label}\nConsensus: ${cat.consensus}\n\nHistorical Price Reaction Precedent:\n${cat.precedent}\n\nRisk Rule: Strict 15-minute news blackout buffer enforced for FundingPips compliance.`);
    }

    _buildTacticalDossierModal() {
      this.dossierModal = document.createElement('div');
      this.dossierModal.className = 'macro-sphere-dossier-modal';
      this.dossierModal.style.position = 'absolute';
      this.dossierModal.style.top = '48px';
      this.dossierModal.style.right = '16px';
      this.dossierModal.style.width = '380px';
      this.dossierModal.style.maxHeight = 'calc(100% - 140px)';
      this.dossierModal.style.overflowY = 'auto';
      this.dossierModal.style.background = 'rgba(10, 15, 26, 0.94)';
      this.dossierModal.style.backdropFilter = 'blur(16px)';
      this.dossierModal.style.webkitBackdropFilter = 'blur(16px)';
      this.dossierModal.style.border = '1px solid rgba(0, 243, 255, 0.35)';
      this.dossierModal.style.borderRadius = '10px';
      this.dossierModal.style.padding = '14px';
      this.dossierModal.style.boxShadow = '0 10px 35px rgba(0, 0, 0, 0.7)';
      this.dossierModal.style.display = 'none';
      this.dossierModal.style.pointerEvents = 'auto';
      this.dossierModal.style.zIndex = '30';

      this.hudOverlay.appendChild(this.dossierModal);
    }

    // ------------------------------------------------------------------------
    // WebGL Three.js Scene Initialization
    // ------------------------------------------------------------------------

    _initWebGLScene() {
      const THREE = this.THREE;
      const width = this.options.width;
      const height = this.options.height;

      // 1. Scene & Camera
      this.scene = new THREE.Scene();
      this.scene.fog = new THREE.FogExp2(0x030712, 0.12);

      this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
      this.camera.position.set(0, 1.2, 5.2);
      this.scene.add(this.camera);

      // 2. Renderer
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setClearColor(0x030712, 1);
      this.container.appendChild(this.renderer.domElement);

      // 3. Lighting
      const ambientLight = new THREE.AmbientLight(0x1e293b, 1.5);
      this.scene.add(ambientLight);

      this.sunLight = new THREE.DirectionalLight(0xffffff, 2.0);
      this.sunLight.position.set(5, 4, 3);
      this.scene.add(this.sunLight);

      const rimLight = new THREE.DirectionalLight(0x00f3ff, 1.2);
      rimLight.position.set(-5, -2, -3);
      this.scene.add(rimLight);

      // 4. Groups
      this.globeGroup = new THREE.Group();
      this.scene.add(this.globeGroup);

      this.networkGroup = new THREE.Group();
      this.scene.add(this.networkGroup);

      // 5. Starfield
      this._createStarfield();

      // 6. Raycaster
      this.raycaster = new THREE.Raycaster();
    }

    _createStarfield() {
      const THREE = this.THREE;
      const starsCount = 1200;
      const starGeo = new THREE.BufferGeometry();
      const positions = new Float32Array(starsCount * 3);
      const colors = new Float32Array(starsCount * 3);

      for (let i = 0; i < starsCount; i++) {
        const radius = 15.0 + Math.random() * 25.0;
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos((Math.random() * 2) - 1);
        positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = radius * Math.cos(phi);
        positions[i * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);

        // Subtly colored stars (cyan, amber, white)
        const rnd = Math.random();
        if (rnd > 0.7) {
          colors[i * 3] = 0.0; colors[i * 3 + 1] = 0.95; colors[i * 3 + 2] = 1.0;
        } else if (rnd > 0.5) {
          colors[i * 3] = 1.0; colors[i * 3 + 1] = 0.7; colors[i * 3 + 2] = 0.2;
        } else {
          colors[i * 3] = 0.9; colors[i * 3 + 1] = 0.95; colors[i * 3 + 2] = 1.0;
        }
      }

      starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      starGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

      const starMat = new THREE.PointsMaterial({
        size: 0.06,
        vertexColors: true,
        transparent: true,
        opacity: 0.85
      });
      const starPoints = new THREE.Points(starGeo, starMat);
      this.scene.add(starPoints);
    }

    // ------------------------------------------------------------------------
    // 3D Planetary Globe Architecture
    // ------------------------------------------------------------------------

    _buildPlanetaryGlobe() {
      const THREE = this.THREE;
      const r = this.options.sphereRadius;

      // 1. Procedural Cybernetic Earth Surface
      const earthTex = this._generateProceduralEarthTexture();
      const globeGeo = new THREE.SphereGeometry(r, 64, 64);
      const globeMat = new THREE.MeshPhongMaterial({
        map: earthTex,
        bumpScale: 0.04,
        specular: new THREE.Color(0x0f2744),
        shininess: 25
      });
      this.globeMesh = new THREE.Mesh(globeGeo, globeMat);
      this.globeGroup.add(this.globeMesh);

      // 2. Tactical Lat/Lon Graticule Wireframe Sphere
      const graticuleGeo = new THREE.SphereGeometry(r * 1.002, 24, 24);
      const graticuleMat = new THREE.MeshBasicMaterial({
        color: 0x00f3ff,
        wireframe: true,
        transparent: true,
        opacity: 0.12
      });
      const graticuleMesh = new THREE.Mesh(graticuleGeo, graticuleMat);
      this.globeGroup.add(graticuleMesh);

      // 3. Atmospheric Fresnel Glow Shell
      const atmosphereGeo = new THREE.SphereGeometry(r * 1.06, 48, 48);
      const atmosphereMat = new THREE.ShaderMaterial({
        vertexShader: `
          varying vec3 vNormal;
          void main() {
            vNormal = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          varying vec3 vNormal;
          void main() {
            float intensity = pow(0.65 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
            gl_FragColor = vec4(0.0, 0.95, 1.0, 1.0) * intensity * 0.85;
          }
        `,
        blending: THREE.AdditiveBlending,
        side: THREE.BackSide,
        transparent: true
      });
      const atmosphereMesh = new THREE.Mesh(atmosphereGeo, atmosphereMat);
      this.globeGroup.add(atmosphereMesh);
    }

    _generateProceduralEarthTexture() {
      const THREE = this.THREE;
      const canvas = document.createElement('canvas');
      canvas.width = 1024;
      canvas.height = 512;
      const ctx = canvas.getContext('2d');

      // Deep oceanic bathymetry
      const grad = ctx.createLinearGradient(0, 0, 0, 512);
      grad.addColorStop(0, '#06101e');
      grad.addColorStop(0.5, '#040b15');
      grad.addColorStop(1, '#06101e');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 1024, 512);

      // Latitude and Longitude Grid Lines
      ctx.strokeStyle = 'rgba(0, 243, 255, 0.15)';
      ctx.lineWidth = 1;
      for (let x = 0; x <= 1024; x += 64) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, 512);
        ctx.stroke();
      }
      for (let y = 0; y <= 512; y += 42) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(1024, y);
        ctx.stroke();
      }

      // Procedural continents representation (stylized cybernetic landmass dots)
      ctx.fillStyle = 'rgba(14, 165, 233, 0.55)';
      const drawContinentBlob = (cx, cy, rx, ry) => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
        ctx.fill();
      };

      // Americas
      drawContinentBlob(260, 180, 70, 55);
      drawContinentBlob(320, 340, 50, 75);
      // Eurasia & Africa
      drawContinentBlob(580, 160, 110, 60);
      drawContinentBlob(550, 280, 65, 75);
      drawContinentBlob(720, 210, 90, 65);
      // Australia
      drawContinentBlob(820, 360, 45, 35);

      const texture = new THREE.CanvasTexture(canvas);
      texture.wrapS = THREE.RepeatWrapping;
      texture.wrapT = THREE.ClampToEdgeWrapping;
      return texture;
    }

    // ------------------------------------------------------------------------
    // Geopolitical Hotspot Beacons & Concentric Pulsing Rings
    // ------------------------------------------------------------------------

    _buildHotspotMarkers() {
      const THREE = this.THREE;
      const r = this.options.sphereRadius;

      Object.values(this.hotspots).forEach((h) => {
        const coords = latLonToVector3(h.latitude, h.longitude, r * 1.008);
        const normal = new THREE.Vector3(coords.x, coords.y, coords.z).normalize();

        // 1. Hotspot Core Beacon Sphere
        const coreGeo = new THREE.SphereGeometry(0.035, 16, 16);
        const isCritical = h.threat_level.includes('WARZONE');
        const colorHex = isCritical ? 0xff2255 : 0xffaa00;

        const coreMat = new THREE.MeshBasicMaterial({ color: colorHex });
        const coreMesh = new THREE.Mesh(coreGeo, coreMat);
        coreMesh.position.set(coords.x, coords.y, coords.z);
        coreMesh.userData = { type: 'HOTSPOT', data: h };
        this.globeGroup.add(coreMesh);
        this.interactiveObjects.push(coreMesh);

        // 2. Concentric Pulsing Rings (Surface-aligned)
        const ringGeo = new THREE.RingGeometry(0.04, 0.07, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: colorHex,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.8
        });
        const ringMesh = new THREE.Mesh(ringGeo, ringMat);
        ringMesh.position.set(coords.x, coords.y, coords.z);
        ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
        this.globeGroup.add(ringMesh);

        this.pulseRings.push({
          mesh: ringMesh,
          initialRadius: 0.04,
          maxRadius: 0.16,
          scale: 1.0,
          speed: 0.008 + (h.disruption_pct / 1000.0),
          material: ringMat
        });
      });
    }

    // ------------------------------------------------------------------------
    // Network Graph: Macro Drivers & Target Asset Nodes
    // ------------------------------------------------------------------------

    _buildNetworkNodes() {
      const THREE = this.THREE;

      // 1. Macro Driver Nodes (Positioned in upper orbital arc)
      const drivers = [
        { id: 'DXY', name: 'US DOLLAR INDEX', val: '104.25', delta: '-0.35%', color: 0x00f3ff, pos: [-2.2, 2.4, 0.5] },
        { id: 'US10Y', name: 'US 10Y YIELD', val: '4.285%', delta: '-1.20%', color: 0xffd700, pos: [0.0, 2.8, 0.8] },
        { id: 'OIL', name: 'CRUDE OIL (WTI)', val: '$78.60', delta: '+2.45%', color: 0xff5500, pos: [2.2, 2.4, 0.5] }
      ];

      drivers.forEach((d) => {
        const node = this._createNodeMesh(d.id, d.name, d.val, d.delta, d.color, d.pos, 'DRIVER');
        this.nodes.push(node);
      });

      // 2. Target Asset Nodes (Positioned in lower receiving orbit)
      const assets = [
        { id: 'XAUUSD', name: 'GOLD (SPOT)', val: '$2,654.50', delta: '+0.85%', color: 0xffd700, pos: [-2.8, -0.8, 1.2] },
        { id: 'EURUSD', name: 'EUR / USD', val: '1.0865', delta: '+0.32%', color: 0x00f3ff, pos: [-1.8, -1.8, 1.5] },
        { id: 'USDJPY', name: 'USD / JPY', val: '152.20', delta: '-0.55%', color: 0x00f3ff, pos: [-0.5, -2.2, 1.4] },
        { id: 'GBPUSD', name: 'GBP / USD', val: '1.3040', delta: '+0.28%', color: 0x00f3ff, pos: [0.8, -2.2, 1.4] },
        { id: 'BTCUSD', name: 'BITCOIN', val: '$64,850', delta: '+2.10%', color: 0xa855f7, pos: [2.0, -1.8, 1.5] },
        { id: 'SOLUSD', name: 'SOLANA', val: '$158.40', delta: '+4.80%', color: 0xa855f7, pos: [2.8, -0.8, 1.2] }
      ];

      assets.forEach((a) => {
        const node = this._createNodeMesh(a.id, a.name, a.val, a.delta, a.color, a.pos, 'RECEIVER');
        this.nodes.push(node);
      });
    }

    _createNodeMesh(id, name, val, delta, colorHex, posArray, nodeType) {
      const THREE = this.THREE;
      const group = new THREE.Group();
      group.position.set(posArray[0], posArray[1], posArray[2]);

      // Core glowing sphere
      const coreGeo = new THREE.SphereGeometry(0.09, 20, 20);
      const coreMat = new THREE.MeshPhongMaterial({
        color: colorHex,
        emissive: colorHex,
        emissiveIntensity: 0.8,
        shininess: 50
      });
      const coreMesh = new THREE.Mesh(coreGeo, coreMat);
      coreMesh.userData = { type: 'NODE', id, name, val, delta, nodeType };
      group.add(coreMesh);
      this.interactiveObjects.push(coreMesh);

      // Outer wireframe halo ring
      const haloGeo = new THREE.RingGeometry(0.12, 0.14, 24);
      const haloMat = new THREE.MeshBasicMaterial({ color: colorHex, side: THREE.DoubleSide, transparent: true, opacity: 0.6 });
      const haloMesh = new THREE.Mesh(haloGeo, haloMat);
      group.add(haloMesh);

      // Billboard Canvas Sprite Label
      const sprite = this._createBillboardSprite(id, val, delta, colorHex);
      sprite.position.set(0, 0.28, 0);
      group.add(sprite);

      this.networkGroup.add(group);
      return { id, group, coreMesh, haloMesh, pos: new THREE.Vector3(...posArray), nodeType };
    }

    _createBillboardSprite(id, val, delta, colorHex) {
      const THREE = this.THREE;
      const canvas = document.createElement('canvas');
      canvas.width = 256;
      canvas.height = 96;
      const ctx = canvas.getContext('2d');

      // Rounded container pill
      ctx.fillStyle = 'rgba(10, 15, 26, 0.85)';
      ctx.strokeStyle = '#00f3ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(8, 8, 240, 80, 12);
      ctx.fill();
      ctx.stroke();

      // Text labels
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 24px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(id, 128, 40);

      const isPositive = delta.startsWith('+');
      ctx.fillStyle = isPositive ? '#10b981' : '#f43f5e';
      ctx.font = '18px monospace';
      ctx.fillText(`${val} (${delta})`, 128, 68);

      const texture = new THREE.CanvasTexture(canvas);
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(0.7, 0.26, 1.0);
      return sprite;
    }

    // ------------------------------------------------------------------------
    // Animated 3D CatmullRom Particle Splines
    // ------------------------------------------------------------------------

    _buildContagionSplines() {
      const THREE = this.THREE;

      // Define contagion linkages: [driverId, targetId, correlation, velocity, colorHex]
      const linkages = [
        // DXY Drivers
        ['DXY', 'XAUUSD', -0.72, 1.8, 0x00f3ff],
        ['DXY', 'EURUSD', -0.96, 2.4, 0x00f3ff],
        ['DXY', 'USDJPY', 0.62, 1.4, 0xff3355],
        ['DXY', 'GBPUSD', -0.89, 2.0, 0x00f3ff],
        ['DXY', 'BTCUSD', -0.48, 1.2, 0x00f3ff],
        ['DXY', 'SOLUSD', -0.52, 1.5, 0x00f3ff],

        // US10Y Yields
        ['US10Y', 'XAUUSD', -0.64, 1.6, 0x00f3ff],
        ['US10Y', 'USDJPY', 0.81, 2.2, 0xff3355],
        ['US10Y', 'BTCUSD', -0.44, 1.1, 0x00f3ff],

        // Crude Oil Shocks
        ['OIL', 'XAUUSD', 0.58, 2.0, 0xffaa00],
        ['OIL', 'EURUSD', -0.54, 1.6, 0xff3355],
        ['OIL', 'BTCUSD', -0.18, 0.9, 0xff3355]
      ];

      linkages.forEach(([sourceId, targetId, corr, vel, colorHex]) => {
        const sourceNode = this.nodes.find(n => n.id === sourceId);
        const targetNode = this.nodes.find(n => n.id === targetId);

        if (!sourceNode || !targetNode) return;

        // Form 3D arc through elevated midpoint
        const p1 = sourceNode.pos;
        const p3 = targetNode.pos;
        const midX = (p1.x + p3.x) * 0.5;
        const midY = (p1.y + p3.y) * 0.5 + 0.6; // Arch elevation
        const midZ = (p1.z + p3.z) * 0.5 + 0.8;
        const p2 = new THREE.Vector3(midX, midY, midZ);

        const curve = new THREE.CatmullRomCurve3([p1, p2, p3]);

        // Base faint guide line
        const points = curve.getPoints(50);
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        const lineMat = new THREE.LineBasicMaterial({
          color: colorHex,
          transparent: true,
          opacity: 0.18
        });
        const lineMesh = new THREE.Line(lineGeo, lineMat);
        this.networkGroup.add(lineMesh);

        // Animated particles along the curve
        const particleCount = 12;
        const pGeo = new THREE.BufferGeometry();
        const pPositions = new Float32Array(particleCount * 3);
        pGeo.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));

        const pMat = new THREE.PointsMaterial({
          color: colorHex,
          size: 0.05,
          transparent: true,
          opacity: 0.85,
          blending: THREE.AdditiveBlending
        });
        const particlePoints = new THREE.Points(pGeo, pMat);
        this.networkGroup.add(particlePoints);

        this.splines.push({
          curve,
          particlePoints,
          particleCount,
          offsets: Array.from({ length: particleCount }, (_, idx) => idx / particleCount),
          speed: vel * 0.003,
          colorHex
        });
      });
    }

    // ------------------------------------------------------------------------
    // Interaction Handlers (Raycasting, Drag, Fly-To Tween)
    // ------------------------------------------------------------------------

    _setupEventListeners() {
      const el = this.renderer.domElement;

      el.addEventListener('pointerdown', (e) => {
        this.pointerDown = true;
        this.previousPointerPos = { x: e.clientX, y: e.clientY };
      });

      window.addEventListener('pointerup', () => {
        this.pointerDown = false;
      });

      el.addEventListener('pointermove', (e) => {
        const rect = el.getBoundingClientRect();
        this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

        if (this.pointerDown) {
          const deltaX = e.clientX - this.previousPointerPos.x;
          const deltaY = e.clientY - this.previousPointerPos.y;
          this.globeGroup.rotation.y += deltaX * 0.005;
          this.globeGroup.rotation.x += deltaY * 0.005;
          this.previousPointerPos = { x: e.clientX, y: e.clientY };
        }
      });

      el.addEventListener('click', (e) => {
        this._handleCanvasClick();
      });

      window.addEventListener('resize', () => this._onWindowResize());
    }

    _handleCanvasClick() {
      const THREE = this.THREE;
      if (!this.camera || !this.raycaster) return;

      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.interactiveObjects, true);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        const data = hit.userData;

        if (data.type === 'HOTSPOT') {
          this.selectHotspot(data.data);
        } else if (data.type === 'NODE') {
          this.selectNode(data);
        }
      }
    }

    selectHotspot(hotspot) {
      // 1. Dispatch custom event
      const eventDetail = {
        hotspot_id: hotspot.hotspot_id,
        title: hotspot.name,
        region: hotspot.region,
        threat_level: hotspot.threat_level,
        disruption_pct: hotspot.disruption_pct,
        baseline_mbd: hotspot.baseline_mbd,
        current_mbd: hotspot.current_mbd,
        commodity_multipliers: hotspot.commodity_multipliers,
        historical_dossier: hotspot.historical_dossier,
        volatility_forecast: hotspot.volatility_forecast
      };

      window.dispatchEvent(new CustomEvent('jarvis:hotspot:selected', { detail: eventDetail }));
      if (typeof this.options.onHotspotSelect === 'function') {
        this.options.onHotspotSelect(eventDetail);
      }

      // 2. Trigger surface shockwave ripple
      this.triggerShockwave(hotspot.hotspot_id);

      // 3. Smooth Camera Fly-To Transition
      const coords = latLonToVector3(hotspot.latitude, hotspot.longitude, 2.5);
      this.targetCameraPos = { x: coords.x * 1.5, y: coords.y * 1.5 + 0.4, z: coords.z * 1.5 };
      this.targetLookAt = { x: coords.x * 0.4, y: coords.y * 0.4, z: coords.z * 0.4 };

      // 4. Render Tactical Dossier Modal
      this._renderDossierModal(hotspot);
    }

    selectNode(nodeData) {
      const eventDetail = {
        node_id: nodeData.id,
        name: nodeData.name,
        price_val: nodeData.val,
        delta: nodeData.delta,
        node_type: nodeData.nodeType
      };

      window.dispatchEvent(new CustomEvent('jarvis:node:selected', { detail: eventDetail }));
      if (typeof this.options.onNodeSelect === 'function') {
        this.options.onNodeSelect(eventDetail);
      }
    }

    _renderDossierModal(h) {
      const isCritical = h.threat_level.includes('WARZONE');
      const badgeColor = isCritical ? '#ef4444' : '#f59e0b';

      let precedentsHtml = (h.historical_dossier || []).map(p => `
        <div style="background:rgba(30,41,59,0.5); border:1px solid rgba(100,116,139,0.3); border-radius:6px; padding:8px; margin-bottom:8px;">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="font-family:monospace; font-size:10px; font-weight:700; color:#38bdf8;">${p.date} — ${p.title}</span>
          </div>
          <div style="font-size:11px; color:#cbd5e1; margin-bottom:6px;">${p.description}</div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:4px; font-family:monospace; font-size:9px;">
            <div style="background:rgba(0,0,0,0.3); padding:3px 5px; border-radius:3px;">
              <span style="color:#f59e0b;">Crude Oil:</span> ${p.crude_oil_impulse}
            </div>
            <div style="background:rgba(0,0,0,0.3); padding:3px 5px; border-radius:3px;">
              <span style="color:#fbbf24;">Gold:</span> ${p.gold_impulse}
            </div>
            <div style="background:rgba(0,0,0,0.3); padding:3px 5px; border-radius:3px;">
              <span style="color:#94a3b8;">DXY:</span> ${p.dxy_reaction}
            </div>
            <div style="background:rgba(0,0,0,0.3); padding:3px 5px; border-radius:3px;">
              <span style="color:#a855f7;">Crypto:</span> ${p.risk_crypto_reaction}
            </div>
          </div>
        </div>
      `).join('');

      let multipliersHtml = Object.entries(h.commodity_multipliers || {}).map(([sym, mul]) => `
        <span style="background:rgba(15,23,42,0.8); border:1px solid rgba(0,243,255,0.25); color:#e2e8f0; font-family:monospace; font-size:9px; padding:2px 6px; border-radius:4px;">
          ${sym}: <b style="color:${mul > 0 ? '#10b981' : '#f43f5e'};">${mul > 0 ? '+' : ''}${mul}x</b>
        </span>
      `).join('');

      this.dossierModal.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px; border-bottom:1px solid rgba(100,116,139,0.3); padding-bottom:8px;">
          <div>
            <div style="font-family:monospace; font-size:10px; color:#00f3ff; font-weight:700;">TACTICAL DOSSIER // CHOKEPOINT</div>
            <div style="font-size:14px; font-weight:700; color:#f8fafc;">${h.name}</div>
            <div style="font-size:10px; color:#94a3b8;">${h.region} (${h.latitude}°N, ${h.longitude}°E)</div>
          </div>
          <button id="btnCloseDossier" style="background:transparent; border:none; color:#94a3b8; font-size:18px; cursor:pointer; line-height:1;">✕</button>
        </div>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px; margin-bottom:10px;">
          <div style="background:rgba(15,23,42,0.6); padding:6px; border-radius:6px; border:1px solid rgba(100,116,139,0.2);">
            <div style="font-family:monospace; font-size:9px; color:#94a3b8;">THREAT LEVEL</div>
            <div style="font-family:monospace; font-size:11px; font-weight:700; color:${badgeColor};">${h.threat_level}</div>
          </div>
          <div style="background:rgba(15,23,42,0.6); padding:6px; border-radius:6px; border:1px solid rgba(100,116,139,0.2);">
            <div style="font-family:monospace; font-size:9px; color:#94a3b8;">FLOW DISRUPTION</div>
            <div style="font-family:monospace; font-size:11px; font-weight:700; color:#ef4444;">${h.disruption_pct}%</div>
          </div>
        </div>

        <div style="font-size:11px; color:#cbd5e1; margin-bottom:10px; line-height:1.4;">
          ${h.status_narrative}
        </div>

        <div style="margin-bottom:10px;">
          <div style="font-family:monospace; font-size:9px; color:#94a3b8; margin-bottom:4px;">COMMODITY VOLATILITY MULTIPLIERS</div>
          <div style="display:flex; flex-wrap:wrap; gap:4px;">
            ${multipliersHtml}
          </div>
        </div>

        <div>
          <div style="font-family:monospace; font-size:9px; color:#00f3ff; margin-bottom:6px; font-weight:700;">HISTORICAL MARKET REACTION DOSSIER</div>
          ${precedentsHtml}
        </div>
      `;

      this.dossierModal.style.display = 'block';

      const btnClose = this.dossierModal.querySelector('#btnCloseDossier');
      if (btnClose) {
        btnClose.addEventListener('click', () => {
          this.dossierModal.style.display = 'none';
        });
      }
    }

    // ------------------------------------------------------------------------
    // Shockwave Ripples & External Event Ingress
    // ------------------------------------------------------------------------

    triggerShockwave(hotspotId) {
      const THREE = this.THREE;
      if (!THREE) return;

      const h = this.hotspots[hotspotId];
      if (!h) return;

      const r = this.options.sphereRadius;
      const coords = latLonToVector3(h.latitude, h.longitude, r * 1.01);
      const normal = new THREE.Vector3(coords.x, coords.y, coords.z).normalize();

      const shockGeo = new THREE.RingGeometry(0.02, 0.05, 32);
      const shockMat = new THREE.MeshBasicMaterial({
        color: 0xffaa00,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 1.0
      });
      const shockMesh = new THREE.Mesh(shockGeo, shockMat);
      shockMesh.position.set(coords.x, coords.y, coords.z);
      shockMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
      this.globeGroup.add(shockMesh);

      this.shockwaves.push({
        mesh: shockMesh,
        radius: 0.02,
        maxRadius: 0.45,
        growth: 0.015,
        opacity: 1.0,
        material: shockMat
      });
    }

    injectShockwave(payload) {
      if (!payload || !payload.driver) return;

      const driver = payload.driver.toUpperCase();
      const delta = payload.delta_pct || 1.0;

      // Find driver node
      const dNode = this.nodes.find(n => n.id === driver);
      if (dNode && this.THREE) {
        // Flash driver halo
        dNode.haloMesh.material.color.setHex(0xffaa00);
        setTimeout(() => dNode.haloMesh.material.color.setHex(0x00f3ff), 2000);
      }

      // Accelerate associated splines temporarily
      this.splines.forEach((s) => {
        s.speed *= 2.5;
        setTimeout(() => { s.speed /= 2.5; }, 4000);
      });

      // If Oil shock, also ripple Middle Eastern hotspots
      if (driver === 'OIL') {
        this.triggerShockwave('red_sea');
        this.triggerShockwave('hormuz_strait');
      }

      console.log(`[MacroContagionSphere3D] Injected macro shockwave for ${driver}: ${delta > 0 ? '+' : ''}${delta}%`);
    }

    resetCameraView() {
      this.targetCameraPos = { x: 0, y: 1.2, z: 5.2 };
      this.targetLookAt = { x: 0, y: 0, z: 0 };
      if (this.dossierModal) this.dossierModal.style.display = 'none';
    }

    // ------------------------------------------------------------------------
    // Animation Loop
    // ------------------------------------------------------------------------

    _startAnimationLoop() {
      const render = () => {
        if (this.isDisposed) return;
        this.animFrameId = requestAnimationFrame(render);

        // 1. Globe auto-rotation if enabled and not dragging
        if (this.options.autoRotate && !this.pointerDown && this.globeGroup) {
          this.globeGroup.rotation.y += this.options.autoRotateSpeed;
        }

        // 2. Concentric hotspot pulsing rings
        this.pulseRings.forEach((p) => {
          p.scale += p.speed;
          if (p.scale > 3.5) {
            p.scale = 1.0;
            p.material.opacity = 0.8;
          } else {
            p.material.opacity = Math.max(0, 0.8 * (1.0 - (p.scale - 1.0) / 2.5));
          }
          p.mesh.scale.set(p.scale, p.scale, 1.0);
        });

        // 3. Shockwave ripples
        for (let i = this.shockwaves.length - 1; i >= 0; i--) {
          const sw = this.shockwaves[i];
          sw.radius += sw.growth;
          sw.opacity -= 0.025;
          if (sw.opacity <= 0 || sw.radius >= sw.maxRadius) {
            this.globeGroup.remove(sw.mesh);
            sw.mesh.geometry.dispose();
            sw.material.dispose();
            this.shockwaves.splice(i, 1);
          } else {
            sw.material.opacity = sw.opacity;
            const s = sw.radius / 0.02;
            sw.mesh.scale.set(s, s, 1.0);
          }
        }

        // 4. Contagion spline particle streams
        this.splines.forEach((s) => {
          const positions = s.particlePoints.geometry.attributes.position.array;
          for (let i = 0; i < s.particleCount; i++) {
            s.offsets[i] = (s.offsets[i] + s.speed) % 1.0;
            const pt = s.curve.getPointAt(s.offsets[i]);
            positions[i * 3] = pt.x;
            positions[i * 3 + 1] = pt.y;
            positions[i * 3 + 2] = pt.z;
          }
          s.particlePoints.geometry.attributes.position.needsUpdate = true;
        });

        // 5. Smooth Camera fly-to interpolation
        if (this.targetCameraPos && this.camera) {
          this.camera.position.x += (this.targetCameraPos.x - this.camera.position.x) * 0.05;
          this.camera.position.y += (this.targetCameraPos.y - this.camera.position.y) * 0.05;
          this.camera.position.z += (this.targetCameraPos.z - this.camera.position.z) * 0.05;

          if (this.targetLookAt) {
            this.currentLookAt.x += (this.targetLookAt.x - this.currentLookAt.x) * 0.05;
            this.currentLookAt.y += (this.targetLookAt.y - this.currentLookAt.y) * 0.05;
            this.currentLookAt.z += (this.targetLookAt.z - this.currentLookAt.z) * 0.05;
            this.camera.lookAt(this.currentLookAt.x, this.currentLookAt.y, this.currentLookAt.z);
          }

          const dist = this.camera.position.distanceTo(new this.THREE.Vector3(this.targetCameraPos.x, this.targetCameraPos.y, this.targetCameraPos.z));
          if (dist < 0.02) {
            this.targetCameraPos = null;
          }
        }

        // 6. Render
        if (this.renderer && this.scene && this.camera) {
          this.renderer.render(this.scene, this.camera);
        }
      };

      this.animFrameId = requestAnimationFrame(render);
    }

    _onWindowResize() {
      if (!this.container || !this.camera || !this.renderer) return;
      const width = this.container.clientWidth || 800;
      const height = this.container.clientHeight || 600;
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    }

    // ------------------------------------------------------------------------
    // WebGL Resource Disposal & Cleanup
    // ------------------------------------------------------------------------

    destroy() {
      this.isDisposed = true;
      if (this.animFrameId) {
        cancelAnimationFrame(this.animFrameId);
        this.animFrameId = null;
      }

      window.removeEventListener('jarvis:macro:shockwave', this._boundShockwaveHandler);

      // Clean up Three.js meshes
      if (this.scene) {
        this.scene.traverse((obj) => {
          if (obj.geometry) obj.geometry.dispose();
          if (obj.material) {
            if (Array.isArray(obj.material)) {
              obj.material.forEach(m => m.dispose());
            } else {
              obj.material.dispose();
            }
          }
        });
      }

      if (this.renderer) {
        this.renderer.dispose();
        if (this.renderer.domElement && this.renderer.domElement.parentNode) {
          this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
        }
      }

      if (this.hudOverlay && this.hudOverlay.parentNode) {
        this.hudOverlay.parentNode.removeChild(this.hudOverlay);
      }
    }
  }

  return MacroContagionSphere3D;
});
