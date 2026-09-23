"""
skills/dexscreener_meme_research.py — Real-Time DEX Screener Meme Coin On-Chain Quant Skill
========================================================================================
Empowers J.A.R.V.I.S. with institutional-grade on-chain meme coin research using free,
unauthenticated public DEX Screener APIs across Solana, Base, Ethereum, and BSC:
1. 'trending' / 'top': Discovers top-boosted viral meme coins on Solana & Base.
2. 'search': Real-time lookup of any token or pair with liquidity USD, volume, and buy/sell ratios.
3. 'deep_research': Quantitative risk audit (volume-to-liquidity ratio, buy pressure, rug risk).

Owner: Master Muhammad Qureshi (+923468053268, futureworldvision842@gmail.com)
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.parse
from typing import Any, Dict, List, Optional

try:
    from trading.meme_safety_filter import MemeSafetyFilter, SafetyReport
except ImportError:
    MemeSafetyFilter = None  # type: ignore
    SafetyReport = None  # type: ignore

logger = logging.getLogger("jarvis.skills.dexscreener")

MANIFEST = {
    "name": "dexscreener_meme_research",
    "description": "Real-time on-chain meme coin quant scanner and research engine using DEX Screener public API (Solana, Base, Ethereum).",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Operation to perform: 'top_trending', 'search', 'deep_research', 'status'"
            },
            "query": {
                "type": "STRING",
                "description": "Token symbol, name, or contract address (e.g. 'pepe', 'bonk', 'wif', or Solana mint address)"
            },
            "chain": {
                "type": "STRING",
                "description": "Optional chain filter (e.g. 'solana', 'base', 'ethereum')"
            }
        },
        "required": ["action"]
    }
}


def _http_get(url: str, timeout: int = 6) -> Optional[Any]:
    """Helper to perform HTTP GET request with User-Agent header."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                raw = response.read().decode("utf-8")
                return json.loads(raw)
    except Exception as e:
        logger.debug(f"DEX Screener API request failed for {url}: {e}")
    return None


