"""Config batches for run.py: (name, symbol, tf, fn, params)."""
B = {}

G = ["XAUUSD"]
FX = ["GBPUSD", "EURUSD", "USDJPY", "XAGUSD"]

# --- batch 1: broad first screen on H1 ---------------------------------
b1 = []
for sym in G + FX:
    # Asian range -> London breakout
    for re_, te in ((9, 14), (10, 15)):
        for tp in (1.0, 2.0, None):
            b1.append((f"asia0-{re_}_te{te}_tp{tp}", sym, "H1", "build_session_orb",
                       dict(rs=0, re=re_, te=te, exit_h=22, sl="far", tp_r=tp)))
    # archived-gold-like early box 1-4
    b1.append(("box1-4_tp2", sym, "H1", "build_session_orb",
               dict(rs=1, re=4, te=12, exit_h=22, sl="far", tp_r=2.0)))
    # London ORB 10-11 / 10-12
    for re_ in (11, 12):
        b1.append((f"lon10-{re_}_tp1.5", sym, "H1", "build_session_orb",
                   dict(rs=10, re=re_, te=16, exit_h=22, sl="far", tp_r=1.5)))
    # NY ORB (H1 16:00 bar contains 16:30 open)
    b1.append(("ny16-17_tp1.5", sym, "H1", "build_session_orb",
               dict(rs=16, re=17, te=20, exit_h=23, sl="far", tp_r=1.5)))
    # previous day high/low
    b1.append(("pdhl_atr0.5_tp1.5", sym, "H1", "build_pdhl",
               dict(ts=9, te=16, exit_h=22, sl="atr", sl_atr=0.5, tp_r=1.5)))
    b1.append(("pdhl_fade_tp1.5", sym, "H1", "build_pdhl",
               dict(ts=9, te=18, exit_h=22, fade=True, buf=0.05, tp_r=1.5)))
    # NR7 / inside
    for k in ("nr7", "inside", "nr4"):
        b1.append((f"{k}_far_tp2", sym, "H1", "build_nr_break",
                   dict(kind=k, ts=0, te=20, exit_h=None, max_hold=48, sl="far", tp_r=2.0)))
    # squeeze, donchian
    b1.append(("sqz_20_tp2", sym, "H1", "build_squeeze", dict()))
    b1.append(("donch20_trail3", sym, "H1", "build_donchian", dict(n_ch=20)))
    b1.append(("donch55_trail3_d", sym, "H1", "build_donchian", dict(n_ch=55, trend="d")))
B["b1"] = b1

BATCHES = B

# --- batch 2: higher-timeframe breakouts + M30 opens ---------------------
b2 = []
SY6 = ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY", "XAGUSD", "AUDUSD"]
for sym in SY6:
    for tf in ("H4", "D1"):
        for n_ch in (20, 55):
            for tr in (None, "d"):
                b2.append((f"donch{n_ch}_tr{tr}", sym, tf, "build_donchian",
                           dict(n_ch=n_ch, sl_atr=2.0, trail_atr=3.0, trail_after_r=0.0, trend=tr)))
    for k in ("inside", "nr7", "nr4"):
        b2.append((f"{k}_hold120_be1_tr2", sym, "H1", "build_nr_break",
                   dict(kind=k, exit_h=None, max_hold=120, sl="far", tp_r=None,
                        be_r=1.0, trail_atr=2.0 * 4, trail_after_r=1.0)))
    for tr in (None, "d"):
        b2.append((f"sqzH4_trail_tr{tr}", sym, "H4", "build_squeeze",
                   dict(sl_atr=1.5, tp_r=None, max_hold=60, trail_atr=2.5,
                        trail_after_r=1.0, trend=tr)))
