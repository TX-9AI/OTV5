"""
execution/handoff.py  v1.1
v1.1  2026-10-03  OTV4TEST r193 (CFG.1) — its config dials are read as config.NAME with NO literal fallback; config v4.48 now defines them (they were getattr defaults on names config never had). Values unchanged.
v1.0  2026-09-10  OTV4TEST r12 — THE HANDOFF GRANT. Operator: the liquidity hunt
      must hand off to the sweep on a rejection even while an ORB is open, and
      an open hunt must never block an ORB→sweep sequence. The slot rule on
      this repo is binary (any non-butterfly position blocks every entry), so
      instead of more exceptions the handing-off strategy writes an EXPLICIT
      TOKEN: from X, to Y, at level L, side S, good for N ticks. The receiving
      strategy's entry check consults it; with a live grant naming it, the slot
      rule yields for that strategy only. Every other bar the receiver has
      still applies — the grant answers the slot question and nothing else.
      Grants expire on their own; expiry with no fire is recorded as a finding.
      N (`HANDOFF_TTL_TICKS`, 8 ≈ two minutes) is a declared prior.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import config

logger = logging.getLogger(__name__)

HANDOFF_TTL_TICKS = int(config.HANDOFF_TTL_TICKS)

_GRANTS: list = []          # dicts: from, to, level, side, tick_issued, ttl, fired, expired
_TICK = {"n": 0}


def tick():
    """Called once per main-loop tick; ages every grant and records expiries."""
    _TICK["n"] += 1
    for g in _GRANTS:
        if not g["fired"] and not g["expired"] and _TICK["n"] - g["tick_issued"] > g["ttl"]:
            g["expired"] = True
            logger.info("[handoff] grant %s→%s at %.2f EXPIRED unfired after %d ticks",
                        g["from"], g["to"], g["level"], g["ttl"])


def grant(from_strategy: str, to_strategy: str, level: float, side: str,
          ttl: int = HANDOFF_TTL_TICKS, why: str = "") -> dict:
    g = {"from": from_strategy, "to": to_strategy, "level": float(level), "side": side,
         "tick_issued": _TICK["n"], "ttl": int(ttl), "fired": False, "expired": False,
         "why": why, "ts": time.time()}
    _GRANTS.append(g)
    del _GRANTS[:-50]
    logger.info("[handoff] %s → %s at %.2f (%s), %d ticks: %s", from_strategy, to_strategy,
                level, side, ttl, why)
    return g


def live(to_strategy: str) -> Optional[dict]:
    """The most recent live grant naming `to_strategy`, else None."""
    for g in reversed(_GRANTS):
        if g["to"] == to_strategy and not g["fired"] and not g["expired"]:
            return g
    return None


def age(g: dict) -> int:
    return _TICK["n"] - g["tick_issued"]


def consume(g: dict) -> None:
    g["fired"] = True
    g["fired_tick"] = _TICK["n"]
    logger.info("[handoff] grant %s→%s at %.2f FIRED on tick %d of %d",
                g["from"], g["to"], g["level"], age(g), g["ttl"])


def reset() -> None:
    _GRANTS.clear()
    _TICK["n"] = 0
