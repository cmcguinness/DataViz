"""Per-100k measles rate choropleth, 2026 YTD, colored relative to the national rate.

Inputs:
  data/MeaslesCasesMap.csv        CDC measles cases by state (2024-2026), as of Oct 1, 2026
  data/census_state_pop_2025.csv  Census Vintage 2025 state population estimates (July 1, 2025),
                                  produced by fetch_population.py

Output:
  measles_rate_map_2026.png
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "measles_rate_map_2026.png"

YEAR = "2026"

# Bins are multiples of the national rate on a doubling scale; zero cases gets its own class.
# ColorBrewer RdBu, 8 classes (dark blue -> dark red).
BINS = [
    # (label, lower ratio inclusive, upper ratio exclusive, color)
    ("No cases", None, None, "#2166ac"),
    ("Under ¼×", 0, 0.25, "#4393c3"),
    ("¼–½×", 0.25, 0.5, "#92c5de"),
    ("½–1×", 0.5, 1, "#d1e5f0"),
    ("1–2×", 1, 2, "#fddbc7"),
    ("2–4×", 2, 4, "#f4a582"),
    ("4–8×", 4, 8, "#d6604d"),
    ("8× or more", 8, np.inf, "#b2182b"),
]

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}


def load() -> tuple[pd.DataFrame, float]:
    cases = pd.read_csv(DATA / "MeaslesCasesMap.csv", encoding="utf-8-sig")
    # CDC reports New York City separately from the rest of New York State; Census does not.
    cases["Location"] = cases["Location"].replace({"New York City": "New York"})
    cases = cases.groupby("Location", as_index=False)[YEAR].sum()
    pop = pd.read_csv(DATA / "census_state_pop_2025.csv")
    df = cases[["Location", YEAR]].rename(columns={YEAR: "cases"}).merge(
        pop, on="Location", how="outer", validate="one_to_one", indicator=True
    )
    unmatched = df[df["_merge"] != "both"]
    if not unmatched.empty:
        raise ValueError(f"States not matched between cases and population:\n{unmatched}")
    df = df.drop(columns="_merge")
    df["abbr"] = df["Location"].map(STATE_ABBR)
    df["rate"] = df["cases"] / df["pop2025"] * 100_000
    national = df["cases"].sum() / df["pop2025"].sum() * 100_000
    df["ratio"] = df["rate"] / national
    df["bin"] = df.apply(classify, axis=1)
    return df, national


def classify(row) -> int:
    if row["cases"] == 0:
        return 0
    for i, (_, lo, hi, _) in enumerate(BINS[1:], start=1):
        if lo <= row["ratio"] < hi:
            return i
    raise ValueError(f"Unbinned ratio {row['ratio']} for {row['Location']}")


def fmt_rate(r: float) -> str:
    return f"{r:.1f}" if r >= 1 else f"{r:.2f}"


def build_figure(df: pd.DataFrame, national: float) -> go.Figure:
    n = len(BINS)
    # Discrete colorscale: each bin index maps to a flat band.
    colorscale = []
    for i, (_, _, _, color) in enumerate(BINS):
        colorscale += [(i / n, color), ((i + 1) / n, color)]

    fig = go.Figure(
        go.Choropleth(
            locations=df["abbr"],
            locationmode="USA-states",
            z=df["bin"] + 0.5,
            zmin=0,
            zmax=n,
            colorscale=colorscale,
            showscale=False,
            marker_line_color="white",
            marker_line_width=1,
        )
    )

    # Legend as manual swatches on the right, with per-100k ranges alongside the multiples.
    counts = df["bin"].value_counts()
    x0, y_top, step = 0.80, 0.78, 0.075
    for i, (label, lo, hi, color) in reversed(list(enumerate(BINS))):
        y = y_top - (n - 1 - i) * step
        if lo is None:
            rng = "0"
        elif np.isinf(hi):
            rng = f"{fmt_rate(lo * national)}+"
        elif lo == 0:
            rng = f"under {fmt_rate(hi * national)}"
        else:
            rng = f"{fmt_rate(lo * national)}–{fmt_rate(hi * national)}"
        fig.add_shape(
            type="rect", xref="paper", yref="paper",
            x0=x0, x1=x0 + 0.03, y0=y - 0.025, y1=y + 0.025,
            fillcolor=color, line=dict(color="#c3c2b7", width=0.5),
        )
        fig.add_annotation(
            xref="paper", yref="paper", x=x0 + 0.04, y=y, xanchor="left", showarrow=False,
            text=f"<b>{label}</b>  <span style='color:#52514e'>{rng}</span>"
            f"  <span style='color:#898781'>({counts.get(i, 0)})</span>",
            font=dict(size=13, color="#0b0b0b"),
        )
    fig.add_annotation(
        xref="paper", yref="paper", x=x0, y=y_top + 0.06, xanchor="left", showarrow=False,
        text="<b>Rate vs. national</b>  <span style='color:#52514e'>per 100k</span>"
        "  <span style='color:#898781'>(states + DC)</span>",
        font=dict(size=14, color="#0b0b0b"),
    )

    # Direct labels on the states that are 4x the national rate or more.
    hot = df[df["bin"] >= 6].sort_values("rate", ascending=False)
    fig.add_trace(
        go.Scattergeo(
            locations=hot["abbr"],
            locationmode="USA-states",
            text=[f"<b>{a}</b><br>{r:.1f}" for a, r in zip(hot["abbr"], hot["rate"])],
            mode="text",
            textfont=dict(size=12, color=["white" if b == 7 else "#0b0b0b" for b in hot["bin"]]),
            hoverinfo="skip",
        )
    )

    total = int(df["cases"].sum())
    fig.update_layout(
        width=1400,
        height=760,
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=100, b=50),
        geo=dict(
            scope="usa",
            projection_type="albers usa",
            bgcolor="white",
            showland=False,
            showlakes=False,
            domain=dict(x=[0, 0.78], y=[0, 1]),
        ),
        title=dict(
            text=(
                "<b>Measles rates are far above the national average in a handful of states</b>"
                f"<br><span style='font-size:16px;color:#52514e'>Confirmed cases per 100,000 residents, "
                f"2026 through Oct. 1. National rate: <b>{national:.2f}</b> per 100k "
                f"({total:,} cases). Blue is below the national rate, red is above.</span>"
            ),
            x=0.02, xanchor="left", y=0.96,
            font=dict(size=24, color="#0b0b0b"),
        ),
        font=dict(family="Helvetica Neue, Helvetica, Arial, sans-serif"),
    )
    fig.add_annotation(
        xref="paper", yref="paper", x=0.0, y=-0.05, xanchor="left", showarrow=False,
        text="Sources: CDC, Measles cases and outbreaks (as of Oct. 1, 2026); "
        "U.S. Census Bureau, Vintage 2025 state population estimates. "
        "Labeled states are at least 4× the national rate. Small states can swing widely on a few cases.",
        font=dict(size=11, color="#898781"),
    )
    return fig


def main() -> None:
    df, national = load()
    print(f"National rate: {national:.3f} per 100k")
    print(
        df.sort_values("rate", ascending=False)[["Location", "cases", "pop2025", "rate", "ratio", "bin"]]
        .to_string(index=False, float_format=lambda v: f"{v:.2f}")
    )
    fig = build_figure(df, national)
    fig.write_image(OUT, scale=2)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
