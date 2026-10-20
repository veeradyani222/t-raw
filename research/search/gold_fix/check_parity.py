"""Parity: our vectorised BOS == bos_backtest.make_bos_signal on IS M30 gold."""
import time
from research.prop import harness as H
from research.search.gold_fix import strategies as S
import bos_backtest as B
df = H.load("XAUUSD", "M30", split="is")
ours = S.build_bos(df)
ref = B.make_bos_signal(df, trend_ma=200)
mism = 0; cnt = 0
for i in range(len(df)):
    a, b = ours[i], ref(df, i)
    if (a is None) != (b is None):
        mism += 1; continue
    if a is not None:
        cnt += 1
        if a.side != b.side or abs(a.sl - b.sl) > 1e-9 or abs(a.tp - b.tp) > 1e-9:
            mism += 1
print("signals", cnt, "mismatch", mism)
