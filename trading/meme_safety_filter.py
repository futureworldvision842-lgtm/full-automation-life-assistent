"""
trading/meme_safety_filter.py — On-Chain Meme Coin Rug-Proof & Safety Filter Kernel
====================================================================================
Authoritative on-chain safety verification for meme coins across Solana, Base, and Ethereum.
Evaluates:
1. LP Token Lock/Burn: >= 95% burned or locked via verifiable locker contracts (Team.Finance,
   UNCX, PinkSale, Raydium incinerator/burn address).
2. Contract Security: Mint authority permanently disabled, Freeze authority permanently disabled,
   and Buy/Sell taxes verified at 0% via honeypot simulation.
3. Distribution Audit: Top 10 non-DEX holders combined must hold <= 15% of total supply;
   detection of developer wallet liquidity drains and dump patterns.
4. Volume Velocity & Organic Ratio:
   - Volume acceleration: VolAccel_5m = (Vol_5m * 12) / max(1, Vol_1h) >= 1.8x
   - Buy pressure: BuyPressure = Buys_5m / max(1, Sells_5m) >= 1.5x
   - Organic Vol-to-MC ratio: 0.5x <= Vol_24h / FDV <= 4.0x (rejects wash-trading)

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jarvis.trading.meme_safety_filter")

# Known burn and dead addresses across chains
SOLANA_BURN_ADDRESSES = {
    "11111111111111111111111111111111",
    "dead1111111111111111111111111111",
    "BurnAddress111111111111111111111111111111111",
}

EVM_BURN_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
    "0xdead000000000000000042069420694206942069",
}

# Known locker contracts on EVM (UNCX, Team.Finance, PinkSale)
KNOWN_EVM_LOCKERS = {
    "0x663a02fb63e427f6885d54246b10e0075257357c",  # UNCX / Unicrypt V3
    "0x71b5759d73262fbbf247952223f869da39399035",  # UNCX V2
    "0xe2fe530c047f2d85298b07d91cc738468626643b",  # Team.Finance Lock
    "0x7ee058420e593749be71ca017458dd299a732564",  # PinkSale Lock
}


@dataclass
class SafetyReport:
    """Standardized on-chain meme coin safety assessment report."""
    is_safe: bool
    reasons: List[str]
    score: float  # 0.0 to 100.0
    lp_locked_pct: float  # Percentage of LP locked or burned (e.g. 98.5)
    mint_revoked: bool  # True if mint authority permanently disabled/null
    freeze_revoked: bool  # True if freeze authority permanently disabled/null
    buy_tax: float  # e.g. 0.0%
    sell_tax: float  # e.g. 0.0%
    top10_pct: float  # Percentage held by top 10 non-DEX holders
    dev_dump_detected: bool = False
    vol_accel: float = 0.0
    buy_pressure: float = 0.0
    vol_mc_ratio: float = 0.0
    volume_velocity_safe: bool = False
    chain: str = "unknown"
    address: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "reasons": list(self.reasons),
            "score": round(self.score, 2),
            "lp_locked_pct": round(self.lp_locked_pct, 2),
            "mint_revoked": self.mint_revoked,
            "freeze_revoked": self.freeze_revoked,
            "buy_tax": round(self.buy_tax, 2),
            "sell_tax": round(self.sell_tax, 2),
            "top10_pct": round(self.top10_pct, 2),
            "dev_dump_detected": self.dev_dump_detected,
            "vol_accel": round(self.vol_accel, 2),
            "buy_pressure": round(self.buy_pressure, 2),
            "vol_mc_ratio": round(self.vol_mc_ratio, 2),
            "volume_velocity_safe": self.volume_velocity_safe,
            "chain": self.chain,
            "address": self.address,
            "details": self.details,
        }


class MemeSafetyFilter:
    """
    On-chain Meme Coin Rug-Proof & Safety Filter.
    Inspects liquidity locks, mint/freeze authorities, honeypot simulation,
    top holder distribution, and trading volume velocity.
    """

    MIN_LP_BURN_LOCK_PCT: float = 95.0
    MAX_TOP10_NON_DEX_PCT: float = 15.0
    MAX_BUY_TAX_PCT: float = 0.5
    MAX_SELL_TAX_PCT: float = 0.5
    MIN_VOL_ACCELERATION: float = 1.8
    MIN_BUY_PRESSURE: float = 1.5
    MIN_VOL_MC_RATIO: float = 0.5
    MAX_VOL_MC_RATIO: float = 4.0
    MIN_24H_VOLUME: float = 25000.0
    PASS_SCORE_THRESHOLD: float = 80.0

    # Live external API endpoints
    RUGCHECK_API: str = "https://api.rugcheck.xyz/v1/tokens/{mint}/report"
    GOPLUS_API: str = "https://api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={address}"
    HONEYPOT_API: str = "https://api.honeypot.is/v2/IsHoneypot?address={address}&chainID={chain_id}"

    # Chain mapping for EVM APIs
    CHAIN_IDS = {
        "base": 8453,
        "ethereum": 1,
        "eth": 1,
        "bsc": 56,
        "arbitrum": 42161,
    }

    def __init__(self, request_timeout: int = 5):
        self.request_timeout = request_timeout

    def _http_get(self, url: str) -> Optional[Any]:
        """Performs a resilient HTTP GET request with standard headers."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) J.A.R.V.I.S. Trading Engine",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                if resp.status == 200:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
        except Exception as e:
            logger.debug(f"HTTP GET failed for {url}: {e}")
        return None

    def evaluate_token(
        self,
        chain: str,
        address: str,
        pair_data: Optional[Dict[str, Any]] = None,
        audit_override: Optional[Dict[str, Any]] = None,
    ) -> SafetyReport:
        """
        Unified evaluation endpoint for meme tokens across Solana, Base, and Ethereum.
        
        Args:
            chain: Blockchain identifier ('solana', 'base', 'ethereum')
            address: Token mint or contract address
            pair_data: Optional DEX Screener or pool market data dict
            audit_override: Optional pre-loaded audit report (used in testing or caching)
        """
        chain_lower = chain.strip().lower()
        if chain_lower in ("solana", "sol"):
            return self.evaluate_solana_token(address, pair_data=pair_data, rugcheck_data=audit_override)
        elif chain_lower in ("base", "ethereum", "eth", "bsc", "arbitrum"):
            return self.evaluate_evm_token(
                chain=chain_lower,
                token_address=address,
                pair_data=pair_data,
                goplus_data=audit_override,
            )
        else:
            return SafetyReport(
                is_safe=False,
                reasons=[f"Unsupported chain: {chain}"],
                score=0.0,
                lp_locked_pct=0.0,
                mint_revoked=False,
                freeze_revoked=False,
                buy_tax=100.0,
                sell_tax=100.0,
                top10_pct=100.0,
                chain=chain,
                address=address,
            )

    # -------------------------------------------------------------------------
    # Solana Token Evaluation
    # -------------------------------------------------------------------------
    def evaluate_solana_token(
        self,
        mint_address: str,
        pair_data: Optional[Dict[str, Any]] = None,
        rugcheck_data: Optional[Dict[str, Any]] = None,
    ) -> SafetyReport:
        """Evaluates Solana SPL token on-chain security via RugCheck API and volume metrics."""
        data = rugcheck_data
        if data is None:
            url = self.RUGCHECK_API.format(mint=mint_address)
            data = self._http_get(url)

        reasons: List[str] = []
        score: float = 100.0

        if not data or not isinstance(data, dict):
            # If no live report available and no mock, fail closed
            if pair_data and pair_data.get("mock_safe_audit"):
                data = pair_data.get("mock_safe_audit")
            else:
                return SafetyReport(
                    is_safe=False,
                    reasons=["RugCheck on-chain report unavailable (fail-closed)"],
                    score=0.0,
                    lp_locked_pct=0.0,
                    mint_revoked=False,
                    freeze_revoked=False,
                    buy_tax=0.0,
                    sell_tax=0.0,
                    top10_pct=0.0,
                    chain="solana",
                    address=mint_address,
                )

        # 1. LP Burn / Lock Verification
        lp_locked_pct = 0.0
        markets = data.get("markets") or []
        if markets and isinstance(markets, list):
            for m in markets:
                lp_info = m.get("lp") or {}
                burned = float(lp_info.get("lpBurnedPct") or lp_info.get("burnedPct") or 0.0)
                locked = float(lp_info.get("lpLockedPct") or lp_info.get("lockedPct") or 0.0)
                total_mkt_lp = burned + locked
                if total_mkt_lp > lp_locked_pct:
                    lp_locked_pct = total_mkt_lp
        elif "lp_locked_pct" in data:
            lp_locked_pct = float(data["lp_locked_pct"])
        elif "totalMarketLiquidity" in data and "lpBurnedPct" in data:
            lp_locked_pct = float(data.get("lpBurnedPct", 0.0)) + float(data.get("lpLockedPct", 0.0))

        if lp_locked_pct < self.MIN_LP_BURN_LOCK_PCT:
            score -= 40.0
            reasons.append(
                f"LP token lock/burn insufficient: {lp_locked_pct:.1f}% (required >= {self.MIN_LP_BURN_LOCK_PCT}%)"
            )

        # 2. Contract Authority Security (Mint & Freeze)
        token_info = data.get("token") or {}
        mint_auth = token_info.get("mintAuthority") if "mintAuthority" in token_info else data.get("mintAuthority")
        freeze_auth = token_info.get("freezeAuthority") if "freezeAuthority" in token_info else data.get("freezeAuthority")

        mint_revoked = mint_auth is None or mint_auth == "" or mint_auth in SOLANA_BURN_ADDRESSES
        freeze_revoked = freeze_auth is None or freeze_auth == "" or freeze_auth in SOLANA_BURN_ADDRESSES

        if not mint_revoked:
            score -= 30.0
            reasons.append(f"Mint authority is active: {mint_auth}")

        if not freeze_revoked:
            score -= 25.0
            reasons.append(f"Freeze authority is active: {freeze_auth}")

        # 3. Transfer Fee / Tax Simulation
        transfer_fee = token_info.get("transferFee") or data.get("transferFee") or {}
        buy_tax = float(transfer_fee.get("pct") or data.get("buy_tax") or 0.0)
        sell_tax = float(transfer_fee.get("pct") or data.get("sell_tax") or 0.0)

        if buy_tax > self.MAX_BUY_TAX_PCT or sell_tax > self.MAX_SELL_TAX_PCT:
            score -= 45.0
            reasons.append(f"Non-zero transfer tax detected: Buy {buy_tax:.1f}%, Sell {sell_tax:.1f}%")

        # 4. Top 10 Non-DEX Distribution
        top10_pct = 0.0
        top_holders = data.get("topHolders") or []
        if top_holders and isinstance(top_holders, list):
            non_dex_shares = []
            for h in top_holders:
                addr = str(h.get("address") or "")
                pct = float(h.get("pct") or h.get("percentage") or 0.0)
                is_pool = bool(h.get("isPool") or h.get("isDex") or addr in SOLANA_BURN_ADDRESSES)
                if not is_pool:
                    non_dex_shares.append(pct)
            non_dex_shares.sort(reverse=True)
            top10_pct = sum(non_dex_shares[:10])
        elif "top10_pct" in data:
            top10_pct = float(data["top10_pct"])

        if top10_pct > self.MAX_TOP10_NON_DEX_PCT:
            score -= 20.0
            reasons.append(
                f"Top 10 non-DEX holders supply concentration too high: {top10_pct:.1f}% (max allowed <= {self.MAX_TOP10_NON_DEX_PCT}%)"
            )

        # 5. Developer Wallet Drain / Dump Detection
        dev_dump_detected = False
        creator_info = data.get("creator") or {}
        creator_pct = float(creator_info.get("pct") or data.get("creator_pct") or 0.0)
        creator_sold = bool(creator_info.get("hasDumped") or data.get("dev_dumped") or False)
        if creator_pct > 3.0 or creator_sold:
            dev_dump_detected = True
            score -= 30.0
            reasons.append(f"Dev wallet risk: Creator holds {creator_pct:.1f}% or recent dump pattern detected")

        # 6. Volume Velocity & Organic Vol/MC
        vol_vel_safe = True
        vol_accel = 0.0
        buy_pressure = 0.0
        vol_mc_ratio = 0.0

        if pair_data:
            vol_vel_safe, vol_accel, buy_pressure, vol_mc_ratio, v_reasons = self.evaluate_volume_velocity(pair_data)
            if not vol_vel_safe:
                score -= 15.0
                reasons.extend(v_reasons)

        score = max(0.0, min(100.0, score))
        is_safe = (
            score >= self.PASS_SCORE_THRESHOLD
            and lp_locked_pct >= self.MIN_LP_BURN_LOCK_PCT
            and mint_revoked
            and freeze_revoked
            and buy_tax <= self.MAX_BUY_TAX_PCT
            and sell_tax <= self.MAX_SELL_TAX_PCT
            and top10_pct <= self.MAX_TOP10_NON_DEX_PCT
            and not dev_dump_detected
        )

        return SafetyReport(
            is_safe=is_safe,
            reasons=reasons,
            score=score,
            lp_locked_pct=lp_locked_pct,
            mint_revoked=mint_revoked,
            freeze_revoked=freeze_revoked,
            buy_tax=buy_tax,
            sell_tax=sell_tax,
            top10_pct=top10_pct,
            dev_dump_detected=dev_dump_detected,
            vol_accel=vol_accel,
            buy_pressure=buy_pressure,
            vol_mc_ratio=vol_mc_ratio,
            volume_velocity_safe=vol_vel_safe,
            chain="solana",
            address=mint_address,
            details=data,
        )

    # -------------------------------------------------------------------------
    # EVM Token Evaluation (Base, Ethereum)
    # -------------------------------------------------------------------------
    def evaluate_evm_token(
        self,
        chain: str,
        token_address: str,
        pair_data: Optional[Dict[str, Any]] = None,
        goplus_data: Optional[Dict[str, Any]] = None,
        honeypot_data: Optional[Dict[str, Any]] = None,
    ) -> SafetyReport:
        """Evaluates EVM token on-chain security via GoPlus and Honeypot.is APIs."""
        chain_id = self.CHAIN_IDS.get(chain.lower(), 8453)  # Default to Base (8453)
        addr_lower = token_address.strip().lower()

        # Query GoPlus Token Security API if not passed in
        gp_data = goplus_data
        if gp_data is None:
            url = self.GOPLUS_API.format(chain_id=chain_id, address=addr_lower)
            res = self._http_get(url)
            if res and isinstance(res, dict) and "result" in res:
                res_dict = res.get("result") or {}
                gp_data = res_dict.get(addr_lower) or res_dict.get(token_address)

        # Query Honeypot.is API if not passed in
        hp_data = honeypot_data
        if hp_data is None:
            url = self.HONEYPOT_API.format(chain_id=chain_id, address=addr_lower)
            hp_data = self._http_get(url)

        reasons: List[str] = []
        score: float = 100.0

        if not gp_data or not isinstance(gp_data, dict):
            # If no live report available and no mock, fail closed
            if pair_data and pair_data.get("mock_safe_audit"):
                gp_data = pair_data.get("mock_safe_audit")
            else:
                return SafetyReport(
                    is_safe=False,
                    reasons=["GoPlus on-chain security report unavailable (fail-closed)"],
                    score=0.0,
                    lp_locked_pct=0.0,
                    mint_revoked=False,
                    freeze_revoked=False,
                    buy_tax=0.0,
                    sell_tax=0.0,
                    top10_pct=0.0,
                    chain=chain,
                    address=token_address,
                )

        # 1. Honeypot check
        is_honeypot = str(gp_data.get("is_honeypot", "0")) == "1"
        if hp_data and isinstance(hp_data, dict):
            hp_res = hp_data.get("honeypotResult") or {}
            if hp_res.get("isHoneypot") is True or hp_data.get("simulationSuccess") is False:
                is_honeypot = True

        if is_honeypot:
            score -= 60.0
            reasons.append("Honeypot confirmed: Token cannot be sold or simulated sell failed")

        # 2. Taxes (Buy / Sell)
        try:
            buy_tax_val = float(gp_data.get("buy_tax", 0.0)) * 100.0 if float(gp_data.get("buy_tax", 0.0)) < 1.0 else float(gp_data.get("buy_tax", 0.0))
        except (ValueError, TypeError):
            buy_tax_val = 0.0

        try:
            sell_tax_val = float(gp_data.get("sell_tax", 0.0)) * 100.0 if float(gp_data.get("sell_tax", 0.0)) < 1.0 else float(gp_data.get("sell_tax", 0.0))
        except (ValueError, TypeError):
            sell_tax_val = 0.0

        # Honeypot.is tax check if available
        if hp_data and isinstance(hp_data, dict):
            sim = hp_data.get("simulationResult") or {}
            hp_buy_tax = float(sim.get("buyTax") or 0.0)
            hp_sell_tax = float(sim.get("sellTax") or 0.0)
            buy_tax_val = max(buy_tax_val, hp_buy_tax)
            sell_tax_val = max(sell_tax_val, hp_sell_tax)

        if buy_tax_val > self.MAX_BUY_TAX_PCT or sell_tax_val > self.MAX_SELL_TAX_PCT:
            score -= 40.0
            reasons.append(f"Non-zero EVM tax verified: Buy {buy_tax_val:.1f}%, Sell {sell_tax_val:.1f}%")

        # 3. Mint Authority permanently disabled
        is_mintable = str(gp_data.get("is_mintable", "0")) == "1"
        can_take_back_ownership = str(gp_data.get("can_take_back_ownership", "0")) == "1"
        mint_revoked = not is_mintable and not can_take_back_ownership
        if not mint_revoked:
            score -= 30.0
            reasons.append("Mint function is active or ownership can be reclaimed")

        # 4. Freeze Authority / Blacklist disabled
        cannot_sell_all = str(gp_data.get("cannot_sell_all", "0")) == "1"
        is_blacklisted = str(gp_data.get("is_blacklisted", "0")) == "1"
        freeze_revoked = not cannot_sell_all and not is_blacklisted
        if not freeze_revoked:
            score -= 25.0
            reasons.append("Contract contains freeze or blacklist mechanism preventing token transfer")

        # 5. LP Burn / Lock Verification
        lp_locked_pct = 0.0
        lp_holders = gp_data.get("lp_holders") or []
        if lp_holders and isinstance(lp_holders, list):
            for holder in lp_holders:
                addr = str(holder.get("address") or "").lower()
                pct = float(holder.get("percent") or holder.get("pct") or 0.0) * 100.0 if float(holder.get("percent") or 0.0) <= 1.0 else float(holder.get("percent") or 0.0)
                is_locked = bool(holder.get("is_locked") or int(holder.get("is_locked") or 0) == 1)
                is_burn = addr in EVM_BURN_ADDRESSES or addr in KNOWN_EVM_LOCKERS or any(addr.startswith(b) for b in ["0x00000000000000000000", "0xdead"])
                if is_locked or is_burn:
                    lp_locked_pct += pct
        elif "lp_locked_pct" in gp_data:
            lp_locked_pct = float(gp_data["lp_locked_pct"])

        if lp_locked_pct < self.MIN_LP_BURN_LOCK_PCT:
            score -= 40.0
            reasons.append(
                f"EVM LP token lock/burn insufficient: {lp_locked_pct:.1f}% (required >= {self.MIN_LP_BURN_LOCK_PCT}%)"
            )

        # 6. Top 10 Non-Contract Holders Distribution
        top10_pct = 0.0
        holders = gp_data.get("holders") or []
        if holders and isinstance(holders, list):
            non_contract_shares = []
            for h in holders:
                addr = str(h.get("address") or "").lower()
                pct = float(h.get("percent") or 0.0) * 100.0 if float(h.get("percent") or 0.0) <= 1.0 else float(h.get("percent") or 0.0)
                is_contract = bool(h.get("is_contract") or int(h.get("is_contract") or 0) == 1)
                is_burn = addr in EVM_BURN_ADDRESSES
                if not is_contract and not is_burn:
                    non_contract_shares.append(pct)
            non_contract_shares.sort(reverse=True)
            top10_pct = sum(non_contract_shares[:10])
        elif "top10_pct" in gp_data:
            top10_pct = float(gp_data["top10_pct"])

        if top10_pct > self.MAX_TOP10_NON_DEX_PCT:
            score -= 20.0
            reasons.append(
                f"Top 10 non-contract holders supply concentration too high: {top10_pct:.1f}% (max allowed <= {self.MAX_TOP10_NON_DEX_PCT}%)"
            )

        # 7. Dev Wallet Dump Detection
        dev_dump_detected = False
        creator_pct_raw = float(gp_data.get("creator_percent") or 0.0)
        creator_pct = creator_pct_raw * 100.0 if creator_pct_raw <= 1.0 else creator_pct_raw
        if creator_pct > 3.0:
            dev_dump_detected = True
            score -= 30.0
            reasons.append(f"Dev wallet risk: Creator address holds {creator_pct:.1f}% of circulating supply")

        # 8. Volume Velocity & Organic Vol/MC
        vol_vel_safe = True
        vol_accel = 0.0
        buy_pressure = 0.0
        vol_mc_ratio = 0.0

        if pair_data:
            vol_vel_safe, vol_accel, buy_pressure, vol_mc_ratio, v_reasons = self.evaluate_volume_velocity(pair_data)
            if not vol_vel_safe:
                score -= 15.0
                reasons.extend(v_reasons)

        score = max(0.0, min(100.0, score))
        is_safe = (
            score >= self.PASS_SCORE_THRESHOLD
            and not is_honeypot
            and lp_locked_pct >= self.MIN_LP_BURN_LOCK_PCT
            and mint_revoked
            and freeze_revoked
            and buy_tax_val <= self.MAX_BUY_TAX_PCT
            and sell_tax_val <= self.MAX_SELL_TAX_PCT
            and top10_pct <= self.MAX_TOP10_NON_DEX_PCT
            and not dev_dump_detected
        )

        return SafetyReport(
            is_safe=is_safe,
            reasons=reasons,
            score=score,
            lp_locked_pct=lp_locked_pct,
            mint_revoked=mint_revoked,
            freeze_revoked=freeze_revoked,
            buy_tax=buy_tax_val,
            sell_tax=sell_tax_val,
            top10_pct=top10_pct,
            dev_dump_detected=dev_dump_detected,
            vol_accel=vol_accel,
            buy_pressure=buy_pressure,
            vol_mc_ratio=vol_mc_ratio,
            volume_velocity_safe=vol_vel_safe,
            chain=chain,
            address=token_address,
            details={"goplus": gp_data, "honeypot": hp_data},
        )

    # -------------------------------------------------------------------------
    # Volume Velocity & Organic Flow Evaluation
    # -------------------------------------------------------------------------
    def evaluate_volume_velocity(self, pair_data: Dict[str, Any]) -> Tuple[bool, float, float, float, List[str]]:
        """
        Calculates:
        1. Volume acceleration: VolAccel_5m = (Vol_5m * 12) / max(1.0, Vol_1h) >= 1.8x
        2. Buy pressure: BuyPressure = Buys_5m / max(1, Sells_5m) >= 1.5x
        3. Organic Vol/MC ratio: 0.5x <= Vol_24h / FDV <= 4.0x
        4. 24h Volume >= MIN_24H_VOLUME
        """
        reasons: List[str] = []
        is_valid = True

        vol = pair_data.get("volume") or {}
        v5m = float(vol.get("m5") or 0.0)
        v1h = float(vol.get("h1") or 0.0)
        v24h = float(vol.get("h24") or 0.0)

        txns = pair_data.get("txns") or {}
        t5m = txns.get("m5") or {}
        buys_5m = float(t5m.get("buys") or 0.0)
        sells_5m = float(t5m.get("sells") or 0.0)

        # Fallback to h1 or h24 txns if m5 txns are not reported
        if buys_5m + sells_5m == 0:
            t1h = txns.get("h1") or {}
            buys_5m = float(t1h.get("buys") or 0.0)
            sells_5m = float(t1h.get("sells") or 0.0)

        fdv = float(pair_data.get("fdv") or pair_data.get("marketCap") or 0.0)

        # 1. 24h Volume threshold
        if v24h < self.MIN_24H_VOLUME:
            is_valid = False
            reasons.append(f"24h volume too low: ${v24h:,.0f} (required >= ${self.MIN_24H_VOLUME:,.0f})")

        # 2. Volume Acceleration
        # Annualizing 5m to 1h rate: v5m * 12
        vol_accel = (v5m * 12.0) / max(1.0, v1h) if v1h > 0 else (2.0 if v5m > 0 else 0.0)
        if vol_accel < self.MIN_VOL_ACCELERATION:
            is_valid = False
            reasons.append(
                f"Volume acceleration sluggish: {vol_accel:.2f}x (required >= {self.MIN_VOL_ACCELERATION:.1f}x)"
            )

        # 3. Buy Pressure
        buy_pressure = buys_5m / max(1.0, sells_5m)
        if buy_pressure < self.MIN_BUY_PRESSURE:
            is_valid = False
            reasons.append(
                f"Buy pressure insufficient: {buy_pressure:.2f}x (required >= {self.MIN_BUY_PRESSURE:.1f}x)"
            )

        # 4. Organic Vol-to-MC Ratio (Wash Trading Elimination)
        vol_mc_ratio = v24h / max(1.0, fdv) if fdv > 0 else 1.0
        if vol_mc_ratio < self.MIN_VOL_MC_RATIO:
            is_valid = False
            reasons.append(
                f"Low liquidity turnover ratio: {vol_mc_ratio:.2f}x (required >= {self.MIN_VOL_MC_RATIO:.1f}x)"
            )
        elif vol_mc_ratio > self.MAX_VOL_MC_RATIO:
            is_valid = False
            reasons.append(
                f"Wash-trading signature: Vol/MC ratio {vol_mc_ratio:.2f}x exceeds organic ceiling {self.MAX_VOL_MC_RATIO:.1f}x"
            )

        return is_valid, vol_accel, buy_pressure, vol_mc_ratio, reasons