for sym in ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY"]:
    b2.append(("m30_lon10-11_tp2", sym, "M30", "build_session_orb",
               dict(rs=10, re=11, te=14, exit_h=22, sl="far", tp_r=2.0)))
    b2.append(("m30_ny16.5-17_tp2", sym, "M30", "build_session_orb",
               dict(rs=16.5, re=17, te=19, exit_h=23, sl="far", tp_r=2.0)))
    b2.append(("m30_asia0-10_trail", sym, "M30", "build_session_orb",
               dict(rs=0, re=10, te=13, exit_h=22, sl="far", tp_r=None, be_r=1.0)))
B["b2"] = b2

# --- batch 3 ------------------------------------------------------------
ALL_H1 = ["XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD",
          "USDCHF", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "NZDJPY", "CADJPY", "EURGBP",
          "EURCHF", "GBPCHF", "AUDCAD", "US30", "US500", "USTEC", "DE40"]
b3 = []
for sym in ALL_H1:
    if sym in ("XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY"):
        pass
    else:
        b3.append(("inside_far_tp2", sym, "H1", "build_nr_break",
                   dict(kind="inside", ts=0, te=20, exit_h=None, max_hold=48, sl="far", tp_r=2.0)))
    b3.append(("donchH1_220_trd", sym, "H1", "build_donchian",
               dict(n_ch=220, sl_atr=4.0, trail_atr=6.0, trail_after_r=0.0, trend="d")))
for n_ch in (30, 40, 80, 120):
    b3.append((f"donch{n_ch}_trd", "XAUUSD", "H4", "build_donchian",
               dict(n_ch=n_ch, sl_atr=2.0, trail_atr=3.0, trail_after_r=0.0, trend="d")))
for tr_atr in (2.0, 4.0):
    b3.append((f"donch55_trd_trail{tr_atr}", "XAUUSD", "H4", "build_donchian",
               dict(n_ch=55, sl_atr=2.0, trail_atr=tr_atr, trail_after_r=0.0, trend="d")))
for sl_atr in (1.5, 3.0):
    b3.append((f"donch55_trd_sl{sl_atr}", "XAUUSD", "H4", "build_donchian",
               dict(n_ch=55, sl_atr=sl_atr, trail_atr=3.0, trail_after_r=0.0, trend="d")))
for sym in ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY"]:
    for k in (0.5, 1.0, 1.5):
        for filt in (None, "nr4"):
            b3.append((f"crabel_k{k}_{filt}", sym, "H1", "build_crabel",
                       dict(ss=10, te=16, exit_h=23, k=k, filt=filt)))
B["b3"] = b3

# --- batch 4: previous-week range breakout --------------------------------
b4 = []
FX_ALL = [s for s in ALL_H1 if s not in ("US30", "US500", "USTEC", "DE40")]
for sym in FX_ALL:
    b4.append(("pweek_sl1_trail8", sym, "H1", "build_prev_week",
               dict(sl_atr=1.0, trail_atr=8.0, trail_after_r=1.0, be_r=1.0)))
for sym in ("XAUUSD", "USDJPY", "GBPJPY", "EURJPY"):
    for sl_atr, tp in ((0.7, None), (1.5, None), (1.0, 2.0), (1.0, 3.0)):
        b4.append((f"pweek_sl{sl_atr}_tp{tp}", sym, "H1", "build_prev_week",
                   dict(sl_atr=sl_atr, tp_r=tp, trail_atr=8.0 if tp is None else None,
                        trail_after_r=1.0, be_r=1.0 if tp is None else None)))
    b4.append(("pweek_sl1_trail8_trd", sym, "H1", "build_prev_week",
               dict(sl_atr=1.0, trail_atr=8.0, trail_after_r=1.0, be_r=1.0, trend="d")))
B["b4"] = b4

