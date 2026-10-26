"""Lightweight demand forecasting (decision support only).

For each blood group we take the monthly requested units of the last
`WINDOW` complete months, fit a straight line with scikit-learn and predict
the next period. The prediction is compared with the recent average and with
current stock to produce a recommendation."""

from datetime import date
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .services import BLOOD_GROUPS

WINDOW = 6
RISE_THRESHOLD_PCT = 15.0


def previous_months(n: int, today: date = None) -> List[str]:
    """The last n COMPLETE months as 'YYYY-MM', oldest first."""
    today = today or date.today()
    y, m = today.year, today.month
    labels = []
    for _ in range(n):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        labels.append(f"{y:04d}-{m:02d}")
    return labels[::-1]


def forecast_demand(
    rows: List[Tuple[str, str, int]],
    stock_by_group: Dict[str, int],
    today: date = None,
) -> List[dict]:
    """rows: (blood_group, 'YYYY-MM', units_requested)."""
    months = previous_months(WINDOW, today)
    df = pd.DataFrame(rows, columns=["blood_group", "month", "units"])
    if df.empty:
        pivot = pd.DataFrame(0, index=months, columns=BLOOD_GROUPS)
    else:
        pivot = (
            df.pivot_table(index="month", columns="blood_group", values="units", aggfunc="sum")
            .reindex(index=months, columns=BLOOD_GROUPS)
            .fillna(0)
        )

    out = []
    x = np.arange(len(months)).reshape(-1, 1)
    for group in BLOOD_GROUPS:
        y = pivot[group].to_numpy(dtype=float)
        history = [int(v) for v in y]
        stock = int(stock_by_group.get(group, 0))
        if np.count_nonzero(y) < 3:
            out.append(
                {
                    "blood_group": group,
                    "history": history,
                    "predicted_units": 0.0,
                    "baseline_units": round(float(y[-3:].mean()), 1),
                    "change_pct": None,
                    "trend": "insufficient data",
                    "current_stock": stock,
                    "shortage_risk": False,
                    "recommendation": "Not enough request history to forecast.",
                }
            )
            continue

        model = LinearRegression().fit(x, y)
        predicted = max(0.0, float(model.predict([[len(months)]])[0]))
        baseline = float(y[-3:].mean())
        change = ((predicted - baseline) / baseline * 100.0) if baseline > 0 else None

        if change is not None and change >= RISE_THRESHOLD_PCT:
            trend = "rising"
        elif change is not None and change <= -RISE_THRESHOLD_PCT:
            trend = "falling"
        else:
            trend = "stable"

        shortage = predicted > stock
        if shortage and trend == "rising":
            rec = (
                f"Demand for {group} is rising (~{change:.0f}% above the recent average) and "
                f"forecast demand ({predicted:.0f} units) exceeds current stock ({stock}). "
                "Increase donor outreach for this blood group."
            )
        elif shortage:
            rec = (
                f"Forecast demand ({predicted:.0f} units) exceeds current stock ({stock}). "
                "Consider a donation campaign."
            )
        elif trend == "rising":
            rec = f"Demand is rising (~{change:.0f}%), but stock currently covers it. Keep monitoring."
        else:
            rec = "Demand and stock look balanced."

        out.append(
            {
                "blood_group": group,
                "history": history,
                "predicted_units": round(predicted, 1),
                "baseline_units": round(baseline, 1),
                "change_pct": None if change is None else round(change, 1),
                "trend": trend,
                "current_stock": stock,
                "shortage_risk": bool(shortage),
                "recommendation": rec,
            }
        )

    out.sort(key=lambda r: r["predicted_units"], reverse=True)
    return out
