#!/usr/bin/env python3
"""
Wave Surf Pump — LONG Trader v5
=================================
Self-contained scanner + position management. Shares signals with SHORT bot.
Uses shared lib/ modules.
"""
import json, time, sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

# Ensure scripts/ is importable
sys.path.insert(0, str(PROJECT_DIR))
from scripts.lib import api as _api
from scripts.lib import mood as _mood
from scripts.lib import scanner as _scanner
from scripts.lib import signals as _signals
from scripts.lib import trader_core as _core

MIN_SCORE_TO_TRADE = 50


def execute():
    state_path = DATA_DIR / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    result = {}

    # BTC mood
    btc_mood = _mood.check(bot_type="long")
    result["btc_mood"] = btc_mood

    # Scanner
    fresh_candidates = _scanner.run_long_scanner(100)
    fresh_candidates = _core.apply_btc_penalty(fresh_candidates, btc_mood)

    scan_output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidates": fresh_candidates,
        "scanned_count": 100,
        "strategy": "v5_long",
        "btc_mood": btc_mood,
    }
    (DATA_DIR / "scan_latest.json").write_text(json.dumps(scan_output, indent=2))
    result["scan_top3"] = [c["symbol"] for c in fresh_candidates[:3]]
    result["scan_top_scores"] = [c["score"] for c in fresh_candidates[:3]]

    # BTC crash → force close position
    if state.get("active_position") and btc_mood.get("hard_block"):
        ap = state["active_position"]
        prices = _api.get_spread_prices(ap["symbol"])
        if prices:
            pnl_pct, _ = _core.compute_pnl_long(ap, prices)
            pc = {"action": "exit", "reason": "btc_mood_crash", "bid": prices["bid"],
                  "ask": prices["ask"], "mid": prices["mid"], "pnl_pct": round(pnl_pct, 2)}
            close_result = _core.close_position(state, pc, DATA_DIR, exit_side="bid")
            result.update(close_result)
            result["position_check"] = pc

    # Check current position
    if state.get("active_position"):
        pos_check, switch_target = _core.check_position_long(state, fresh_candidates)
        result["position_check"] = pos_check

        if pos_check["action"] == "exit":
            close_result = _core.close_position(state, pos_check, DATA_DIR, exit_side="bid")
            result.update(close_result)
            if switch_target:
                entry_info = _core.open_position_long(state, switch_target)
                result["switch_entered"] = entry_info
        else:
            state["active_position"]["highest_price"] = max(
                state["active_position"].get("highest_price", state["active_position"]["entry_price"]),
                pos_check.get("mid", 0))

    # Enter new position (no active position)
    if not state.get("active_position"):
        if fresh_candidates and fresh_candidates[0]["score"] >= MIN_SCORE_TO_TRADE:
            entry_info = _core.open_position_long(state, fresh_candidates[0])
            result["entered"] = entry_info
            result["entry_reason"] = f"new_signal_{fresh_candidates[0]['score']}"
        else:
            result["evaluation"] = {"action": "skip",
                "reason": f"no_candidate_above_{MIN_SCORE_TO_TRADE}" if fresh_candidates else "no_candidates"}

    # Write shared signals for SHORT bot
    pos_check = result.get("position_check")
    _signals.write_long_signals(state, pos_check, fresh_candidates)

    # Save
    state_path.write_text(json.dumps(state, indent=2))
    print(json.dumps(result, indent=2))
    (DATA_DIR / "trade_latest.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    execute()