# --- batch 5: indices + JPY crosses H4 -------------------------------------
b5 = []
IDX = ["US30", "US500", "USTEC", "DE40"]
for sym in IDX:
    op = 10.0 if sym == "DE40" else 16.5
    ex = 18 if sym == "DE40" else 23
    for tp in (1.0, 2.0, None):
        b5.append((f"orb_open30_tp{tp}", sym, "M30", "build_session_orb",
                   dict(rs=op, re=op + 0.5, te=op + 3, exit_h=ex, sl="far", tp_r=tp)))
    b5.append(("orb_open60_tp2", sym, "M30", "build_session_orb",
               dict(rs=op, re=op + 1, te=op + 3.5, exit_h=ex, sl="far", tp_r=2.0)))
    b5.append(("orb_open30_mid_tp2", sym, "M30", "build_session_orb",
               dict(rs=op, re=op + 0.5, te=op + 3, exit_h=ex, sl="mid", tp_r=2.0)))
    b5.append(("preopen_rng_tpNone", sym, "M30", "build_session_orb",
               dict(rs=1, re=op, te=op + 3, exit_h=ex, sl="far", tp_r=None)))
    for k in (0.5, 1.0):
        for filt in (None, "nr4"):
            b5.append((f"crabel_k{k}_{filt}", sym, "M30", "build_crabel",
                       dict(ss=op, te=op + 4, exit_h=ex, k=k, filt=filt)))
    b5.append(("pdhl_atr0.5_tp1.5", sym, "H1", "build_pdhl",
               dict(ts=op - 0.5, te=22, exit_h=23, sl="atr", sl_atr=0.5, tp_r=1.5)))
    b5.append(("pdhl_fade_tp1.5", sym, "H1", "build_pdhl",
               dict(ts=9, te=22, exit_h=23, fade=True, buf=0.05, tp_r=1.5)))
    for k in ("inside", "nr7"):
        b5.append((f"{k}_far_tp2", sym, "H1", "build_nr_break",
                   dict(kind=k, ts=0, te=23, exit_h=None, max_hold=48, sl="far", tp_r=2.0)))
    for n_ch, tr in ((20, "d"), (55, "d"), (55, None)):
        b5.append((f"donch{n_ch}_tr{tr}", sym, "H4", "build_donchian",
                   dict(n_ch=n_ch, sl_atr=2.0, trail_atr=3.0, trail_after_r=0.0, trend=tr)))
    b5.append(("sqzH4_trail_trNone", sym, "H4", "build_squeeze",
               dict(sl_atr=1.5, tp_r=None, max_hold=60, trail_atr=2.5, trail_after_r=1.0)))
    b5.append(("pweek_sl1_trail8", sym, "H1", "build_prev_week",
               dict(sl_atr=1.0, trail_atr=8.0, trail_after_r=1.0, be_r=1.0)))
