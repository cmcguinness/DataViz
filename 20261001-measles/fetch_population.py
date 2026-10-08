"""Download Census Vintage 2025 state population estimates and extract 50 states + DC.

Output: data/census_state_pop_2025.csv (Location, pop2025), population as of July 1, 2025.
"""

import ssl
from io import StringIO
from pathlib import Path
from urllib.request import urlopen

import certifi
import pandas as pd

URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2025/state/totals/NST-EST2025-ALLDATA.csv"
)
OUT = Path(__file__).parent / "data" / "census_state_pop_2025.csv"


def main() -> None:
    # python.org builds of Python don't use the macOS keychain; use certifi's CA bundle.
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urlopen(URL, timeout=60, context=ctx) as resp:
        raw = resp.read().decode("latin-1")
    df = pd.read_csv(StringIO(raw))
    # SUMLEV 40 = state-level rows (includes DC and Puerto Rico).
    states = df[(df["SUMLEV"] == 40) & (df["NAME"] != "Puerto Rico")]
    out = states[["NAME", "POPESTIMATE2025"]].rename(
        columns={"NAME": "Location", "POPESTIMATE2025": "pop2025"}
    )
    if len(out) != 51:
        raise ValueError(f"Expected 51 rows (50 states + DC), got {len(out)}")
    OUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"Wrote {OUT}: {len(out)} rows, total population {out['pop2025'].sum():,}")


if __name__ == "__main__":
    main()
