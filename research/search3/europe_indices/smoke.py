import sys, time
sys.path.insert(0, ".")
from research.search3.europe_indices.common import *
from research.search3.europe_indices import strategies as S

sym = sys.argv[1] if len(sys.argv) > 1 else "DE40"
df = load(sym, "M30"); print(sym, len(df))
tests = [('gap', {}), ('us_open_fade', {}), ('close_fade', {}), ('overnight', {}), ('orb', {}), ('or_fail', {}),
         ('pdhl', {}), ('round', {}), ('round_fade', {}), ('late_momentum', {}), ('time_window', {}),
         ('lunch_break', {}), ('pullback', {}), ('prev_week', {}), ('calendar', {'kind': 'tom'}),
         ('compression_break', {}), ('fh_retest', {}), ('donchian', {})]
for nm, kw in tests:
    t0 = time.time(); s = S.BUILDERS[nm](df, **kw); n = sum(x is not None for x in s); t1 = time.time()
    r = H.score(df, s, name=nm)
    print(f'{nm:<20} sigs {n:>5} build {t1-t0:.1f}s score {time.time()-t1:.1f}s', H.summary_line(r))
d1 = load(sym, "D1")
for nm in ('d1_meanrev', 'big_day'):
    s = S.BUILDERS[nm](d1); r = H.score(d1, s, name=nm); print(H.summary_line(r))
