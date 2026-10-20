import os, sys
os.environ["PROP_OOS"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
import numpy as np, pandas as pd
from research.prop import harness as H
df = pd.read_csv("data/search/de40-m30.csv", parse_dates=["time"])
df["rng"]=df.high-df.low
df["flat"]=df.rng<3
t=pd.DatetimeIndex(df.time)
q=df[(t.hour>=10)&(t.hour<18)]
print(q.groupby(q.time.dt.to_period("Q")).flat.mean().round(3).to_string())
