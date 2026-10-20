import sys
import pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120)
from research.search.mean_reversion.analyze import load
d = load(sys.argv[1], {'USTEC': 18})
syms = sys.argv[2].split(',')
d = d[d.symbol.isin(syms)]
p = d.pivot_table(index='key', columns='symbol', values='est')
n = d.pivot_table(index='key', columns='symbol', values='n')
p['min'] = p[syms].min(axis=1); p['mean'] = p[syms].mean(axis=1); p['nmin'] = n.min(axis=1)
p = p[p.nmin >= (int(sys.argv[3]) if len(sys.argv) > 3 else 40)]
for tf in sorted(d.tf.unique()):
    q = p[p.index.str.contains('|' + tf + '|', regex=False)]
    print(tf, len(q)); print(q.sort_values('min', ascending=False).head(15).round(1).to_string())
