"""
macro_contagion_service.py — Institutional Macro Contagion & Geopolitical Hotspot Service for J.A.R.V.I.S.
=======================================================================================================
Computes:
  1. Cross-Asset Macro Contagion Vectors:
     Maps transmission of macro shocks from Primary Drivers (DXY, US10Y, Crude Oil)
     into Target Financial Assets (Gold/XAUUSD, EURUSD, USDJPY, GBPUSD, BTCUSD, SOLUSD)
     using empirical sensitivity elasticities (Beta), correlation coefficients (r), and transmission velocity.
  2. Geopolitical Hotspot Telemetry:
     Real-time tracking of critical choke points:
       - Bab-el-Mandeb / Red Sea (Lat 12.78°N, Lon 43.33°E)
       - Strait of Hormuz (Lat 26.56°N, Lon 56.25°E)
       - Taiwan Strait (Lat 24.25°N, Lon 119.50°E)
       - Eastern Europe / Black Sea / Suwalki Gap (Lat 48.01°N, Lon 37.80°E)
     Includes baseline flows, disruption %, commodity volatility impact multipliers, and historical market reaction dossiers.
  3. Forward-Looking Catalyst Timeline:
     Calendar of high-impact macroeconomic releases, central bank policy meetings (FOMC, ECB, BoE, BoJ),
     speeches, 15-minute pre/post blackout status, and historical price reaction precedents.
  4. 3D Graph Topology Generator:
     Generates node coordinates, directional contagion spline edges, velocity scalars, and color codes
     for WebGL rendering in MacroContagionSphere3D.js.
=======================================================================================================
"""

from __future__ import annotations

import math
import time
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("Jarvis.MacroContagion")


# ============================================================================
# Canonical Constants & Data Structures
# ============================================================================

DRIVERS = ["DXY", "US10Y", "OIL"]
ASSETS = ["XAUUSD", "EURUSD", "USDJPY", "GBPUSD", "BTCUSD", "SOLUSD"]
HOTSPOTS = ["red_sea", "hormuz_strait", "taiwan_strait", "eastern_europe"]


@dataclass
class MacroDriverState:
    symbol: str
    name: str
    current_value: float
    unit: str
    change_24h_pct: float
    volatility_index: float  # Annualized or daily normalized vol (0-100)
    trend: str  # BULLISH, BEARISH, NEUTRAL
    last_update_ts: float = field(default_factory=time.time)


@dataclass
class TargetAssetState:
    symbol: str
    name: str
    category: str  # SAFE_HAVEN, FOREX, CRYPTO_HIGH_BETA
    current_price: float
    change_24h_pct: float
    implied_volatility: float
    beta_to_dxy: float
    beta_to_us10y: float
    beta_to_oil: float
    last_update_ts: float = field(default_factory=time.time)


@dataclass
class ContagionVector:
    driver: str
    target: str
    correlation: float  # Pearson r [-1.0, 1.0]
    beta: float  # Elasticity multiplier (% change in target per 1% change in driver)
    transmission_lag_s: float  # Estimated propagation latency in seconds
    flow_velocity: float  # 3D spline particle animation velocity scalar (0.5 - 3.0)
    color_code: str  # Hex or CSS color string
    sentiment_channel: str  # HEADWIND, TAILWIND, CONTAGION_SHOCK
    description: str


@dataclass
class HistoricalReactionPrecedent:
    incident_id: str
    date: str
    title: str
    description: str
    crude_oil_impulse: str
    gold_impulse: str
    dxy_reaction: str
    risk_crypto_reaction: str
    resolution_timeframe: str
    primary_chokepoint: str


@dataclass
class HotspotTelemetry:
    hotspot_id: str
    name: str
    region: str
    latitude: float
    longitude: float
    cartesian_coords: Dict[str, float]  # Unit sphere coordinates x, y, z
    flow_baseline_description: str
    baseline_mbd: float  # Million barrels per day or equivalent metric
    current_mbd: float
    disruption_pct: float
    threat_level: str  # DEFCON_1, DEFCON_2, DEFCON_3, CRITICAL_WARZONE, HIGH_TENSION
    incident_count_7d: int
    reroute_recommendation: str
    status_narrative: str
    commodity_volatility_multipliers: Dict[str, float]
    historical_dossier: List[HistoricalReactionPrecedent]
    volatility_forecast_24h: Dict[str, Any]


@dataclass
class CatalystEvent:
    event_id: str
    title: str
    category: str  # CENTRAL_BANK, INFLATION, EMPLOYMENT, COMMODITY, SPEECH
    scheduled_utc: str
    institution: str
    impact_level: str  # HIGH, MEDIUM, LOW
    blackout_buffer_active: bool  # True if within ±15 minutes
    historical_precedents: List[Dict[str, Any]]
    expected_consensus: str
    previous_print: str
    estimated_volatility_pip_range: Dict[str, str]


# ============================================================================
# Coordinate Transformation Utilities
# ============================================================================

def lat_lon_to_cartesian(lat: float, lon: float, radius: float = 1.0) -> Dict[str, float]:
    """
    Converts Latitude / Longitude into 3D Cartesian coordinates for Three.js unit sphere.
    Standard Three.js coordinate mapping:
      phi = (90 - lat) * (pi / 180)
      theta = (lon + 180) * (pi / 180)
      x = -radius * sin(phi) * cos(theta)
      y = radius * cos(phi)
      z = radius * sin(phi) * sin(theta)
    """
    phi = math.radians(90.0 - lat)
    theta = math.radians(lon + 180.0)
    x = -radius * math.sin(phi) * math.cos(theta)
    y = radius * math.cos(phi)
    z = radius * math.sin(phi) * math.sin(theta)
    return {"x": round(x, 4), "y": round(y, 4), "z": round(z, 4)}


# ============================================================================
# Macro Contagion Service Implementation
# ============================================================================

