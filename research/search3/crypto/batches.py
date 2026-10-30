"""Config grids: (name, symbol, tf, build_fn, params)."""
SYMS = ["BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "SOLUSD", "ADAUSD", "BNBUSD", "DOTUSD"]
ALTS = [s for s in SYMS if s != "BTCUSD"]


def _grid(name, fn, tf, variants, syms=SYMS):
    out = []
    for tag, p in variants:
        for s in syms:
            out.append((f"{name}_{tag}", s, tf, fn, p))
    return out


def screen():
    c = []
    # 1 time-series momentum
    c += _grid("tsmom", "build_tsmom", "D1", [
        ("d1_lb10_a2", dict(lb=10, atr_mult=2.0)), ("d1_lb20_a2", dict(lb=20, atr_mult=2.0)),
        ("d1_lb40_a2", dict(lb=40, atr_mult=2.0)), ("d1_lb20_a3", dict(lb=20, atr_mult=3.0)),
        ("d1_lb40_a3", dict(lb=40, atr_mult=3.0)), ("d1_lb20_a3_L", dict(lb=20, atr_mult=3.0, long_only=True))])
    c += _grid("tsmom", "build_tsmom", "H4", [
        ("h4_lb30", dict(lb=30, atr_mult=2.5)), ("h4_lb60", dict(lb=60, atr_mult=2.5)),
        ("h4_lb120", dict(lb=120, atr_mult=2.5))])
    # 2 donchian
    c += _grid("donch", "build_donchian", "D1", [
        ("d1_20_10", dict(n=20, exit_n=10)), ("d1_55_20", dict(n=55, exit_n=20)),
        ("d1_20_10_a0", dict(n=20, exit_n=10, atr_mult=0)), ("d1_20_10_L", dict(n=20, exit_n=10, long_only=True))])
    c += _grid("donch", "build_donchian", "H4", [
        ("h4_30_15", dict(n=30, exit_n=15)), ("h4_60_15", dict(n=60, exit_n=15))])
    # 3 compression breakout
    c += _grid("compress", "build_compress_bo", "H4", [
        ("h4_r07_rr2", dict(ratio=0.7, rr=2.0)), ("h4_r07_trail", dict(ratio=0.7, trail=True))])
    c += _grid("compress", "build_compress_bo", "D1", [("d1_r07_rr2", dict(ratio=0.7, rr=2.0))])
    # 4 weekend range breakout
    c += _grid("weekend", "build_weekend_bo", "H1", [
        ("mid_h24", dict(stop="mid", hold=24)), ("atr_rr2", dict(stop="atr", rr=2.0, hold=48)),
        ("mid_h48_montue", dict(stop="mid", hold=48, days=(0, 1)))])
    # 5 asian range breakout
    c += _grid("asia", "build_session_bo", "H1", [
        ("rr15", dict(rr=1.5)), ("noTP_x23", dict(rr=None)), ("range_rr2", dict(stop="range", rr=2.0)),
        ("wk_rr15", dict(rr=1.5, weekdays_only=True))])
    # 6 US open momentum
    c += _grid("usopen", "build_us_open_mom", "H1", [
        ("t075", dict(thresh=0.75)), ("t10", dict(thresh=1.0)), ("fade_t10", dict(thresh=1.0, fade=True)),
        ("t075_rr15", dict(thresh=0.75, rr=1.5))])
    # 7 weekday calendar
    c += _grid("weekday", "build_weekday", "H1", [
        ("MW_Th", dict()), ("MW", dict(short_days=())), ("Th", dict(long_days=())),
        ("W", dict(long_days=(2,), short_days=())), ("MWF_Th", dict(long_days=(0, 2, 4)))])
    c += _grid("weekday", "build_weekday", "D1", [("d1_MW_Th", dict())])
    # 8 overnight / calendar slices
    c += _grid("overnight", "build_overnight", "H1", [
        ("sun20_L12", dict(side="long", entry_wd=6, entry_hour=20, hold=12)),
        ("mon00_L24", dict(side="long", entry_wd=0, entry_hour=0, hold=24)),
        ("fri20_S48", dict(side="short", entry_wd=4, entry_hour=20, hold=48)),
        ("sat00_S48", dict(side="short", entry_wd=5, entry_hour=0, hold=48))])
    # 9 prior-day levels
    c += _grid("pd", "build_pd_break", "H1", [
        ("break_rr2", dict(mode="break", rr=2.0)), ("sfp_rr2", dict(mode="sfp", rr=2.0)),
        ("sfp_lvl", dict(mode="sfp", tp_level=True)), ("break_rr2_x23", dict(mode="break", rr=2.0, exit_hour=23))])
    c += _grid("pd", "build_pd_break", "H4", [("h4_sfp_rr2", dict(mode="sfp", rr=2.0))])
    # 10 prior-week levels
    c += _grid("pw", "build_pw_sfp", "H1", [("sfp_rr2", dict(rr=2.0))])
    c += _grid("pw", "build_pw_sfp", "H4", [
        ("h4_sfp_trail2", dict(trail_mult=2.0)), ("h4_break_trail2", dict(mode="break", trail_mult=2.0)),
        ("h4_break_rr2", dict(mode="break", rr=2.0))])
    # 11 prior-day-close reversion
    c += _grid("pdc", "build_pdc_revert", "H1", [
        ("z15", dict(z=1.5)), ("z20", dict(z=2.0)), ("z15_h24", dict(z=1.5, hold=24, atr_mult=1.5))])
    # 12 RSI2 mean reversion
    c += _grid("rsi2", "build_rsi2_mr", "H1", [("trend", dict()), ("notrend", dict(use_trend=False))])
    c += _grid("rsi2", "build_rsi2_mr", "H4", [("h4_trend", dict()), ("h4_notrend", dict(use_trend=False))])
    # 13 EMA pullback
    c += _grid("emapb", "build_ema_pullback", "H4", [("h4_rr2", dict()), ("h4_trail", dict(trail=True))])
    c += _grid("emapb", "build_ema_pullback", "D1", [("d1_rr2", dict(fast=10, slow=20, trend=50))])
    # 14 squeeze
    c += _grid("squeeze", "build_squeeze", "H4", [("h4", dict()), ("h4_rr2", dict(trail=False))])
    c += _grid("squeeze", "build_squeeze", "H1", [("h1", dict())])
    c += _grid("squeeze", "build_squeeze", "D1", [("d1", dict(min_bars=4))])
    # 15 round numbers
    c += _grid("round", "build_round_bounce", "H1", [("h1", dict()), ("h1_rr15", dict(rr=1.5, tol=0.3))])
    c += _grid("round", "build_round_bounce", "H4", [("h4", dict())])
    # 16 weekly open bias
    c += _grid("wopen", "build_weekly_open", "H1", [("h1_05", dict()), ("h1_10", dict(min_dist=1.0))])
    c += _grid("wopen", "build_weekly_open", "H4", [("h4_05", dict()), ("h4_notrail", dict(trail=False))])
    # 17 alt vs BTC relative strength
    c += _grid("relstr", "build_rel_strength", "H1", [
        ("lb120_h24", dict(lb=120, hold=24)), ("lb120_nobtc", dict(lb=120, hold=24, need_btc=False)),
        ("lb48_h12", dict(lb=48, hold=12))], syms=ALTS)
    c += _grid("relstr", "build_rel_strength", "H4", [("h4_lb30_h6", dict(lb=30, hold=6))], syms=ALTS)
    # 18 volatility spikes
    c += _grid("spike", "build_vol_spike", "H1", [("fade", dict()), ("follow", dict(mode="follow", rr=2.0, hold=12))])
    c += _grid("spike", "build_vol_spike", "H4", [("h4_fade", dict(k=2.5))])
    # 19 server-day opening range
    c += _grid("orb", "build_day_orb", "H1", [
        ("n4_rr2", dict(n_hours=4, rr=2.0)), ("n2_rr2", dict(n_hours=2, rr=2.0)),
        ("n6_rr15", dict(n_hours=6, rr=1.5)), ("n4_noTP", dict(n_hours=4, rr=None, stop="atr"))])
    # 20 inside day
    c += _grid("inside", "build_inside_day", "H1", [("h1_rr2", dict())])
    c += _grid("inside", "build_inside_day", "H4", [("h4_rr2", dict()), ("h4_trail", dict(trail=True))])
    c += _grid("inside", "build_inside_day", "D1", [("d1_trail", dict(trail=True))])
    # 21 supertrend
    c += _grid("stt", "build_supertrend", "H4", [("h4_10_3", dict()), ("h4_14_2", dict(n=14, mult=2.0))])
    c += _grid("stt", "build_supertrend", "D1", [("d1_10_3", dict()), ("d1_10_3_L", dict(long_only=True))])
    return c


BATCHES = {"screen": screen}


def rerun():
    """Configs that errored in `screen` (out-of-memory while reading the csv)."""
    import json
    from pathlib import Path
    rows = [json.loads(l) for l in open(Path(__file__).with_name("results.jsonl"))]
    bad = [r for r in rows if "error" in r]
    return [(r["name"], r["symbol"], r["tf"], r["fn"], r["params"]) for r in bad]


def refine():
    c = []
    BE = ["BTCUSD", "ETHUSD"]
    BIG = ["BTCUSD", "ETHUSD", "XRPUSD", "SOLUSD"]
    # weekday sweep: every single day long and short (D1 + H1), two ATR widths
    for d in range(7):
        c += _grid("wd", "build_weekday", "D1", [(f"L{d}", dict(long_days=(d,), short_days=())),
                                                   (f"S{d}", dict(long_days=(), short_days=(d,)))])
    c += _grid("wd", "build_weekday", "H1", [(f"L{d}_h1", dict(long_days=(d,), short_days=())) for d in (0, 1, 2, 5, 6)]
               + [(f"S{d}_h1", dict(long_days=(), short_days=(d,))) for d in (3, 4, 5, 6)], syms=BIG)
    c += _grid("wd", "build_weekday", "D1", [
        ("MW_Th_a3", dict(atr_mult=3.0)), ("MW_Th_a15", dict(atr_mult=1.5)),
        ("MTW_Th", dict(long_days=(0, 1, 2))), ("MW_ThF", dict(short_days=(3, 4))),
        ("MW_Th_noS", dict(long_days=(0, 2), short_days=())), ("MWSu_Th", dict(long_days=(0, 2, 6)))])
    c += _grid("wd", "build_weekday", "H1", [("MW_Th_e0", dict(entry_hour=0)), ("MW_Th_e12", dict(entry_hour=12)),
                                             ("MW_Th_a3", dict(atr_mult=3.0))], syms=BIG)
    # hour slices (all days): best/worst hours from the study + funding-hour anchors
    for hh in (0, 2, 8, 10, 14, 16, 18, 20, 22):
        c += _grid("hs", "build_hour_slice", "H1", [(f"L{hh}_h8", dict(hour=hh, side="long", hold=8)),
                                                      (f"S{hh}_h8", dict(hour=hh, side="short", hold=8))], syms=BE)
    c += _grid("hs", "build_hour_slice", "H1", [("L0_h24", dict(hour=0, side="long", hold=24)),
                                                 ("L16_h8_wk", dict(hour=16, side="long", hold=8, days=(0, 1, 2, 3, 4))),
                                                 ("L0_h12_we", dict(hour=0, side="long", hold=12, days=(5, 6)))])
    # funding cycle
    c += _grid("fund", "build_funding_cycle", "H1", [
        ("t05_h8", dict()), ("t10_h8", dict(thresh=1.0)), ("t05_h8_fade", dict(fade=True)),
        ("t10_h8_fade", dict(thresh=1.0, fade=True)), ("t05_h4_a1", dict(hold=4, atr_mult=1.0))])
    # btc lead
    c += _grid("lead", "build_btc_lead", "H1", [
        ("lb4_h12", dict()), ("lb4_h24", dict(hold=24)), ("lb8_t15_h12", dict(lb=8, btc_thresh=1.5)),
        ("lb4_h12_rr2", dict(rr=2.0)), ("lb2_t08_h6", dict(lb=2, btc_thresh=0.8, hold=6))], syms=ALTS)
    c += _grid("lead", "build_btc_lead", "H4", [("h4_lb2_h6", dict(lb=2, hold=6)), ("h4_lb4_h12", dict(lb=4, hold=12))], syms=ALTS)
    # n-day breakout
    c += _grid("nbo", "build_nday_bo", "D1", [
        ("d1_10_h5", dict()), ("d1_20_h10", dict(n=20, hold_days=10)), ("d1_10_h5_L", dict(long_only=True)),
        ("d1_20_h10_trail", dict(n=20, hold_days=10, trail=True)), ("d1_5_h3", dict(n=5, hold_days=3)),
        ("d1_30_h15_a3", dict(n=30, hold_days=15, atr_mult=3.0))])
    c += _grid("nbo", "build_nday_bo", "H4", [("h4_60_h5", dict(n=60, hold_days=5)), ("h4_120_h10_trail", dict(n=120, hold_days=10, trail=True))])
    # weekend mean reversion / follow
    c += _grid("wemr", "build_weekend_mr", "H1", [
        ("fade_t10", dict()), ("fade_t05", dict(thresh=0.5)), ("fade_t15_h48", dict(thresh=1.5, hold=48)),
        ("follow_t10", dict(follow=True)), ("follow_t05_h48", dict(follow=True, thresh=0.5, hold=48)),
        ("fade_sun20", dict(entry_hour=20))])
    # prior-day-close follow-through / fade
    c += _grid("pdm", "build_pd_mom", "H1", [
        ("t05_h24", dict()), ("t10_h24", dict(thresh=1.0)), ("t05_h24_fade", dict(fade=True)),
        ("t10_h24_fade", dict(thresh=1.0, fade=True)), ("h16_t05_h8", dict(hour=16, hold=8)),
        ("h12_t05_h12", dict(hour=12, hold=12))])
    # US-session / day-so-far momentum via us_open_mom params
    c += _grid("usopen", "build_us_open_mom", "H1", [
        ("day_0_15_t10", dict(t0=0, t1=15, thresh=1.0)), ("day_0_15_t10_fade", dict(t0=0, t1=15, thresh=1.0, fade=True)),
        ("ldn_10_15_t075", dict(t0=10, t1=15, thresh=0.75)), ("t10_rr2", dict(thresh=1.0, rr=2.0))])
    # overnight variants around the Monday-open winner
    c += _grid("overnight", "build_overnight", "H1", [
        ("sun23_L24", dict(side="long", entry_wd=6, entry_hour=23, hold=24)),
        ("mon00_L48", dict(side="long", entry_wd=0, entry_hour=0, hold=48)),
        ("mon00_L12", dict(side="long", entry_wd=0, entry_hour=0, hold=12)),
        ("mon00_L24_a3", dict(side="long", entry_wd=0, entry_hour=0, hold=24, atr_mult=3.0)),
        ("wed00_L24", dict(side="long", entry_wd=2, entry_hour=0, hold=24)),
        ("thu00_S24", dict(side="short", entry_wd=3, entry_hour=0, hold=24))])
    # prior-week sfp / squeeze / spike / tsmom refinements
    c += _grid("pw", "build_pw_sfp", "H4", [("h4_sfp_trail15", dict(trail_mult=1.5)), ("h4_sfp_trail3", dict(trail_mult=3.0)),
                                            ("h4_sfp_rr3", dict(rr=3.0)), ("h4_sfp_trail2_h60", dict(trail_mult=2.0, max_hold=60))])
    c += _grid("pw", "build_pw_sfp", "H1", [("h1_sfp_trail2", dict(trail_mult=2.0)), ("h1_sfp_trail3", dict(trail_mult=3.0))])
    c += _grid("pw", "build_pw_sfp", "D1", [("d1_sfp_trail2", dict(trail_mult=2.0)), ("d1_break_trail2", dict(mode="break", trail_mult=2.0))])
    c += _grid("squeeze", "build_squeeze", "H4", [("h4_mb4", dict(min_bars=4)), ("h4_mb8", dict(min_bars=8)),
                                                  ("h4_kc1", dict(kc_mult=1.0)), ("h4_a2", dict(atr_mult=2.0)), ("h4_a25_kc2", dict(atr_mult=2.5, kc_mult=2.0))])
    c += _grid("spike", "build_vol_spike", "H1", [("follow_k25_h12", dict(mode="follow", k=2.5, rr=2.0, hold=12)),
                                                  ("follow_k3_h24", dict(mode="follow", rr=3.0, hold=24)),
                                                  ("follow_k3_noTP_h24", dict(mode="follow", rr=None, hold=24)),
                                                  ("follow_k35_h12", dict(mode="follow", k=3.5, rr=2.0, hold=12))])
    c += _grid("spike", "build_vol_spike", "H4", [("h4_follow_k25_h6", dict(mode="follow", k=2.5, rr=2.0, hold=6))])
    c += _grid("tsmom", "build_tsmom", "D1", [("d1_lb30_a25", dict(lb=30, atr_mult=2.5)), ("d1_lb60_a3", dict(lb=60, atr_mult=3.0)),
                                              ("d1_lb40_a4", dict(lb=40, atr_mult=4.0)), ("d1_lb40_a2_notrail", dict(lb=40, atr_mult=2.0, trail=False))])
    c += _grid("inside", "build_inside_day", "H4", [("h4_trail_a15", dict(trail=True, atr_mult=1.5)), ("h4_rr3", dict(rr=3.0))])
    c += _grid("donch", "build_donchian", "D1", [("d1_55_20_a3", dict(n=55, exit_n=20, atr_mult=3.0)), ("d1_40_20", dict(n=40, exit_n=20))])
    return c


BATCHES.update({"rerun": rerun, "refine": refine})
