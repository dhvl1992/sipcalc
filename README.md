# sipcalc

Monthly ETF SIP splitter, holdings tracker and risk check. Live at `dhvl1992.github.io/sipcalc/`.

- **This month** – split the SIP by target %, or "Fill the gaps" (new money goes to what is below target, nothing sold).
- **Holdings** – qty + avg price per ETF, value, gain/loss, mix vs target, drift warnings. Saved only on your phone (use Save backup).
- **Risk** – 10,000 possible futures for the next 1 / 3 / 6 months, built from real past days (5-day blocks). Bad case, very bad case, chance of a loss, worst real past stretch, 2020-crash replay, and which ETF the risk comes from.

## Market data
`.github/workflows/update-data.yml` runs `scripts/update_data.py` every weekday at 18:47 IST and commits `data/market.json`
(latest prices + cleaned daily returns since 2011). Run it by hand: **Actions → Update market data → Run workflow**.