def get_top_boosted_meme_coins(limit: int = 8) -> str:
    """Fetches top-boosted viral tokens currently active on DEX Screener."""
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    data = _http_get(url)
    if not data or not isinstance(data, list):
        return "⚠️ Could not retrieve live boosted tokens from DEX Screener (Network timeout or rate limit)."

    tokens = data[:limit]
    lines = [
        "🔥 [DEX SCREENER TOP BOOSTED MEME COINS]",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for idx, t in enumerate(tokens, 1):
        chain = (t.get("chainId") or "unknown").upper()
        addr = t.get("tokenAddress") or "N/A"
        desc = (t.get("description") or t.get("url") or "").strip()
        if len(desc) > 80:
            desc = desc[:77] + "..."
        link = t.get("url") or f"https://dexscreener.com/{chain.lower()}/{addr}"

        short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 12 else addr
        lines.append(f"{idx}. [{chain}] Address: `{short_addr}`")
        if desc:
            lines.append(f"   Premise: {desc}")
        lines.append(f"   DEX Chart: {link}")

    return "\n".join(lines)


def search_meme_coin(query: str, chain_filter: Optional[str] = None) -> str:
    """Searches for tokens by symbol or address and reports liquidity and metrics."""
    clean_q = urllib.parse.quote(query.strip())
    url = f"https://api.dexscreener.com/latest/dex/search?q={clean_q}"
    data = _http_get(url)
    if not data or "pairs" not in data or not data["pairs"]:
        return f"🔍 No liquidity pools found on DEX Screener for '{query}'."

    pairs = data["pairs"]
    if chain_filter:
        pairs = [p for p in pairs if p.get("chainId", "").lower() == chain_filter.lower()] or pairs

    # Sort by liquidity USD descending
    pairs.sort(key=lambda p: float((p.get("liquidity") or {}).get("usd", 0) or 0), reverse=True)
    top_pairs = pairs[:3]

    lines = [
        f"📊 [DEX SCREENER MEME COIN RADAR: '{query.upper()}']",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    for p in top_pairs:
        base = p.get("baseToken") or {}
        quote = p.get("quoteToken") or {}
        sym = f"{base.get('symbol', 'UNKNOWN')}/{quote.get('symbol', 'USD')}"
        chain = (p.get("chainId") or "CHAIN").upper()
        dex = (p.get("dexId") or "DEX").upper()
        price = p.get("priceUsd", "0.0")
        liq = float((p.get("liquidity") or {}).get("usd", 0) or 0)
        vol24 = float((p.get("volume") or {}).get("h24") or 0)
        fdv = float(p.get("fdv") or 0)

        price_change = p.get("priceChange") or {}
        m5 = price_change.get("m5", 0)
        h1 = price_change.get("h1", 0)
        h24 = price_change.get("h24", 0)

        txns24 = (p.get("txns") or {}).get("h24") or {}
        buys = txns24.get("buys", 0)
        sells = txns24.get("sells", 0)
        buy_ratio = round((buys / (buys + sells) * 100), 1) if (buys + sells) > 0 else 50.0

        pair_url = p.get("url") or f"https://dexscreener.com/{chain.lower()}/{p.get('pairAddress')}"

        lines.append(f"• **{sym}** ({chain} • {dex})")
        lines.append(f"  💰 Price: ${price} | Market Cap: ${fdv:,.0f}")
        lines.append(f"  💧 Liquidity: ${liq:,.0f} | 24h Vol: ${vol24:,.0f}")
        lines.append(f"  📈 Changes: 5m: {m5:+.1f}% | 1h: {h1:+.1f}% | 24h: {h24:+.1f}%")
        lines.append(f"  ⚖️ Buy/Sell Pressure: {buy_ratio}% Buys ({buys:,} Buys / {sells:,} Sells)")
        lines.append(f"  🔗 Chart: {pair_url}")
        lines.append("")

    return "\n".join(lines).strip()


def deep_meme_coin_research(query: str) -> str:
    """Conducts quantitative safety and momentum evaluation of a meme coin."""
    clean_q = urllib.parse.quote(query.strip())
    url = f"https://api.dexscreener.com/latest/dex/search?q={clean_q}"
    data = _http_get(url)
    if not data or "pairs" not in data or not data["pairs"]:
        return f"❌ Deep research failed: No active DEX pools found for '{query}'."

    # Top pool by liquidity
    pairs = sorted(data["pairs"], key=lambda p: float((p.get("liquidity") or {}).get("usd", 0) or 0), reverse=True)
    best = pairs[0]

    base = best.get("baseToken") or {}
    chain = (best.get("chainId") or "SOLANA").upper()
    price = best.get("priceUsd", "0.0")
    liq = float((best.get("liquidity") or {}).get("usd", 0) or 0)
    vol24 = float((best.get("volume") or {}).get("h24") or 0)
    fdv = float(best.get("fdv") or 0)

    txns24 = (best.get("txns") or {}).get("h24") or {}
    buys = txns24.get("buys", 0)
    sells = txns24.get("sells", 0)
    total_txns = buys + sells
    buy_pct = (buys / total_txns * 100) if total_txns > 0 else 50

    # Quantitative Health Checks
    score = 50
    risks = []
    positives = []

    if liq >= 100000:
        score += 20
        positives.append(f"Deep liquidity reserve (${liq:,.0f}) protects against slippage.")
    elif liq < 20000:
        score -= 25
        risks.append(f"Extremely low liquidity (${liq:,.0f}) — high dump / slippage hazard.")
    else:
        score += 5
        positives.append(f"Moderate liquidity (${liq:,.0f}).")

    vol_liq_ratio = vol24 / liq if liq > 0 else 0
    if vol_liq_ratio > 3.0:
        score += 15
        positives.append(f"Hyper-active trading velocity (Vol/Liq ratio: {vol_liq_ratio:.1f}x).")
    elif vol_liq_ratio < 0.2:
        score -= 10
        risks.append(f"Stagnant volume relative to pool size ({vol_liq_ratio:.2f}x).")

    if buy_pct > 55:
        score += 10
        positives.append(f"Bullish order flow ({buy_pct:.1f}% buy transactions).")
    elif buy_pct < 42:
        score -= 15
        risks.append(f"Heavy selling absorption pressure ({100 - buy_pct:.1f}% sell transactions).")

    score = max(5, min(95, score))
    rating = "BULLISH MOMENTUM" if score >= 70 else ("NEUTRAL / CAUTION" if score >= 45 else "EXTREME RISK / LOW QUALITY")

    token_addr = str(base.get("address") or best.get("pairAddress") or "")
    safety_rep = None
    if MemeSafetyFilter:
        try:
            filter_engine = MemeSafetyFilter()
            safety_rep = filter_engine.evaluate_token(chain=chain.lower(), address=token_addr, pair_data=best)
        except Exception as e:
            logger.debug(f"On-chain safety audit failed: {e}")

    lines = [
        f"🔬 [INSTITUTIONAL MEME COIN QUANT AUDIT: {base.get('symbol', query).upper()}]",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• Token: {base.get('name')} (${base.get('symbol')}) | Chain: {chain}",
        f"• Contract: `{token_addr}`",
        f"• Current Price: ${price} | Fully Diluted Valuation: ${fdv:,.0f}",
        f"• Liquidity Pool: ${liq:,.0f} | 24h Trading Volume: ${vol24:,.0f}",
        f"• Volume / Liquidity Ratio: {vol_liq_ratio:.2f}x",
        f"• Order Book Flow: {buys:,} Buys vs {sells:,} Sells ({buy_pct:.1f}% Buy Dominance)",
    ]

    if safety_rep:
        status_tag = "✅ VERIFIED RUG-PROOF" if safety_rep.is_safe else "⚠️ CAUTION / FAILED SAFETY"
        lines.extend([
            "",
            f"🛡️ [ON-CHAIN SECURITY AUDIT: {status_tag}]",
            f"• Safety Score: {safety_rep.score:.1f}/100",
            f"• LP Burned/Locked: {safety_rep.lp_locked_pct:.1f}% ({'PASSED >=95%' if safety_rep.lp_locked_pct >= 95.0 else 'FAILED <95%'})",
            f"• Mint Authority: {'Permanently Disabled (Safe)' if safety_rep.mint_revoked else 'ACTIVE (High Risk)'}",
            f"• Freeze Authority: {'Permanently Disabled (Safe)' if safety_rep.freeze_revoked else 'ACTIVE (High Risk)'}",
            f"• Verified Buy/Sell Tax: Buy {safety_rep.buy_tax:.1f}% | Sell {safety_rep.sell_tax:.1f}%",
            f"• Top 10 Distribution: {safety_rep.top10_pct:.1f}% ({'PASSED <=15%' if safety_rep.top10_pct <= 15.0 else 'CONCENTRATED >15%'})",
            f"• Dev Dump Pattern: {'CLEAN (No Dump)' if not safety_rep.dev_dump_detected else 'ALERT (Dump Detected)'}",
        ])
        if not safety_rep.is_safe and safety_rep.reasons:
            lines.append("• Safety Rejection Reasons: " + "; ".join(safety_rep.reasons[:3]))

    lines.extend([
        "",
        f"🛡️ QUANT REPUTATION SCORE: {score}/100 [{rating}]",
        f"• Strengths: " + (", ".join(positives) if positives else "None identified."),
        f"• Risk Warnings: " + (", ".join(risks) if risks else "Standard meme volatility applies."),
        f"• Direct Pool: {best.get('url')}"
    ])

    return "\n".join(lines)


def run(parameters: Optional[Dict[str, Any]] = None, player=None, speak=None) -> str:
    """Entry point for J.A.R.V.I.S. skill loader."""
    params = parameters or {}
    action = str(params.get("action") or "top_trending").lower()
    query = str(params.get("query") or "")
    chain = params.get("chain")

    if action in ("top_trending", "top", "trending", "boosted"):
        return get_top_boosted_meme_coins()
    elif action in ("search", "scan", "lookup") or (query and action != "deep_research"):
        return search_meme_coin(query or "pepe", chain_filter=chain)
    elif action in ("deep_research", "research", "audit"):
        return deep_meme_coin_research(query or "pepe")
    elif action == "status":
        return (
            "✅ [DEX SCREENER ON-CHAIN MEME RADAR ACTIVE]\n"
            "• Public API: https://api.dexscreener.com\n"
            "• Supported Chains: Solana, Base, Ethereum, BSC, Arbitrum\n"
            "• Zero Paid API Dependency: 100% Free Live On-Chain Data"
        )
    else:
        return f"Unknown DEX action: {action}. Supported: top_trending, search, deep_research, status."


if __name__ == "__main__":
    print(get_top_boosted_meme_coins(3))
    print("\n")
    print(search_meme_coin("pepe"))
