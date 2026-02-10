"""
Core alerting logic.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from alerts import send_alert
from config import (
    INDEX_SYMBOL,
    LEVELS,
    STATE_FILE,
    VIX_SYMBOL,
    DEPLOYMENT_PLAN,
)
from data import fetch_data, get_latest_close
from state import load_state, save_state


# =====================
# HELPERS
# =====================
def _close_series(data) -> pd.Series:
    close = data["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close


def consecutive_closes_below(data, threshold: float, days: int) -> bool:
    if days <= 0:
        return False

    closes = _close_series(data).iloc[-days:]
    if len(closes) < days:
        return False

    return all(c <= threshold for c in closes)


def format_action(level: int) -> str:
    plan = DEPLOYMENT_PLAN.get(level)

    if not plan:
        return "➡️ Execute your pre-defined deployment plan."

    lines = [
        f"Suggested action: {plan['title']}",
        plan["action"],
    ]

    if plan.get("allocation"):
        lines.append(f"Allocation hint: {plan['allocation']}")

    return "➡️ " + "\n➡️ ".join(lines)


# =====================
# CORE LOGIC
# =====================
def run_alerts(
    *,
    test_mode: bool = False,
    forced_drawdown: float | None = None,
    force_confirm: bool = False,
    state_file: str = STATE_FILE,
) -> None:
    # If the market recovers to better than this drawdown (e.g. -2%),
    # we clear all previously triggered levels so they can fire again
    # on a future drawdown cycle.
    RESET_THRESHOLD = -3  # percent
    VIX_CONFIRMATION_THRESHOLD = 20.0
    # Persistence confirmation by level (days below threshold).
    # 5% is intentional noise zone, so no persistence requirement.
    PERSISTENCE_DAYS = {
        5: 0,
        10: 1,
        15: 2,
        20: 0,
    }

    # ---- Load state FIRST ----
    # This tells us which levels have already fired so we don't
    # spam duplicate alerts for the same drawdown episode.
    state: Dict[str, Any] = load_state(state_file)

    # ---- Fetch latest prices ----
    # Wrap in a small guard so transient data issues just cause a no-op,
    # rather than crashing the whole script / cron job.
    try:
        index_price = get_latest_close(INDEX_SYMBOL)
        vix_price = get_latest_close(VIX_SYMBOL)
    except Exception:
        # In production you might want to log this instead.
        return

    # ---- Fetch data once per required period ----
    # Each level may share the same period (e.g. 3mo, 6mo).
    # Pre-fetch into a map so multiple levels don't redundantly
    # hit yfinance for the same period.
    unique_periods = set(LEVELS.values())
    data_map = {
        period: fetch_data(INDEX_SYMBOL, period)
        for period in unique_periods
    }

    # ---- Reset logic ----
    # Use the smallest level's lookback as the "cycle reset" reference.
    # If price has recovered close to its recent peak, we allow all levels
    # to trigger again in the next drawdown cycle.
    reset_level = min(LEVELS)
    reset_period = LEVELS[reset_level]
    reset_data = data_map.get(reset_period)

    if reset_data is not None and not reset_data.empty:
        reset_close = _close_series(reset_data)
        reset_peak = float(reset_close.max())
        if reset_peak > 0:
            reset_drawdown = (index_price - reset_peak) / reset_peak * 100
            if forced_drawdown is not None:
                reset_drawdown = forced_drawdown

            if reset_drawdown > RESET_THRESHOLD and state:
                print("Market recovered. Resetting alert state.")
                state.clear()
                save_state(state, state_file)

    # ---- Evaluate levels ----
    for level, period in LEVELS.items():
        level_key = str(level)

        # Already triggered in this cycle – skip.
        if level_key in state:
            continue

        data = data_map.get(period)
        if data is None or data.empty:
            continue

        close = _close_series(data)
        peak = float(close.max())
        if peak <= 0:
            continue

        # Reference line is level-specific rolling peak based on lookback period.
        drawdown = (index_price - peak) / peak * 100
        if forced_drawdown is not None:
            drawdown = forced_drawdown

        # Drawdown isn't deep enough for this threshold.
        if drawdown > -level:
            continue

        threshold = peak * (1 - level / 100)

        # -------- Investor-grade confirmation --------
        # Rule: persistence OR high-VIX stress.
        persistence_days = PERSISTENCE_DAYS.get(level, 0)
        persistence_confirmed = (
            True
            if persistence_days == 0
            else consecutive_closes_below(data, threshold, persistence_days)
        )
        vix_confirmed = vix_price >= VIX_CONFIRMATION_THRESHOLD

        if force_confirm:
            confirmed = True
        else:
            confirmed = persistence_confirmed or vix_confirmed
        # --------------------------------------------

        if not confirmed:
            continue

        emoji = {5: "🟡", 10: "🟠", 15: "🔴", 20: "🔥"}[level]
        prefix = "[TEST] " if test_mode else ""
        action_text = format_action(level)

        # Human-friendly interpretation for each zone to nudge the right behaviour.
        zone_text = {
            5: "Mild correction zone. Usually no need for action beyond SIPs.",
            10: "Healthy correction. Good time to start deploying long-term money.",
            15: "Deep correction. Attractive zone for meaningful deployment.",
            20: "Panic zone. Historically rare levels – act according to plan, not emotions.",
        }[level]

        # Approximate index drop from period-specific peak in points (for intuition)
        points_down = peak - index_price
        persistence_text = (
            "N/A (instant trigger at this level)"
            if persistence_days == 0
            else f"{persistence_days} day(s) below threshold"
        )
        confirmation_text = (
            "PERSISTENCE + HIGH VIX"
            if persistence_confirmed and vix_confirmed
            else "PERSISTENCE"
            if persistence_confirmed
            else "HIGH VIX"
        )

        msg = (
            f"{prefix}{emoji} MARKET OPPORTUNITY ALERT {emoji}\n\n"
            f"Index: {INDEX_SYMBOL}\n"
            f"Current price: {index_price:.2f}\n"
            f"Reference period: {period}\n"
            f"Rolling peak ({period}): {peak:.2f}\n"
            f"Correction: {drawdown:.2f}% (~{points_down:.0f} points below peak)\n"
            f"Level hit: {level}% drawdown\n"
            f"India VIX: {vix_price:.2f}\n\n"
            "Trigger logic:\n"
            f"- Threshold price: {threshold:.2f}\n"
            f"- Persistence rule: {persistence_text}\n"
            f"- VIX override: VIX >= {VIX_CONFIRMATION_THRESHOLD:.0f}\n"
            f"- Confirmed by: {confirmation_text}\n\n"
            f"{zone_text}\n\n"
            f"{action_text}\n\n"
            "Checklist before acting:\n"
            "- Are you following your pre-decided asset allocation?\n"
            "- Is your emergency fund and short-term cash fully safe?\n"
            "- Are you comfortable staying invested for 5+ years?\n"
        )

        send_alert(msg)

        state[level_key] = {
            "triggered_at_price": round(index_price, 2),
            "drawdown": round(drawdown, 2),
            "reference_period": period,
            "reference_peak": round(peak, 2),
            "threshold_price": round(threshold, 2),
            "vix": round(vix_price, 2),
            "confirmed_by": confirmation_text,
        }

    save_state(state, state_file)