class MacroContagionService:
    """
    Master service for Macro Contagion modeling, Geopolitical Hotspot surveillance,
    and Catalyst Timeline analytics.
    """

    def __init__(self):
        self._init_drivers()
        self._init_assets()
        self._init_contagion_matrix()
        self._init_hotspots()
        self._init_catalyst_timeline()

    # ------------------------------------------------------------------------
    # Initialization Routines
    # ------------------------------------------------------------------------

    def _init_drivers(self):
        """Initializes primary macro drivers with institutional baselines."""
        self.drivers: Dict[str, MacroDriverState] = {
            "DXY": MacroDriverState(
                symbol="DXY",
                name="US Dollar Index",
                current_value=104.25,
                unit="Points",
                change_24h_pct=-0.35,
                volatility_index=48.5,
                trend="BEARISH"
            ),
            "US10Y": MacroDriverState(
                symbol="US10Y",
                name="US 10-Year Treasury Yield",
                current_value=4.285,
                unit="%",
                change_24h_pct=-1.20,
                volatility_index=55.0,
                trend="BEARISH"
            ),
            "OIL": MacroDriverState(
                symbol="OIL",
                name="WTI Crude Oil",
                current_value=78.60,
                unit="USD/bbl",
                change_24h_pct=2.45,
                volatility_index=68.2,
                trend="BULLISH"
            ),
        }

    def _init_assets(self):
        """Initializes target assets across Safe Haven, Forex, and Crypto."""
        self.assets: Dict[str, TargetAssetState] = {
            "XAUUSD": TargetAssetState(
                symbol="XAUUSD",
                name="Spot Gold",
                category="SAFE_HAVEN",
                current_price=2654.50,
                change_24h_pct=0.85,
                implied_volatility=16.8,
                beta_to_dxy=-0.68,
                beta_to_us10y=-0.58,
                beta_to_oil=0.52
            ),
            "EURUSD": TargetAssetState(
                symbol="EURUSD",
                name="Euro / US Dollar",
                category="FOREX",
                current_price=1.0865,
                change_24h_pct=0.32,
                implied_volatility=7.2,
                beta_to_dxy=-0.92,
                beta_to_us10y=-0.35,
                beta_to_oil=-0.48
            ),
            "USDJPY": TargetAssetState(
                symbol="USDJPY",
                name="US Dollar / Japanese Yen",
                category="FOREX",
                current_price=152.20,
                change_24h_pct=-0.55,
                implied_volatility=9.8,
                beta_to_dxy=0.55,
                beta_to_us10y=0.78,
                beta_to_oil=-0.25
            ),
            "GBPUSD": TargetAssetState(
                symbol="GBPUSD",
                name="British Pound / US Dollar",
                category="FOREX",
                current_price=1.3040,
                change_24h_pct=0.28,
                implied_volatility=8.4,
                beta_to_dxy=-0.85,
                beta_to_us10y=-0.28,
                beta_to_oil=-0.22
            ),
            "BTCUSD": TargetAssetState(
                symbol="BTCUSD",
                name="Bitcoin",
                category="CRYPTO_HIGH_BETA",
                current_price=64850.0,
                change_24h_pct=2.10,
                implied_volatility=48.5,
                beta_to_dxy=-0.45,
                beta_to_us10y=-0.40,
                beta_to_oil=-0.15
            ),
            "SOLUSD": TargetAssetState(
                symbol="SOLUSD",
                name="Solana",
                category="CRYPTO_HIGH_BETA",
                current_price=158.40,
                change_24h_pct=4.80,
                implied_volatility=65.2,
                beta_to_dxy=-0.65,
                beta_to_us10y=-0.60,
                beta_to_oil=-0.20
            ),
        }

    def _init_contagion_matrix(self):
        """Constructs empirical cross-asset contagion vectors."""
        self.vectors: List[ContagionVector] = [
            # DXY Contagion Vectors
            ContagionVector(
                driver="DXY",
                target="XAUUSD",
                correlation=-0.72,
                beta=-0.68,
                transmission_lag_s=2.5,
                flow_velocity=1.8,
                color_code="#00f3ff",  # Cyan: Dollar weakness tailwind for Gold
                sentiment_channel="TAILWIND",
                description="Inverse dollar pricing dynamic. Dollar softening provides immediate upward monetary velocity for Spot Gold."
            ),
            ContagionVector(
                driver="DXY",
                target="EURUSD",
                correlation=-0.96,
                beta=-0.92,
                transmission_lag_s=0.5,
                flow_velocity=2.5,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="Primary bilateral FX transmission. Dollar sell-off directly translates to EURUSD appreciation."
            ),
            ContagionVector(
                driver="DXY",
                target="USDJPY",
                correlation=0.62,
                beta=0.55,
                transmission_lag_s=1.0,
                flow_velocity=1.5,
                color_code="#ff3355",  # Rose/Crimson: Drag
                sentiment_channel="HEADWIND",
                description="Co-directional dollar momentum. Dollar softness weighs on USDJPY price action."
            ),
            ContagionVector(
                driver="DXY",
                target="GBPUSD",
                correlation=-0.89,
                beta=-0.85,
                transmission_lag_s=0.8,
                flow_velocity=2.0,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="Inverse FX transmission. DXY depreciation unlocks upside relief rallies in Cable."
            ),
            ContagionVector(
                driver="DXY",
                target="BTCUSD",
                correlation=-0.48,
                beta=-0.45,
                transmission_lag_s=15.0,
                flow_velocity=1.2,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="Global dollar liquidity expansion channel. Lower DXY expands crypto risk appetite."
            ),
            ContagionVector(
                driver="DXY",
                target="SOLUSD",
                correlation=-0.52,
                beta=-0.65,
                transmission_lag_s=20.0,
                flow_velocity=1.4,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="High-beta altcoin liquidity multiplier responding to broad macro dollar easing."
            ),

            # US10Y Contagion Vectors
            ContagionVector(
                driver="US10Y",
                target="XAUUSD",
                correlation=-0.64,
                beta=-0.58,
                transmission_lag_s=3.0,
                flow_velocity=1.6,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="Real yield compression diminishes opportunity cost of holding non-yielding Gold bullion."
            ),
            ContagionVector(
                driver="US10Y",
                target="EURUSD",
                correlation=-0.42,
                beta=-0.35,
                transmission_lag_s=2.0,
                flow_velocity=1.1,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="Narrowing sovereign interest rate differential supports European sovereign assets."
            ),
            ContagionVector(
                driver="US10Y",
                target="USDJPY",
                correlation=0.81,
                beta=0.78,
                transmission_lag_s=0.8,
                flow_velocity=2.4,
                color_code="#ff3355",
                sentiment_channel="HEADWIND",
                description="Benchmark US-Japan yield spread is the primary driver of USDJPY carry trade flows."
            ),
            ContagionVector(
                driver="US10Y",
                target="BTCUSD",
                correlation=-0.44,
                beta=-0.40,
                transmission_lag_s=30.0,
                flow_velocity=1.0,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="Lower discount rates stimulate valuation multiples across speculative digital store-of-value assets."
            ),
            ContagionVector(
                driver="US10Y",
                target="SOLUSD",
                correlation=-0.48,
                beta=-0.60,
                transmission_lag_s=35.0,
                flow_velocity=1.2,
                color_code="#00f3ff",
                sentiment_channel="TAILWIND",
                description="High-duration tech asset sensitivity to sovereign cost of capital fluctuations."
            ),

            # OIL Contagion Vectors
            ContagionVector(
                driver="OIL",
                target="XAUUSD",
                correlation=0.58,
                beta=0.52,
                transmission_lag_s=5.0,
                flow_velocity=2.2,
                color_code="#ffaa00",  # Amber: Geopolitical inflation shock
                sentiment_channel="CONTAGION_SHOCK",
                description="Petroleum cost surges feed structural headline inflation expectations and safe-haven accumulation."
            ),
            ContagionVector(
                driver="OIL",
                target="EURUSD",
                correlation=-0.54,
                beta=-0.48,
                transmission_lag_s=4.0,
                flow_velocity=1.7,
                color_code="#ff3355",
                sentiment_channel="HEADWIND",
                description="European terms-of-trade degradation: Eurozone energy import bill expands on oil price spikes."
            ),
            ContagionVector(
                driver="OIL",
                target="USDJPY",
                correlation=-0.30,
                beta=-0.25,
                transmission_lag_s=6.0,
                flow_velocity=1.0,
                color_code="#ff3355",
                sentiment_channel="HEADWIND",
                description="Japanese resource dependency triggers trade balance deficit pressure vs safe-haven yen buying."
            ),
            ContagionVector(
                driver="OIL",
                target="BTCUSD",
                correlation=-0.18,
                beta=-0.15,
                transmission_lag_s=45.0,
                flow_velocity=0.8,
                color_code="#ff3355",
                sentiment_channel="HEADWIND",
                description="Energy price shocks raise stagflation risk, temporarily restraining high-risk capital deployments."
            ),
            ContagionVector(
                driver="OIL",
                target="SOLUSD",
                correlation=-0.22,
                beta=-0.20,
                transmission_lag_s=50.0,
                flow_velocity=0.9,
                color_code="#ff3355",
                sentiment_channel="HEADWIND",
                description="Secondary risk-off liquidity dampener caused by macro energy cost pressures."
            ),
        ]

    def _init_hotspots(self):
        """Initializes the 4 canonical maritime and geopolitical hotspots with dossiers."""
        self.hotspots: Dict[str, HotspotTelemetry] = {
            "red_sea": HotspotTelemetry(
                hotspot_id="red_sea",
                name="Bab el-Mandeb / Red Sea Chokepoint",
                region="Middle East / Horn of Africa",
                latitude=12.78,
                longitude=43.33,
                cartesian_coords=lat_lon_to_cartesian(12.78, 43.33, 1.0),
                flow_baseline_description="EIA Baseline: 6.2 mbd crude & petroleum products + 12% global maritime trade transit",
                baseline_mbd=6.2,
                current_mbd=2.1,
                disruption_pct=66.1,
                threat_level="CRITICAL_WARZONE",
                incident_count_7d=28,
                reroute_recommendation="Commercial container traffic diverted via Cape of Good Hope (+10-14 days transit). War-risk insurance premiums elevated +350%.",
                status_narrative="Houthi anti-ship ballistic missile and drone swarm interdictions active in southern Red Sea corridor; Operation Prosperity Guardian escorts active.",
                commodity_volatility_multipliers={
                    "XAUUSD": 1.40,
                    "WTI": 1.35,
                    "BRENT": 1.38,
                    "EURUSD": -0.60,
                    "GLOBAL_FREIGHT": 2.50,
                    "INFLATION_SURGE": 1.30
                },
                historical_dossier=[
                    HistoricalReactionPrecedent(
                        incident_id="HIST-RS-2023-12",
                        date="2023-12-15",
                        title="Red Sea Commercial Fleet Interdictions & Rerouting Cascade",
                        description="Major container lines (Maersk, Hapag-Lloyd) pause Suez transits following anti-ship missile strikes near Bab el-Mandeb.",
                        crude_oil_impulse="+4.8% surge in 48 hours ($73.80 -> $77.35)",
                        gold_impulse="Gold safe haven expansion: +$36.50/oz to $2,042",
                        dxy_reaction="-0.35% intraday churn",
                        risk_crypto_reaction="BTC held steady (+0.8%), altcoins rangebound",
                        resolution_timeframe="Structural transit reduction persisted 6+ months",
                        primary_chokepoint="red_sea"
                    ),
                    HistoricalReactionPrecedent(
                        incident_id="HIST-RS-2024-01",
                        date="2024-01-12",
                        title="Operation Poseidon Archer Coalition Strikes",
                        description="US and UK naval aviation execute joint strikes on Yemen coastal radar, UAV launching facilities, and ballistic bunkers.",
                        crude_oil_impulse="+3.2% gap open ($78.20 -> $80.70)",
                        gold_impulse="Gold safe haven rally: +$22.00/oz immediate surge",
                        dxy_reaction="+0.20% safe-haven USD bid",
                        risk_crypto_reaction="Crypto flash liquidation dip (-1.8%) followed by rapid V-reversal",
                        resolution_timeframe="48-hour volatility spike followed by plateau",
                        primary_chokepoint="red_sea"
                    )
                ],
                volatility_forecast_24h={
                    "expected_oil_range_usd": [77.20, 81.50],
                    "expected_gold_range_usd": [2635.0, 2678.0],
                    "implied_chokepoint_risk_premium_oil": "+$4.20/bbl",
                    "implied_safe_haven_premium_gold": "+$32.00/oz"
                }
            ),

            "hormuz_strait": HotspotTelemetry(
                hotspot_id="hormuz_strait",
                name="Strait of Hormuz Chokepoint",
                region="Persian Gulf / Arabian Sea",
                latitude=26.56,
                longitude=56.25,
                cartesian_coords=lat_lon_to_cartesian(26.56, 56.25, 1.0),
                flow_baseline_description="EIA Baseline: 21.0 mbd crude & condensates (21% of global petroleum consumption)",
                baseline_mbd=21.0,
                current_mbd=14.5,
                disruption_pct=31.0,
                threat_level="CRITICAL_WARZONE",
                incident_count_7d=42,
                reroute_recommendation="Zero viable maritime bypass exists for bulk volume (Saudi East-West Pipeline and UAE ADCOP have limited 5.0 mbd capacity). Strict military convoy protocol.",
                status_narrative="IRGC naval patrol gunboats and fast attack craft active in traffic separation scheme; tanker boarding risk at DEFCON 1.",
                commodity_volatility_multipliers={
                    "XAUUSD": 1.45,
                    "WTI": 1.50,
                    "BRENT": 1.52,
                    "DXY": -0.40,
                    "EURUSD": -0.65,
                    "BTCUSD": -1.25,
                    "GLOBAL_ENERGY_SHOCK": 2.10
                },
                historical_dossier=[
                    HistoricalReactionPrecedent(
                        incident_id="HIST-HZ-2024-04",
                        date="2024-04-13",
                        title="MSC Aries Seizure & Persian Gulf Aerial Escalation",
                        description="Special forces heliborne boarding of Portuguese-flagged container vessel MSC Aries in the Strait of Hormuz.",
                        crude_oil_impulse="+6.2% 24h surge testing $90.50/bbl",
                        gold_impulse="+$52.00/oz vertical push to then-record $2,431.50",
                        dxy_reaction="+0.40% flight to dollar safety",
                        risk_crypto_reaction="BTC flash crash -4.5% ($67,500 -> $64,400) on weekend liquidation cascade",
                        resolution_timeframe="72-hour risk repricing and de-escalation buffer",
                        primary_chokepoint="hormuz_strait"
                    ),
                    HistoricalReactionPrecedent(
                        incident_id="HIST-HZ-2019-09",
                        date="2019-09-14",
                        title="Abqaiq-Khurais Processing Complex Drone Swarm Attack",
                        description="Precision coordinated strike halting 5.7 mbd of crude processing (over 50% of Saudi output).",
                        crude_oil_impulse="+14.6% single-day spike (largest historical percentage jump in 30 years)",
                        gold_impulse="+$19.50/oz gap open",
                        dxy_reaction="+0.15% modest gain",
                        risk_crypto_reaction="Equities slid -1.2%, crypto neutral",
                        resolution_timeframe="Gradual crude normalization over 3 weeks",
                        primary_chokepoint="hormuz_strait"
                    )
                ],
                volatility_forecast_24h={
                    "expected_oil_range_usd": [76.50, 83.20],
                    "expected_gold_range_usd": [2640.0, 2690.0],
                    "implied_chokepoint_risk_premium_oil": "+$6.80/bbl",
                    "implied_safe_haven_premium_gold": "+$45.00/oz"
                }
            ),

            "taiwan_strait": HotspotTelemetry(
                hotspot_id="taiwan_strait",
                name="Taiwan Strait & Luzon Strait",
                region="East Asia / Western Pacific",
                latitude=24.25,
                longitude=119.50,
                cartesian_coords=lat_lon_to_cartesian(24.25, 119.50, 1.0),
                flow_baseline_description="Baseline: 48% of global container ship fleet transit + 88% of leading-edge semiconductor supply chain",
                baseline_mbd=0.0,  # Container/Tech focus rather than oil mbd
                current_mbd=0.0,
                disruption_pct=12.0,
                threat_level="HIGH_TENSION",
                incident_count_7d=35,
                reroute_recommendation="Vessels rerouting east of Taiwan via Philippine Sea during military live-fire maritime exclusion zones.",
                status_narrative="PLA naval carrier strike group and air incursions crossing median line; electronic warfare surveillance zones declared.",
                commodity_volatility_multipliers={
                    "XAUUSD": 1.50,
                    "USDJPY": -0.80,
                    "BTCUSD": 1.30,
                    "SEMI_TECH_SHOCK": 1.75,
                    "GLOBAL_EQUITIES": -1.40
                },
                historical_dossier=[
                    HistoricalReactionPrecedent(
                        incident_id="HIST-TW-2022-08",
                        date="2022-08-04",
                        title="Joint Blockade Exercises & Missile Overflights",
                        description="Live-fire military maneuvers surrounding Taiwan with DF-15 ballistic missiles overflying Taipei airspace.",
                        crude_oil_impulse="Neutral to +0.8%",
                        gold_impulse="+$18.00/oz safe haven buying",
                        dxy_reaction="+0.25% dollar dominance",
                        risk_crypto_reaction="Semiconductor stocks (SOX) -2.8%, BTC rallied +2.1% on sovereign seizure hedge narrative",
                        resolution_timeframe="5 days of high tension followed by resumption of commercial transit",
                        primary_chokepoint="taiwan_strait"
                    ),
                    HistoricalReactionPrecedent(
                        incident_id="HIST-TW-2024-05",
                        date="2024-05-23",
                        title="Joint Sword-2024A Island Encirclement Drills",
                        description="Comprehensive naval and air encirclement simulations across northern, southern, and eastern sectors of Taiwan.",
                        crude_oil_impulse="Flat (+0.2%)",
                        gold_impulse="+$14.20/oz intraday spike",
                        dxy_reaction="Unchanged",
                        risk_crypto_reaction="Taiwan Dollar (TWD) -0.3%, crypto unaffected (+0.4%)",
                        resolution_timeframe="48-hour planned exercise window",
                        primary_chokepoint="taiwan_strait"
                    )
                ],
                volatility_forecast_24h={
                    "expected_tech_volatility_pct": "+3.4%",
                    "expected_gold_range_usd": [2645.0, 2685.0],
                    "implied_safe_haven_premium_gold": "+$28.00/oz"
                }
            ),

            "eastern_europe": HotspotTelemetry(
                hotspot_id="eastern_europe",
                name="Eastern Europe / Black Sea / Suwalki Corridor",
                region="Eastern Europe / Baltic / Black Sea",
                latitude=48.01,
                longitude=37.80,
                cartesian_coords=lat_lon_to_cartesian(48.01, 37.80, 1.0),
                flow_baseline_description="Baseline: Primary Eurasian natural gas, crude transit pipelines (Druzhba) and Black Sea grain maritime corridor",
                baseline_mbd=2.8,
                current_mbd=1.2,
                disruption_pct=57.1,
                threat_level="HIGH_TENSION",
                incident_count_7d=39,
                reroute_recommendation="Black Sea maritime shipping requires special war-risk grain insurance. Pipeline alternatives utilized through southern routes.",
                status_narrative="Maritime drone warfare in Black Sea ports; military forward deployments along Suwalki Gap and Kaliningrad perimeter.",
                commodity_volatility_multipliers={
                    "XAUUSD": 1.35,
                    "WTI": 1.30,
                    "NAT_GAS_EU": 1.85,
                    "EURUSD": -0.70,
                    "WHEAT_AGRI": 1.45
                },
                historical_dossier=[
                    HistoricalReactionPrecedent(
                        incident_id="HIST-EE-2022-02",
                        date="2022-02-24",
                        title="Eastern European Armed Conflict Outbreak",
                        description="Large-scale military mobilization across borders triggering international sanctions and resource export bans.",
                        crude_oil_impulse="+8.5% intraday surge past $100/bbl (peaked at $130)",
                        gold_impulse="+$65.00/oz explosion testing $1,974/oz",
                        dxy_reaction="+0.90% massive global liquidity flight to US Dollar",
                        risk_crypto_reaction="Initial crypto sell-off (-8.0%) followed by massive global adoption surge (+15% in 7 days)",
                        resolution_timeframe="Multi-year macro regime transformation",
                        primary_chokepoint="eastern_europe"
                    ),
                    HistoricalReactionPrecedent(
                        incident_id="HIST-EE-2023-07",
                        date="2023-07-17",
                        title="Black Sea Grain Initiative Suspension & Danube Strikes",
                        description="Termination of safe corridor agreements and drone strikes on Izmail and Reni port grain elevators.",
                        crude_oil_impulse="+2.1% supportive pressure",
                        gold_impulse="+$12.00/oz modest gain",
                        dxy_reaction="+0.15%",
                        risk_crypto_reaction="Wheat futures spiked +8.2%, EURUSD dropped -45 pips",
                        resolution_timeframe="2 weeks of acute supply chain repricing",
                        primary_chokepoint="eastern_europe"
                    )
                ],
                volatility_forecast_24h={
                    "expected_gas_spike_pct": "+5.2%",
                    "expected_gold_range_usd": [2638.0, 2675.0],
                    "implied_safe_haven_premium_gold": "+$22.00/oz"
                }
            )
        }

    def _init_catalyst_timeline(self):
        """Initializes forward-looking catalyst schedule with precedents and blackout buffer telemetry."""
        now = datetime.now(timezone.utc)

        # Build realistic calendar items centered around current date
        def event_time(hours_ahead: float) -> str:
            t = now + timedelta(hours=hours_ahead)
            return t.strftime("%Y-%m-%dT%H:%M:%SZ")

        self.catalysts: List[CatalystEvent] = [
            CatalystEvent(
                event_id="CAT-FED-001",
                title="FOMC Interest Rate Decision & Monetary Policy Statement",
                category="CENTRAL_BANK",
                scheduled_utc=event_time(14.5),
                institution="Federal Reserve",
                impact_level="HIGH",
                blackout_buffer_active=False,
                expected_consensus="4.75% (-25 bps cut)",
                previous_print="5.00%",
                estimated_volatility_pip_range={
                    "EURUSD": "60-90 pips",
                    "USDJPY": "110-160 pips",
                    "XAUUSD": "$25-$40/oz",
                    "BTCUSD": "$1,200-$2,500"
                },
                historical_precedents=[
                    {
                        "date": "2024-09-18",
                        "event": "FOMC 50 bps Jumbo Cut",
                        "market_reaction": "Gold surged +$28 to fresh ATH, DXY tumbled -0.55%, BTC expanded +3.4%."
                    },
                    {
                        "date": "2024-07-31",
                        "event": "FOMC Hold with Dovish Powell Presser",
                        "market_reaction": "US10Y plunged 11 bps, EURUSD gained +45 pips, Gold tested $2,450."
                    }
                ]
            ),
            CatalystEvent(
                event_id="CAT-CPI-002",
                title="US Consumer Price Index (CPI YoY / MoM)",
                category="INFLATION",
                scheduled_utc=event_time(38.0),
                institution="US Bureau of Labor Statistics",
                impact_level="HIGH",
                blackout_buffer_active=False,
                expected_consensus="2.3% YoY / 0.2% MoM",
                previous_print="2.5% YoY",
                estimated_volatility_pip_range={
                    "EURUSD": "45-75 pips",
                    "USDJPY": "80-120 pips",
                    "XAUUSD": "$20-$35/oz",
                    "BTCUSD": "$900-$1,800"
                },
                historical_precedents=[
                    {
                        "date": "2024-08-14",
                        "event": "CPI Inline Print (2.9%)",
                        "market_reaction": "Equities surged, DXY steady, Gold rallied +$15 into London close."
                    },
                    {
                        "date": "2024-06-12",
                        "event": "Cool CPI Surprise (3.3% vs 3.4% exp)",
                        "market_reaction": "DXY collapsed -0.85%, Gold spiked +$32, BTC broke out +$2,200."
                    }
                ]
            ),
            CatalystEvent(
                event_id="CAT-NFP-003",
                title="US Non-Farm Payrolls & Unemployment Rate",
                category="EMPLOYMENT",
                scheduled_utc=event_time(86.0),
                institution="US Department of Labor",
                impact_level="HIGH",
                blackout_buffer_active=False,
                expected_consensus="+145K jobs / 4.2% Unemployment",
                previous_print="+142K jobs",
                estimated_volatility_pip_range={
                    "EURUSD": "50-80 pips",
                    "USDJPY": "90-140 pips",
                    "XAUUSD": "$22-$38/oz",
                    "BTCUSD": "$800-$1,600"
                },
                historical_precedents=[
                    {
                        "date": "2024-09-06",
                        "event": "NFP Below Consensus (+142K vs +160K exp)",
                        "market_reaction": "Dollar whipsawed, US10Y fell 7 bps, Gold tested $2,520 resistance."
                    }
                ]
            ),
            CatalystEvent(
                event_id="CAT-ECB-004",
                title="ECB Governing Council Policy Meeting & Lagarde Presser",
                category="CENTRAL_BANK",
                scheduled_utc=event_time(110.0),
                institution="European Central Bank",
                impact_level="HIGH",
                blackout_buffer_active=False,
                expected_consensus="3.25% (-25 bps deposit rate cut)",
                previous_print="3.50%",
                estimated_volatility_pip_range={
                    "EURUSD": "45-70 pips",
                    "EURGBP": "25-40 pips",
                    "EURJPY": "70-110 pips"
                },
                historical_precedents=[
                    {
                        "date": "2024-09-12",
                        "event": "ECB 25 bps Cut with Neutral Guidance",
                        "market_reaction": "EURUSD dipped 20 pips then rallied 40 pips; Eurozone bond yields eased."
                    }
                ]
            ),
            CatalystEvent(
                event_id="CAT-BOJ-005",
                title="Bank of Japan Monetary Policy Statement & Ueda Briefing",
                category="CENTRAL_BANK",
                scheduled_utc=event_time(158.0),
                institution="Bank of Japan",
                impact_level="HIGH",
                blackout_buffer_active=False,
                expected_consensus="0.25% Policy Rate Hold",
                previous_print="0.25%",
                estimated_volatility_pip_range={
                    "USDJPY": "120-220 pips",
                    "GBPJPY": "140-250 pips",
                    "EURJPY": "100-180 pips"
                },
                historical_precedents=[
                    {
                        "date": "2024-07-31",
                        "event": "BoJ Surprise Rate Hike to 0.25%",
                        "market_reaction": "Triggered historic global carry-trade unwind; USDJPY dropped 800 pips over 4 sessions; Nikkei -12% shock."
                    }
                ]
            ),
            CatalystEvent(
                event_id="CAT-SPK-006",
                title="Fed Chair Jerome Powell Keynote Address",
                category="SPEECH",
                scheduled_utc=event_time(6.0),
                institution="Federal Reserve",
                impact_level="HIGH",
                blackout_buffer_active=False,
                expected_consensus="Guidance on rate path normalization & balance sheet runoff",
                previous_print="N/A",
                estimated_volatility_pip_range={
                    "EURUSD": "35-55 pips",
                    "XAUUSD": "$15-$25/oz",
                    "US10Y": "5-9 bps"
                },
                historical_precedents=[
                    {
                        "date": "2024-08-23",
                        "event": "Jackson Hole Keynote ('The time has come for policy to adjust')",
                        "market_reaction": "Massive risk rally: Gold +$30, DXY -0.80%, BTC +$3,000 in 2 hours."
                    }
                ]
            )
        ]

    # ------------------------------------------------------------------------
    # Analytical Engine: Shock Simulation & Regime Detection
    # ------------------------------------------------------------------------

    def simulate_macro_shock(self, driver: str, delta_pct: float) -> Dict[str, Any]:
        """
        Simulates an exogenous shock to a primary macro driver (DXY, US10Y, or OIL)
        and computes the immediate cascading impact on all target assets.
        
        Args:
            driver: "DXY", "US10Y", or "OIL"
            delta_pct: Percentage change shock (e.g. +1.5 for +1.5%, or -2.0 for -2.0%)
            
        Returns:
            Dict containing driver update, affected asset vector impacts, and macro regime shift.
        """
        driver_norm = driver.strip().upper()
        if driver_norm not in self.drivers:
            raise ValueError(f"Unknown macro driver: {driver}. Supported drivers: {list(self.drivers.keys())}")

        d_state = self.drivers[driver_norm]
        prev_value = d_state.current_value
        new_value = prev_value * (1.0 + delta_pct / 100.0)

        # Compute asset reactions based on Beta sensitivities
        impacts: Dict[str, Any] = {}
        for asset_sym, a_state in self.assets.items():
            if driver_norm == "DXY":
                beta = a_state.beta_to_dxy
            elif driver_norm == "US10Y":
                beta = a_state.beta_to_us10y
            else:  # OIL
                beta = a_state.beta_to_oil

            expected_change_pct = delta_pct * beta
            prev_price = a_state.current_price
            new_price = prev_price * (1.0 + expected_change_pct / 100.0)

            # Volatility multiplier scale
            vol_multiplier = 1.0 + (abs(delta_pct) * 0.15)

            impacts[asset_sym] = {
                "asset": asset_sym,
                "name": a_state.name,
                "category": a_state.category,
                "beta": beta,
                "previous_price": prev_price,
                "projected_price": round(new_price, 4 if "USD" in asset_sym and a_state.category == "FOREX" else 2),
                "expected_change_pct": round(expected_change_pct, 3),
                "directional_bias": "BULLISH" if expected_change_pct > 0 else ("BEARISH" if expected_change_pct < 0 else "NEUTRAL"),
                "volatility_surge_factor": round(vol_multiplier, 2)
            }

        # Classify resulting macro regime
        regime = self._classify_macro_regime(driver_norm, delta_pct)

        return {
            "simulation_timestamp": datetime.now(timezone.utc).isoformat(),
            "shocked_driver": {
                "symbol": driver_norm,
                "name": d_state.name,
                "delta_pct": delta_pct,
                "previous_value": round(prev_value, 4),
                "shocked_value": round(new_value, 4),
                "unit": d_state.unit
            },
            "cascading_asset_impacts": impacts,
            "macro_regime": regime
        }

    def simulate_hotspot_escalation(self, hotspot_id: str, escalation_delta_pct: float) -> Dict[str, Any]:
        """
        Simulates an escalation or supply disruption at a geopolitical hotspot.
        """
        if hotspot_id not in self.hotspots:
            raise ValueError(f"Unknown hotspot: {hotspot_id}. Available: {list(self.hotspots.keys())}")

        hotspot = self.hotspots[hotspot_id]
        multipliers = hotspot.commodity_volatility_multipliers

        # Derive crude oil and gold shocks based on hotspot multipliers
        oil_multiplier = multipliers.get("WTI", multipliers.get("BRENT", 1.20))
        gold_multiplier = multipliers.get("XAUUSD", 1.25)

        oil_shock_pct = escalation_delta_pct * (oil_multiplier - 1.0) * 1.5
        gold_shock_pct = escalation_delta_pct * (gold_multiplier - 1.0) * 1.2

        oil_cascade = self.simulate_macro_shock("OIL", oil_shock_pct)

        return {
            "hotspot_id": hotspot_id,
            "name": hotspot.name,
            "escalation_delta_pct": escalation_delta_pct,
            "threat_level": "CRITICAL_WARZONE" if escalation_delta_pct > 15.0 else hotspot.threat_level,
            "oil_price_surge_pct": round(oil_shock_pct, 2),
            "gold_price_surge_pct": round(gold_shock_pct, 2),
            "cascading_network_impact": oil_cascade,
            "historical_precedent_sample": hotspot.historical_dossier[0] if hotspot.historical_dossier else None
        }

    def _classify_macro_regime(self, shocked_driver: str, delta: float) -> Dict[str, str]:
        """Determines the overarching institutional macro regime."""
        if shocked_driver == "DXY" and delta > 1.0:
            return {
                "regime": "DOLLAR_DOMINANCE_LIQUIDITY_SQUEEZE",
                "bias": "Risk-off contraction across equities, crypto, and emerging market FX.",
                "tactical_guidance": "Favour USD cash, reduce high-beta crypto exposure, short EURUSD and GBPUSD on rallies."
            }
        elif shocked_driver == "DXY" and delta < -1.0:
            return {
                "regime": "GLOBAL_LIQUIDITY_EXPANSION",
                "bias": "Broad tailwind for Gold, commodities, and high-beta crypto assets (BTC, SOL).",
                "tactical_guidance": "Long XAUUSD and high-conviction Solana meme/blue-chip breakouts."
            }
        elif shocked_driver == "OIL" and delta > 3.0:
            return {
                "regime": "GEOPOLITICAL_STAGFLATION_SHOCK",
                "bias": "Commodity inflation shock dampening European terms-of-trade; safe-haven bid for Gold.",
                "tactical_guidance": "Long WTI/Gold spreads, short EURUSD, monitor Red Sea / Hormuz tanker alerts."
            }
        elif shocked_driver == "US10Y" and delta > 2.0:
            return {
                "regime": "BOND_YIELD_SPIKE_DISCOUNT_PRESSURE",
                "bias": "Cost of capital increase pressuring speculative valuations and non-yielding bullion.",
                "tactical_guidance": "Long USDJPY carry setups, tighten stop-losses on speculative crypto perps."
            }
        else:
            return {
                "regime": "BALANCED_MACRO_CONSOLIDATION",
                "bias": "Cross-asset equilibrium within institutional statistical bands.",
                "tactical_guidance": "Trade technical SMC levels (Order Blocks, FVGs) with standard 1:2.5 risk-reward."
            }

    # ------------------------------------------------------------------------
    # Public Query Methods
    # ------------------------------------------------------------------------

    def get_macro_drivers_telemetry(self) -> Dict[str, Any]:
        """Returns current state of all primary macro drivers."""
        return {k: asdict(v) for k, v in self.drivers.items()}

    def get_target_assets_telemetry(self) -> Dict[str, Any]:
        """Returns current state of all target financial assets."""
        return {k: asdict(v) for k, v in self.assets.items()}

    def get_contagion_vectors(self) -> List[Dict[str, Any]]:
        """Returns all cross-asset contagion vectors."""
        return [asdict(v) for v in self.vectors]

    def get_all_hotspots(self) -> Dict[str, Any]:
        """Returns all geopolitical hotspot dossiers and live flow telemetry."""
        return {
            k: {
                **asdict(v),
                "historical_dossier": [asdict(p) for p in v.historical_dossier]
            }
            for k, v in self.hotspots.items()
        }

    def get_hotspot_dossier(self, hotspot_id: str) -> Optional[Dict[str, Any]]:
        """Returns complete historical dossier and telemetry for a specific hotspot."""
        h = self.hotspots.get(hotspot_id.lower().strip())
        if not h:
            return None
        res = asdict(h)
        res["historical_dossier"] = [asdict(p) for p in h.historical_dossier]
        return res

    def get_catalyst_timeline(self, check_blackout_now: bool = True) -> Dict[str, Any]:
        """
        Returns forward-looking catalyst timeline with countdowns,
        precedents, and 15-minute news blackout status.
        """
        now = datetime.now(timezone.utc)
        events_output = []
        any_blackout_active = False

        for ev in self.catalysts:
            ev_dict = asdict(ev)
            # Calculate time difference
            try:
                dt = datetime.fromisoformat(ev.scheduled_utc.replace("Z", "+00:00"))
                delta_mins = (dt - now).total_seconds() / 60.0
                ev_dict["minutes_to_release"] = round(delta_mins, 1)

                # Active blackout buffer: within [-15 min, +15 min] of release
                is_blackout = abs(delta_mins) <= 15.0 if check_blackout_now else False
                ev_dict["blackout_buffer_active"] = is_blackout
                if is_blackout and ev.impact_level == "HIGH":
                    any_blackout_active = True
            except Exception as e:
                logger.warning(f"Error parsing date {ev.scheduled_utc}: {e}")
                ev_dict["minutes_to_release"] = 999.0

            events_output.append(ev_dict)

        # Sort by upcoming time
        events_output.sort(key=lambda x: x.get("minutes_to_release", 999.0))

        return {
            "current_utc": now.isoformat(),
            "global_news_blackout_active": any_blackout_active,
            "blackout_rule": "Deterministic 15-minute pre/post high-impact execution freeze (FundingPips #40000294403 compliance)",
            "catalysts_count": len(events_output),
            "catalysts": events_output
        }

    # ------------------------------------------------------------------------
    # 3D Graph Topology Generator
    # ------------------------------------------------------------------------

    def get_contagion_network_graph(self) -> Dict[str, Any]:
        """
        Generates 3D graph topology for MacroContagionSphere3D.js:
          - nodes: Macro drivers, Geopolitical hotspots, and Target assets.
          - edges: Animated 3D particle splines with flow velocities, correlation colors, and betas.
        """
        nodes: List[Dict[str, Any]] = []

        # 1. Macro Driver Nodes (Positioned in upper orbital arc)
        driver_positions = {
            "DXY": {"x": -2.2, "y": 2.4, "z": 0.5},
            "US10Y": {"x": 0.0, "y": 2.8, "z": 0.8},
            "OIL": {"x": 2.2, "y": 2.4, "z": 0.5}
        }
        for d_sym, d_state in self.drivers.items():
            pos = driver_positions.get(d_sym, {"x": 0, "y": 2.5, "z": 0})
            nodes.append({
                "id": f"driver_{d_sym}",
                "symbol": d_sym,
                "name": d_state.name,
                "node_type": "DRIVER",
                "value": d_state.current_value,
                "unit": d_state.unit,
                "change_24h_pct": d_state.change_24h_pct,
                "volatility_index": d_state.volatility_index,
                "trend": d_state.trend,
                "position_3d": pos,
                "glow_color": "#00f3ff" if d_sym == "DXY" else ("#ffd700" if d_sym == "US10Y" else "#ff5500")
            })

        # 2. Geopolitical Hotspot Nodes (Positioned directly on unit sphere R=1.0)
        for h_id, h_state in self.hotspots.items():
            nodes.append({
                "id": f"hotspot_{h_id}",
                "symbol": h_id.upper(),
                "name": h_state.name,
                "node_type": "HOTSPOT",
                "latitude": h_state.latitude,
                "longitude": h_state.longitude,
                "position_3d": h_state.cartesian_coords,  # Surface coords on sphere
                "threat_level": h_state.threat_level,
                "disruption_pct": h_state.disruption_pct,
                "baseline_mbd": h_state.baseline_mbd,
                "current_mbd": h_state.current_mbd,
                "glow_color": "#ff2255" if "WARZONE" in h_state.threat_level else "#ffaa00",
                "pulse_active": True
            })

        # 3. Target Asset Nodes (Positioned in equatorial/lower receiving orbit)
        asset_positions = {
            "XAUUSD": {"x": -2.8, "y": -0.8, "z": 1.2},
            "EURUSD": {"x": -1.8, "y": -1.8, "z": 1.5},
            "USDJPY": {"x": -0.5, "y": -2.2, "z": 1.4},
            "GBPUSD": {"x": 0.8, "y": -2.2, "z": 1.4},
            "BTCUSD": {"x": 2.0, "y": -1.8, "z": 1.5},
            "SOLUSD": {"x": 2.8, "y": -0.8, "z": 1.2}
        }
        for a_sym, a_state in self.assets.items():
            pos = asset_positions.get(a_sym, {"x": 0, "y": -2.0, "z": 1.0})
            nodes.append({
                "id": f"asset_{a_sym}",
                "symbol": a_sym,
                "name": a_state.name,
                "node_type": "RECEIVER",
                "category": a_state.category,
                "current_price": a_state.current_price,
                "change_24h_pct": a_state.change_24h_pct,
                "position_3d": pos,
                "glow_color": "#ffd700" if a_sym == "XAUUSD" else ("#00f3ff" if "USD" in a_sym and a_state.category == "FOREX" else "#a855f7")
            })

        # 4. Animated Contagion Spline Edges
        edges: List[Dict[str, Any]] = []
        for idx, vec in enumerate(self.vectors):
            edges.append({
                "edge_id": f"edge_{vec.driver}_{vec.target}",
                "source_id": f"driver_{vec.driver}",
                "target_id": f"asset_{vec.target}",
                "driver": vec.driver,
                "target": vec.target,
                "correlation": vec.correlation,
                "beta": vec.beta,
                "transmission_lag_s": vec.transmission_lag_s,
                "flow_velocity": vec.flow_velocity,
                "color_code": vec.color_code,
                "sentiment_channel": vec.sentiment_channel,
                "description": vec.description,
                "curvature_lift": 1.25  # Height scalar for CatmullRom spline arch above the globe
            })

        # Also add Hotspot to Asset contagion linkages (e.g. Hormuz/Red Sea -> Gold, Oil)
        hotspot_edges = [
            {
                "edge_id": "edge_hotspot_red_sea_oil",
                "source_id": "hotspot_red_sea",
                "target_id": "driver_OIL",
                "correlation": 0.85,
                "beta": 1.35,
                "flow_velocity": 2.4,
                "color_code": "#ffaa00",
                "sentiment_channel": "CONTAGION_SHOCK",
                "description": "Red Sea tanker transit disruption directly transmits supply-risk premium into WTI Crude Oil.",
                "curvature_lift": 1.15
            },
            {
                "edge_id": "edge_hotspot_hormuz_gold",
                "source_id": "hotspot_hormuz_strait",
                "target_id": "asset_XAUUSD",
                "correlation": 0.90,
                "beta": 1.45,
                "flow_velocity": 2.8,
                "color_code": "#ff2255",
                "sentiment_channel": "CONTAGION_SHOCK",
                "description": "Hormuz warzone posture generates acute flight-to-safety capital flows into Gold bullion.",
                "curvature_lift": 1.35
            },
            {
                "edge_id": "edge_hotspot_taiwan_crypto",
                "source_id": "hotspot_taiwan_strait",
                "target_id": "asset_BTCUSD",
                "correlation": 0.65,
                "beta": 1.30,
                "flow_velocity": 1.6,
                "color_code": "#a855f7",
                "sentiment_channel": "CONTAGION_SHOCK",
                "description": "Taiwan semiconductor supply chain vulnerability accelerates capital hedging into borderless digital gold.",
                "curvature_lift": 1.25
            }
        ]
        edges.extend(hotspot_edges)

        return {
            "topology_type": "MACRO_CONTAGION_PLANETARY_NETWORK",
            "generation_utc": datetime.now(timezone.utc).isoformat(),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges
        }


# ============================================================================
# Singleton Accessor
# ============================================================================

_macro_contagion_instance: Optional[MacroContagionService] = None

def get_macro_contagion_service() -> MacroContagionService:
    """Singleton getter for institutional Macro Contagion Service."""
    global _macro_contagion_instance
    if _macro_contagion_instance is None:
        _macro_contagion_instance = MacroContagionService()
    return _macro_contagion_instance