for sym in ["EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "NZDJPY", "CADJPY"]:
    for n_ch, tr in ((20, "d"), (55, "d")):
        b5.append((f"donch{n_ch}_tr{tr}", sym, "H4", "build_donchian",
                   dict(n_ch=n_ch, sl_atr=2.0, trail_atr=3.0, trail_after_r=0.0, trend=tr)))
    b5.append(("sqzH4_trail_trNone", sym, "H4", "build_squeeze",
               dict(sl_atr=1.5, tp_r=None, max_hold=60, trail_atr=2.5, trail_after_r=1.0)))
B["b5"] = b5

# --- batch 6: day-range -> NY breakout ("late breakout") -----------------
b6 = []
for sym in ["XAUUSD", "GBPUSD", "EURUSD", "USDJPY", "GBPJPY", "US30", "US500", "DE40"]:
    for re_ in (14, 15, 16):
        for tp in (1.5, None):
            b6.append((f"day1-{re_}_te20_tp{tp}", sym, "H1", "build_session_orb",
                       dict(rs=1, re=re_, te=20, exit_h=23, sl="far", tp_r=tp)))
    b6.append(("day1-15_mid_tp2", sym, "H1", "build_session_orb",
               dict(rs=1, re=15, te=20, exit_h=23, sl="mid", tp_r=2.0)))
B["b6"] = b6

# --- batch 7: DE40 open-range neighbourhood + H1 long-history check --------
b7 = []
for tf, rlen in (("M30", 0.5), ("M30", 1.0), ("M30", 1.5), ("H1", 1.0), ("H1", 2.0)):
    for tr in (None, "d"):
        for tp in (2.0, None):
            for ex in (18, 22):
                b7.append((f"de_orb{rlen}_tr{tr}_tp{tp}_ex{ex}", "DE40", tf, "build_session_orb",
                           dict(rs=10, re=10 + rlen, te=14, exit_h=ex, sl="far", tp_r=tp,
                                trend=tr, min_rng=0.1)))
# same trend-filtered open-range idea on other markets (London/NY opens)
for sym, op in (("XAUUSD", 10), ("GBPUSD", 10), ("EURUSD", 10), ("USDJPY", 10), ("GBPJPY", 10),
                ("XAUUSD", 16), ("US30", 16), ("US500", 16), ("EURJPY", 10)):
    b7.append((f"orb{op}_1h_trd_tpNone", sym, "H1", "build_session_orb",
               dict(rs=op, re=op + 1, te=op + 4, exit_h=22 if op == 10 else 23, sl="far",
                    tp_r=None, trend="d", min_rng=0.1)))
B["b7"] = b7

# --- batch 8: refinements + same-symbol combos ---------------------------
b8 = []
DEB = dict(rs=10, re=10.5, te=14, exit_h=18, sl="far", tp_r=None, trend="d", min_rng=0.1)
for tag, ch in (("te12", dict(te=12)), ("te16", dict(te=16)), ("frac0.5", dict(sl_frac=0.5)),
                ("be1", dict(be_r=1.0)), ("tp3", dict(tp_r=3.0)), ("minr0.2", dict(min_rng=0.2)),
                ("long", dict(sides="long")), ("short", dict(sides="short")),
                ("ex17", dict(exit_h=17)), ("ex20", dict(exit_h=20)), ("body", dict(body=True))):
    b8.append((f"de_orb30_trd_{tag}", "DE40", "M30", "build_session_orb", {**DEB, **ch}))
b8.append(("de_orb30_trd_base", "DE40", "M30", "build_session_orb", DEB))
for sym in ("USDJPY", "GBPJPY"):
    for tag, ch in (("tp1.5", dict(tp_r=1.5)), ("tp3", dict(tp_r=3.0)), ("hold24", dict(max_hold=24)),
                    ("hold72", dict(max_hold=72)), ("mid", dict(sl="mid")), ("trd", dict(trend="d")),
                    ("nr4in", dict(kind="nr4in"))):
        base = dict(kind="inside", ts=0, te=20, exit_h=None, max_hold=48, sl="far", tp_r=2.0)
        b8.append((f"inside_{tag}", sym, "H1", "build_nr_break", {**base, **ch}))
PW = ("build_prev_week", dict(sl_atr=1.0, trail_atr=8.0, trail_after_r=1.0, be_r=1.0))
IN = ("build_nr_break", dict(kind="inside", ts=0, te=20, exit_h=None, max_hold=48, sl="far", tp_r=2.0))
DH = ("build_donchian", dict(n_ch=220, sl_atr=4.0, trail_atr=6.0, trail_after_r=0.0, trend="d"))
for sym in ("GBPJPY", "XAUUSD", "USDJPY", "AUDJPY", "EURJPY"):
    b8.append(("combo_pw_in_dh", sym, "H1", "build_combo", dict(parts=[PW, IN, DH])))
    b8.append(("combo_pw_in", sym, "H1", "build_combo", dict(parts=[PW, IN])))
B["b8"] = b8

# --- batch 9: DE40 entry-window grid, inside-day tp3 across JPY ----------
b9 = []
for te in (11.0, 11.5, 12.5, 13.0):
    b9.append((f"de_orb30_trd_te{te}", "DE40", "M30", "build_session_orb", {**DEB, "te": te}))
for tag, ch in (("frac0.5", dict(sl_frac=0.5)), ("minr0.2", dict(min_rng=0.2)), ("notr", dict(trend=None)),
                ("tp2", dict(tp_r=2.0)), ("ex22", dict(exit_h=22)), ("re11", dict(re=11.0, te=12.5))):
    b9.append((f"de_orb30_trd_te12_{tag}", "DE40", "M30", "build_session_orb", {**DEB, "te": 12, **ch}))
b9.append(("de_orb60_trd_te12_H1", "DE40", "H1", "build_session_orb", {**DEB, "re": 11, "te": 12}))
b9.append(("de_orb60_trd_te13_H1", "DE40", "H1", "build_session_orb", {**DEB, "re": 11, "te": 13}))
b9.append(("de_orb15_trd_te12_M15", "DE40", "M15", "build_session_orb", {**DEB, "re": 10.25, "te": 12}))
b9.append(("de_orb30_trd_te12_M15", "DE40", "M15", "build_session_orb", {**DEB, "te": 12}))
# same "first 1.5h after a 30-min open range" on the other cash opens
for sym, op, ex in (("US30", 16.5, 23), ("US500", 16.5, 23), ("USTEC", 16.5, 23), ("XAUUSD", 16.5, 23),
                    ("XAUUSD", 10, 18), ("GBPUSD", 10, 18), ("EURUSD", 10, 18)):
    b9.append((f"orb30_trd_te+2_{op}", sym, "M30", "build_session_orb",
               {**DEB, "rs": op, "re": op + 0.5, "te": op + 2, "exit_h": ex}))
INB = dict(kind="inside", ts=0, te=20, exit_h=None, max_hold=48, sl="far", tp_r=3.0)
for sym in ("EURJPY", "AUDJPY", "CHFJPY", "CADJPY", "NZDJPY", "XAUUSD", "GBPUSD", "EURUSD", "DE40", "US30"):
    b9.append(("inside_tp3", sym, "H1", "build_nr_break", INB))
for sym in ("USDJPY", "GBPJPY"):
    b9.append(("inside_tp4", sym, "H1", "build_nr_break", {**INB, "tp_r": 4.0}))
    b9.append(("inside_tp2.5", sym, "H1", "build_nr_break", {**INB, "tp_r": 2.5}))
    b9.append(("inside_tp3_hold72", sym, "H1", "build_nr_break", {**INB, "max_hold": 72}))
    b9.append(("inside_tp3_H4", sym, "H4", "build_nr_break", {**INB, "max_hold": 12}))
B["b9"] = b9

# --- batch 10: DE40 second sessions + stop variants -----------------------
b10 = []
DE = {**DEB, "te": 12.5}
for tag, ch in (("frac0.75", dict(sl_frac=0.75)), ("frac0.5", dict(sl_frac=0.5)),
                ("atr0.25", dict(sl="atr", sl_atr=0.25)), ("atr0.4", dict(sl="atr", sl_atr=0.4)),
                ("open9", dict(rs=9, re=9.5, te=11.5)), ("ema20", dict(trend="d")),):
    b10.append((f"de_orb30_te12.5_{tag}", "DE40", "M30", "build_session_orb", {**DE, **ch}))
NYDE = {**DEB, "rs": 16.5, "re": 17, "te": 19, "exit_h": 22}
b10.append(("de_nyorb30_trd", "DE40", "M30", "build_session_orb", NYDE))
b10.append(("de_nyorb30_notr", "DE40", "M30", "build_session_orb", {**NYDE, "trend": None}))
b10.append(("de_combo_xetra_ny", "DE40", "M30", "build_combo",
            dict(parts=[("build_session_orb", DE), ("build_session_orb", NYDE)])))
b10.append(("de_combo_xetra_open9", "DE40", "M30", "build_combo",
            dict(parts=[("build_session_orb", DE), ("build_session_orb", {**DE, "rs": 9, "re": 9.5, "te": 9.99})])))
B["b10"] = b10
