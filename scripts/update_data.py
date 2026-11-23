"""
Builds data/market.json for the SIP calculator page.
Runs every weekday evening on GitHub Actions (see .github/workflows/update-data.yml).

What it writes:
  prices  : latest real traded price of each ETF (what your broker shows)
  returns : daily log returns since 2011 (cleaned), used by the Monte Carlo risk check

Cleaning (same rules as our Colab tests):
  - a one-day move bigger than 35% is an unadjusted split -> set to 0
  - EBBETF0433 listed in 2022: before that use EBBETF0430's moves; before any bond ETF, a steady 7%/yr
"""
import json, os, sys, time, datetime as dt
import numpy as np
import pandas as pd
import yfinance as yf

RISK_ETFS  = ["NIFTYBEES", "JUNIORBEES", "MON100", "GOLDBEES", "EBBETF0433"]
PRICE_ONLY = ["LIQUIDBEES"]                 # price is flat ~1000 on Yahoo (pays in units) -> no risk history
BOND_PROXY = "EBBETF0430"
START      = "2011-04-01"                   # MON100 starts in 2011
MAX_DAY    = 0.35
BOND_YIELD = 0.07
SCALE      = 100_000                        # store log returns as integers (x 100000) to keep the file small
OUT        = "data/market.json"

ns = lambda t: t + ".NS"
tickers = [ns(t) for t in RISK_ETFS + PRICE_ONLY + [BOND_PROXY]]

# ---- 1. Download (Yahoo sometimes refuses; retry a few times) ----
raw = None
for attempt in range(1, 5):
    try:
        raw = yf.download(tickers, start=START, auto_adjust=False, progress=False, threads=False)
        if raw is not None and not raw.empty and raw["Close"][ns("NIFTYBEES")].notna().sum() > 1000:
            break
        print(f"attempt {attempt}: got too little data")
    except Exception as e:
        print(f"attempt {attempt}: {e}")
    time.sleep(30 * attempt)
else:
    sys.exit("Download failed. Old market.json is kept.")

close = raw["Close"]          # real traded price  -> holdings value
adj   = raw["Adj Close"]      # includes dividends -> risk

# ---- 2. Latest prices ----
prices = {}
for t in RISK_ETFS + PRICE_ONLY:
    s = close[ns(t)].dropna()
    if len(s):
        prices[t] = {"close": round(float(s.iloc[-1]), 2), "date": s.index[-1].strftime("%Y-%m-%d")}
    else:
        print(f"WARNING: no price for {t}")

# ---- 3. Clean daily returns ----
notes = []
r = adj.pct_change(fill_method=None)
bad = r.abs() > MAX_DAY
for t in r.columns:
    for d in r.index[bad[t]]:
        notes.append(f"{t.replace('.NS','')} {r.at[d, t]:+.0%} on {d.date()} treated as split, set to 0")
r = r.mask(bad, 0.0)

R = r[[ns(t) for t in RISK_ETFS]].copy()
bond = ns("EBBETF0433")
gap = R[bond].isna()
if ns(BOND_PROXY) in r:
    R.loc[gap, bond] = r.loc[gap, ns(BOND_PROXY)]
    notes.append(f"EBBETF0433: {int((gap & R[bond].notna()).sum())} early days use {BOND_PROXY} moves")
still = R[bond].isna()
R.loc[still, bond] = (1 + BOND_YIELD) ** (1 / 252) - 1
notes.append(f"EBBETF0433: {int(still.sum())} days before any bond ETF set to steady {BOND_YIELD:.0%}/yr (risk understated)")

R = R.iloc[1:]
first_full = R.notna().all(axis=1).idxmax()          # first day every ETF has data
R = R.loc[first_full:].fillna(0.0)
LR = np.log1p(R)

# ---- 4. Write ----
out = {
    "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "prices": prices,
    "returns": {
        "assets": RISK_ETFS,
        "scale": SCALE,
        "dates": [int(d.strftime("%Y%m%d")) for d in LR.index],
        "lr": {t: [int(round(x * SCALE)) for x in LR[ns(t)].values] for t in RISK_ETFS},
    },
    "notes": notes,
}
# Backup runs: if nothing but the timestamp changed, leave the file alone (no empty commits)
try:
    old = json.load(open(OUT))
    if {k: v for k, v in old.items() if k != "updated"} == {k: v for k, v in out.items() if k != "updated"}:
        print("No new data since last run. Nothing written.")
        sys.exit(0)
except (FileNotFoundError, ValueError):
    pass

os.makedirs(os.path.dirname(OUT), exist_ok=True)   # git does not keep empty folders
with open(OUT, "w") as f:
    json.dump(out, f, separators=(",", ":"))

print(f"wrote {OUT}: {len(LR)} days {LR.index[0].date()} -> {LR.index[-1].date()}")
for n in notes:
    print("  NOTE:", n)
for t, p in prices.items():
    print(f"  {t:11} {p['close']:>10} ({p['date']})")
