"""K-02 — the market-anchored prior, and why its weight is blank.

The brief: *blend the model line with the closing line, weight by measured out-of-sample
log-loss.* Two things are needed for that and only one of them exists:

* **the model's out-of-sample log-loss** — measured, twice, on two independent samples
  (167 walk-forward games and 14 settled sealed games). Both numbers are published below
  with the file they come from.
* **the market's out-of-sample log-loss** — not measured, because no closing line exists in
  any committed capture. Requirement R-043 and R-101 have been blocked on this since the
  first session; the v4 capture index records it as ``F-V4-04``.

So the weight is a blank with a reason, and what is published instead is the **rule** that
will compute it and the **sensitivity grid** showing what the rule returns for every
plausible market log-loss. The grid is arithmetic on a stated formula over a stated input
range — it is not a measurement, and every cell says so.

The rule (pre-registered here so it cannot be fitted to a result later)
---------------------------------------------------------------------
Both forecasters are scored against the same coin-flip baseline ``L0 = ln 2 = 0.6931`` nats,
which is the log-loss of calling every binary outcome 50/50. Skill against that baseline is
``s = L0 − L``, floored at zero (a forecaster worse than a coin flip gets no weight, it does
not get negative weight). The blend weight is the skill share::

    w_market = max(0, s_market) / (max(0, s_model) + max(0, s_market))
    blended_margin = (1 − w_market) · model_margin + w_market · market_margin

It is monotone in each forecaster's measured skill, it is 0 when the market has no measured
skill, and it is undefined — blank, never 0.5 — when the market has not been scored at all.
"""

from __future__ import annotations

import json
import math

from .common import DATA, maybe_load

BACKTEST = DATA / "v2" / "backtest.json"
SETTLED_ALL = DATA / "v4" / "settlement" / "settled-all.json"

L0 = math.log(2.0)          # 0.6931… — a coin flip on a binary outcome
BLOCKED_REASON = ("no closing line exists in any committed capture — requirement R-043 / "
                  "R-101, flagged F-V4-04 in the v4 capture index")

# Hypothetical market log-losses, in nats, over the range a liquid NBA closing line has been
# reported to occupy. These are grid points of a stated function, not measurements.
GRID = [0.6931, 0.6800, 0.6700, 0.6600, 0.6500, 0.6400, 0.6300, 0.6200, 0.6100,
        0.6000, 0.5900, 0.5800, 0.5600, 0.5400, 0.5200, 0.5000]


def weight(l_model: float, l_market: float) -> float | None:
    """The pre-registered skill-share weight. ``None`` when either input is unmeasured."""
    if l_model is None or l_market is None:
        return None
    s_model = max(0.0, L0 - float(l_model))
    s_market = max(0.0, L0 - float(l_market))
    if s_model + s_market <= 0:
        return None
    return s_market / (s_model + s_market)


def measurements() -> list[dict]:
    """Every out-of-sample log-loss this repository has actually measured."""
    out = []
    b = maybe_load(BACKTEST)
    if b:
        h = b.get("headline") or {}
        m = b.get("meta") or {}
        out.append({
            "id": "BT-167",
            "sample": "walk-forward backtest, official history",
            "n_games": m.get("n_games_scored"),
            "window": f"{m.get('first_date')} → {m.get('last_date')}",
            "log_loss": h.get("log_loss"),
            "log_loss_baseline": h.get("log_loss_baseline"),
            "skill_vs_baseline": (round(h["log_loss_baseline"] - h["log_loss"], 4)
                                  if h.get("log_loss") is not None
                                  and h.get("log_loss_baseline") is not None else None),
            "leakage_rule": m.get("leakage_rule"),
            "brier": h.get("brier"), "brier_baseline": h.get("brier_baseline"),
            "auroc": h.get("auroc"),
            "calibration_read": h.get("calibration_read"),
            "source_file": "data/v2/backtest.json",
            "source_url": "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v2/backtest.json",
            "official_source": m.get("source"),
        })
    s = maybe_load(SETTLED_ALL)
    if s:
        st = s.get("settlement") or {}
        out.append({
            "id": "SETTLED-14",
            "sample": "sealed ledgers settled against official finals",
            "n_games": st.get("n_distinct_games_graded"),
            "window": f"through {st.get('latest_graded_game_date')}",
            "log_loss": st.get("distinct_log_loss_model"),
            "log_loss_baseline": st.get("distinct_log_loss_coin"),
            "skill_vs_baseline": (round(st["distinct_log_loss_coin"]
                                        - st["distinct_log_loss_model"], 4)
                                  if st.get("distinct_log_loss_model") is not None
                                  and st.get("distinct_log_loss_coin") is not None else None),
            "leakage_rule": ("predictions were sealed (sha256) before tip and verified "
                             "unmodified at settlement"),
            "brier": None, "brier_baseline": None, "auroc": None,
            "calibration_read": st.get("luck_statement"),
            "source_file": "data/v4/settlement/settled-all.json",
            "source_url": "https://github.com/wingbangboozle1-lang/NBA2/blob/main/data/v4/settlement/settled-all.json",
            "official_source": "https://www.nba.com/games",
        })
    return out


def build() -> dict:
    ms = measurements()
    # The model's number is the smaller-sample, sealed-ledger measurement when it exists
    # (it is the one that cannot have been fitted after the fact), else the backtest.
    sealed = next((m for m in ms if m["id"] == "SETTLED-14"), None)
    primary = sealed or (ms[0] if ms else None)
    l_model = primary["log_loss"] if primary else None

    grid = []
    for lm in GRID:
        grid.append({
            "hypothetical_market_log_loss": lm,
            "market_skill_vs_coin": round(L0 - lm, 4),
            "w_market": weight(l_model, lm),
            "w_model": (round(1 - weight(l_model, lm), 4)
                        if weight(l_model, lm) is not None else None),
        })

    # A worked example needs two numbers; only one exists, so the example is published as a
    # template with the market side explicitly blank rather than filled with a plausible price.
    return {
        "schema": "nba2.v6.market-prior.v1",
        "session": "arena/f5ac4e74-nba2",
        "rule": ("w_market = max(0, L0 − L_market) / (max(0, L0 − L_model) + "
                 "max(0, L0 − L_market)); blended = (1 − w_market)·model + w_market·market"),
        "baseline_l0": round(L0, 4),
        "primary_measurement_id": primary["id"] if primary else None,
        "model_log_loss": l_model,
        "market_log_loss": None,
        "market_log_loss_reason": BLOCKED_REASON,
        "w_market": None,
        "w_market_reason": (f"undefined until a closing line is captured and scored "
                            f"out-of-sample — {BLOCKED_REASON}"),
        "blended_margin_published": False,
        "blended_margin_reason": ("a blend needs a market number; with no closing line the "
                                  "blend would be the model number wearing a market label"),
        "measurements": ms,
        "sensitivity_grid": grid,
        "grid_note": ("Every row is the pre-registered rule evaluated at a hypothetical "
                      "market log-loss. It is arithmetic on the stated formula, not a "
                      "measurement: no market log-loss has been observed, because no "
                      "closing price exists in any committed capture."),
        "what_would_unblock_it": [
            "A licensed odds feed capturing the closing spread, total and moneyline per game "
            "with a stated timestamp policy (R-101).",
            "A decision on storage and display terms for those prices (open question on the "
            "Decisions needed page).",
            "At least one full out-of-sample window of market log-loss scored on the same "
            "games as the model, so the two numbers are comparable.",
        ],
    }
