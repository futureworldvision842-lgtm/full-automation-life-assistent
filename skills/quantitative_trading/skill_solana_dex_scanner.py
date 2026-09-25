"""
skills/solana/raydium_pumpfun_alpha_scanner.py
High‑frequency scanner for real‑time Solana token liquidity additions and
volume velocity on Raydium and Pump.fun.

Author: Master Muhammad Qureshi
Contact: +923468053268, futureworldvision842@gmail.com
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp
import websockets

# --------------------------------------------------------------------------- #
# Configuration - adjust only if you host your own RPC endpoint.
# --------------------------------------------------------------------------- #
SOLANA_RPC_HTTP = "https://api.mainnet-beta.solana.com"
SOLANA_RPC_WS = "wss://api.mainnet-beta.solana.com"
RAYDIUM_PROGRAM_ID = "5quorZ4M2gZxVZfXbZ5KcXc3t8F4Z1B8YF6j2R2XK9g7"   # placeholder
PUMPFUN_PROGRAM_ID = "PumpFun1111111111111111111111111111111111"   # placeholder

# --------------------------------------------------------------------------- #
# Logging - minimal, JSON‑friendly for downstream processing.
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)

# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class LiquidityEvent:
    """Immutable representation of a liquidity‑addition event."""
    signature: str
    slot: int
    token_mint: str
    amount: int
    program: str
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature": self.signature,
            "slot": self.slot,
            "token_mint": self.token_mint,
            "amount": self.amount,
            "program": self.program,
            "timestamp": self.timestamp,
        }

# --------------------------------------------------------------------------- #
# Low‑level RPC helpers
# --------------------------------------------------------------------------- #
async def _rpc_request(method: str, params: List[Any]) -> Dict[str, Any]:
    """Perform a JSON‑RPC request over HTTP."""
    async with aiohttp.ClientSession() as session:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        async with session.post(SOLANA_RPC_HTTP, json=payload, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.json()
            if "error" in data:
                raise RuntimeError(f"RPC error: {data['error']}")
            return data["result"]


async def _get_slot() -> int:
    """Return the most recent confirmed slot."""
    result = await _rpc_request("getSlot", [{"commitment": "confirmed"}])
    return int(result)


async def _get_block_time(slot: int) -> Optional[int]:
    """Return the Unix timestamp for a slot, or None if unavailable."""
    try:
        result = await _rpc_request("getBlockTime", [slot])
        return int(result) if result is not None else None
    except Exception:  # pragma: no cover - defensive fallback
        return None


# --------------------------------------------------------------------------- #
# WebSocket subscription utilities
# --------------------------------------------------------------------------- #
async def _subscribe_program(program_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Subscribe to all `programSubscribe` notifications for a given program.
    Yields raw notification objects as they arrive.
    """
    sub_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "programSubscribe",
        "params": [program_id, {"encoding": "jsonParsed", "commitment": "confirmed"}],
    }

    async with websockets.connect(SOLANA_RPC_WS) as ws:
        await ws.send(json.dumps(sub_req))
        resp = json.loads(await ws.recv())
        if "error" in resp:
            raise RuntimeError(f"Subscription error: {resp['error']}")

        sub_id = resp.get("result")
        if not sub_id:
            raise RuntimeError("Failed to obtain subscription id")

        try:
            while True:
                raw_msg = await ws.recv()
                notification = json.loads(raw_msg)
                if notification.get("method") == "programNotification":
                    params = notification.get("params", {})
                    if params.get("subscription") == sub_id:
                        yield params.get("result", {})
        finally:
            # Clean up subscription
            unsub_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "programUnsubscribe",
                "params": [sub_id],
            }
            await ws.send(json.dumps(unsub_req))


# --------------------------------------------------------------------------- #
# Core detection logic
# --------------------------------------------------------------------------- #
def _extract_liquidity(event: Dict[str, Any], program: str) -> Optional[LiquidityEvent]:
    """
    Attempt to parse a Raydium or Pump.fun liquidity‑addition event.
    Returns a LiquidityEvent on success, otherwise None.
    """
    try:
        # The exact layout depends on the program; we handle the two most common patterns.
        info = event.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
        if not info:
            return None

        # Raydium: look for `initializePool` or `addLiquidity` instructions.
        if program == RAYDIUM_PROGRAM_ID:
            if info.get("type") not in {"initializePool", "addLiquidity"}:
                return None
            token_mint = info["baseMint"] if "baseMint" in info else info.get("mint")
            amount = int(info.get("baseAmount", 0) or info.get("liquidity", 0))
        # Pump.fun: look for `addLiquidity` in its custom schema.
        elif program == PUMPFUN_PROGRAM_ID:
            if info.get("action") != "addLiquidity":
                return None
            token_mint = info.get("tokenMint")
            amount = int(info.get("amount", 0))
        else:
            return None

        signature = event.get("signature")
        slot = int(event.get("slot", 0))
        timestamp = time.time()
        return LiquidityEvent(
            signature=signature,
            slot=slot,
            token_mint=token_mint,
            amount=amount,
            program=program,
            timestamp=timestamp,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logging.debug("Failed to parse liquidity event: %s", exc)
        return None


async def monitor_liquidity(
    duration_seconds: int = 60,
) -> List[LiquidityEvent]:
    """
    Monitor Raydium and Pump.fun for liquidity‑addition events for the given duration.

    Parameters
    ----------
    duration_seconds:
        How long to listen on the WebSocket (default 60 seconds).

    Returns
    -------
    List[LiquidityEvent]
        All detected events ordered by receipt time.
    """
    end_time = time.time() + max(duration_seconds, 0)
    detected: List[LiquidityEvent] = []

    async def _collect(program_id: str) -> None:
        async for raw in _subscribe_program(program_id):
            ev = _extract_liquidity(raw, program_id)
            if ev:
                logging.info(
                    json.dumps(
                        {
                            "type": "liquidity_detected",
                            "program": ev.program,
                            "token_mint": ev.token_mint,
                            "amount": ev.amount,
                            "signature": ev.signature,
                        }
                    )
                )
                detected.append(ev)
            if time.time() >= end_time:
                break

    # Run both subscriptions concurrently
    await asyncio.wait(
        [asyncio.create_task(_collect(RAYDIUM_PROGRAM_ID)),
         asyncio.create_task(_collect(PUMPFUN_PROGRAM_ID))],
        timeout=duration_seconds + 5,  # small buffer for graceful shutdown
    )
    # Sort by timestamp for deterministic output
    detected.sort(key=lambda e: e.timestamp)
    return detected


# --------------------------------------------------------------------------- #
# Public entry point - J.A.R.V.I.S. compatible
# --------------------------------------------------------------------------- #
def scan_solona_raydium_pumpfun(
    duration_seconds: int = 60,
) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper that launches the async scanner and returns plain dicts.

    Parameters
    ----------
    duration_seconds:
        Number of seconds to monitor the blockchain (default 60).

    Returns
    -------
    List[Dict[str, Any]]
        Each dict corresponds to a `LiquidityEvent` (see `LiquidityEvent.to_dict`).
    """
    try:
        events = asyncio.run(monitor_liquidity(duration_seconds))
        return [e.to_dict() for e in events]
    except Exception as exc:  # pragma: no cover - top‑level safety net
        logging.error("Scanner failed: %s", exc)
        return []


# --------------------------------------------------------------------------- #
# Example usage (removed from production import; kept for documentation)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Run a quick 30‑second scan and pretty‑print results.
    results = scan_solona_raydium_pumpfun(30)
    print(json.dumps(results, indent=2))