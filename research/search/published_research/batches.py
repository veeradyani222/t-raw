"""Experiment batches (name, builder, symbol, tf, params)."""

def b_gold_session():
    j = []
    # Donati & Jung: gold up in Asian hours. Entry after bar 1 (avoid rollover bars 23-00)
    for ex in (4, 6, 8, 10):
        for sl in (0.5, 1.0):
            j.append((f"asia_long_1to{ex}_sl{sl}", "build_session_drift", "XAUUSD", "H1",
                      dict(side="long", entry_hour=1, exit_hour=ex, sl_datr=sl)))
    j.append(("asia_long_0to8_sl1", "build_session_drift", "XAUUSD", "H1",
              dict(side="long", entry_hour=0, exit_hour=8, sl_datr=1.0)))
    j.append(("asia_long_2to8_sl1", "build_session_drift", "XAUUSD", "H1",
              dict(side="long", entry_hour=2, exit_hour=8, sl_datr=1.0)))
    # western-hours short (London PM fix / NY)
    for en, ex in ((15, 17), (15, 20), (16, 20), (10, 17)):
        j.append((f"west_short_{en}to{ex}", "build_session_drift", "XAUUSD", "H1",
                  dict(side="short", entry_hour=en, exit_hour=ex, sl_datr=1.0)))
    j.append(("gold_daycycle", "build_two_leg_session", "XAUUSD", "H1", dict()))
    # silver cross-check
    j.append(("asia_long_1to8_sl1", "build_session_drift", "XAGUSD", "H1",
              dict(side="long", entry_hour=1, exit_hour=8, sl_datr=1.0)))
    return j


def b_fx_session():
    j = []
    # Breedon & Ranaldo: EUR weakens in European morning, strengthens in US hours
    for sym in ("EURUSD", "GBPUSD"):
        j.append((f"br_eu_morning_short_9to14", "build_session_drift", sym, "H1",
                  dict(side="short", entry_hour=9, exit_hour=14, sl_datr=1.0)))
        j.append((f"br_us_hours_long_15to21", "build_session_drift", sym, "H1",
                  dict(side="long", entry_hour=15, exit_hour=21, sl_datr=1.0)))
        j.append((f"br_two_leg", "build_two_leg_session", sym, "H1",
                  dict(long_entry=15, long_exit=21, short_entry=9, short_exit=14, sl_datr=1.0)))
    # JPY depreciates during Tokyo hours -> long USDJPY Tokyo session
    j.append(("br_tokyo_long_1to9", "build_session_drift", "USDJPY", "H1",
              dict(side="long", entry_hour=1, exit_hour=9, sl_datr=1.0)))
    j.append(("br_tokyo_long_2to9", "build_session_drift", "USDJPY", "H1",
              dict(side="long", entry_hour=2, exit_hour=9, sl_datr=1.0)))
    for sym in ("AUDUSD", "NZDUSD"):
        # AUD/NZD home hours = Asia -> short AUDUSD in Sydney/Tokyo session
        j.append(("br_asia_short_1to9", "build_session_drift", sym, "H1",
                  dict(side="short", entry_hour=1, exit_hour=9, sl_datr=1.0)))
    return j


def b_tsmom():
    j = []
    for sym in ("XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"):
        for lb in (63, 126, 252):
            j.append((f"tsmom_lb{lb}_M", "build_tsmom", sym, "D1",
                      dict(lookback=lb, rebalance="M", sl_atr=3.0)))
    return j


def b_donchian():
    j = []
    for sym in ("XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"):
        j.append(("donchian_55_20", "build_donchian", sym, "D1", dict(entry_n=55, exit_n=20)))
        j.append(("donchian_20_10", "build_donchian", sym, "D1", dict(entry_n=20, exit_n=10)))
    for e, x in ((55, 20), (110, 40)):
        j.append((f"donchian_{e}_{x}", "build_donchian", "XAUUSD", "H4", dict(entry_n=e, exit_n=x)))
    return j


def b_rsi2():
    j = []
    for sym in ("XAUUSD", "XAGUSD", "EURUSD", "USDJPY"):
        j.append(("rsi2_long", "build_rsi2", sym, "D1", dict()))
        j.append(("rsi2_both", "build_rsi2", sym, "D1", dict(long_only=False)))
    return j


def b_fomc_gold():
    j = []
    for sym in ("XAUUSD", "EURUSD", "USDJPY"):
        for side in ("long", "short"):
            j.append((f"prefomc_{side}", "build_pre_fomc", sym, "H1", dict(side=side)))
    j.append(("tom_long", "build_turn_of_month", "XAUUSD", "H1", dict()))
    return j


IDX = ("US500", "US30", "USTEC", "DE40")


def b_indices():
    j = []
    for sym in IDX:
        j.append(("overnight_22to15", "build_overnight", sym, "H1", dict()))
        j.append(("tom_1_4", "build_turn_of_month", sym, "H1", dict()))
        j.append(("preholiday", "build_pre_holiday", sym, "H1", dict()))
        j.append(("prefomc_long", "build_pre_fomc", sym, "H1", dict()))
        j.append(("rsi2_long", "build_rsi2", sym, "D1", dict()))
        j.append(("gap_fade", "build_gap_fade", sym, "H1", dict()))
        j.append(("intraday_mom_h1", "build_intraday_momentum", sym, "H1", dict()))
        j.append(("intraday_mom_m30", "build_intraday_momentum", sym, "M30", dict()))
        j.append(("tsmom_lb252_M", "build_tsmom", sym, "D1", dict(lookback=252)))
    return j


def b_fx_fix():
    """Krohn, Mueller & Whelan (JF 2024): USD appreciates into the London 4pm
    fix (server 18:00) and depreciates after it."""
    j = []
    for sym, usd_base in (("EURUSD", False), ("GBPUSD", False), ("AUDUSD", False),
                          ("NZDUSD", False), ("USDJPY", True), ("XAUUSD", False)):
        after = "short" if usd_base else "long"     # USD down after the fix
        before = "long" if usd_base else "short"
        j.append(("kmw_postfix_17to21", "build_session_drift", sym, "H1",
                  dict(side=after, entry_hour=17, exit_hour=21, sl_datr=1.0)))
        j.append(("kmw_prefix_14to17", "build_session_drift", sym, "H1",
                  dict(side=before, entry_hour=14, exit_hour=17, sl_datr=1.0)))
    return j





def b_fomc_robust():
    """Pre-FOMC USD weakness (Lucca & Moench 2015 window; Mueller,
    Tahbaz-Salehi & Vedolin 2017 FX version): neighbours + other USD pairs."""
    j = []
    usd_short = {"XAUUSD": "long", "XAGUSD": "long", "EURUSD": "long", "GBPUSD": "long",
                 "AUDUSD": "long", "NZDUSD": "long", "USDJPY": "short", "USDCHF": "short",
                 "USDCAD": "short"}
    for sym, side in usd_short.items():
        j.append(("prefomc_usdshort", "build_pre_fomc", sym, "H1", dict(side=side)))
    for sym in ("XAUUSD", "EURUSD"):
        side = usd_short[sym]
        for en, ex in ((18, 20), (22, 20), (20, 19), (20, 21), (20, 23), (16, 20)):
            j.append((f"prefomc_{en}to{ex}", "build_pre_fomc", sym, "H1",
                      dict(side=side, entry_hour=en, exit_hour=ex)))
        for sl in (1.0, 2.0):
            j.append((f"prefomc_sl{sl}", "build_pre_fomc", sym, "H1", dict(side=side, sl_datr=sl)))
    return j


def b_tom_robust():
    j = []
    for db in (0, 1, 2, 3):
        for hd in (2, 4, 6):
            j.append((f"tom_db{db}_hd{hd}", "build_turn_of_month", "XAUUSD", "H1",
                      dict(days_before=db, hold_days=hd)))
    for sym in ("XAGUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"):
        j.append(("tom_long_1_4", "build_turn_of_month", sym, "H1", dict()))
        j.append(("tom_short_1_4", "build_turn_of_month", sym, "H1", dict(side="short")))
    for eh in (10, 16):
        j.append((f"tom_eh{eh}", "build_turn_of_month", "XAUUSD", "H1", dict(entry_hour=eh)))
    j.append(("tom_d1", "build_turn_of_month", "XAUUSD", "D1", dict()))
    return j

USD_SHORT = {"XAUUSD": "long", "XAGUSD": "long", "EURUSD": "long", "GBPUSD": "long",
             "AUDUSD": "long", "NZDUSD": "long", "USDJPY": "short", "USDCHF": "short",
             "USDCAD": "short"}


def b_fomc2():
    j = []
    for sym, side in USD_SHORT.items():
        # MTV-style: hold THROUGH the announcement (eve 21:00 -> FOMC day 00:00)
        j.append(("fomc_through_27b", "build_pre_fomc", sym, "H1", dict(side=side, hold_bars=27)))
        j.append(("prefomc_sl1", "build_pre_fomc", sym, "H1", dict(side=side, sl_datr=1.0)))
    for sym in ("XAUUSD", "EURUSD", "GBPUSD"):
        side = USD_SHORT[sym]
        j.append(("prefomc_eve22_to20", "build_pre_fomc", sym, "H1", dict(side=side, entry_hour=22)))
        j.append(("prefomc_eve19_to20", "build_pre_fomc", sym, "H1", dict(side=side, entry_hour=19)))
        j.append(("prefomc_eve20_to19", "build_pre_fomc", sym, "H1", dict(side=side, exit_hour=19)))
        j.append(("prefomc_tp2", "build_pre_fomc", sym, "H1", dict(side=side, sl_datr=1.0, tp_datr=2.0)))
        j.append(("fomc_daywithann_24b_from23", "build_pre_fomc", sym, "H1",
                  dict(side=side, entry_hour=23, hold_bars=24)))
    return j


def b_cycle_season():
    j = []
    for sym in ("XAUUSD", "EURUSD", "GBPUSD", "AUDUSD"):
        j.append(("fomc_cycle_even_usdshort", "build_fomc_cycle", sym, "H1", dict(side=USD_SHORT[sym])))
        j.append(("fomc_cycle_odd_usdshort", "build_fomc_cycle", sym, "H1",
                  dict(side=USD_SHORT[sym], weeks=(1, 3, 5))))
    j.append(("autumn_sep_nov", "build_month_season", "XAUUSD", "D1", dict()))
    j.append(("autumn_sep_nov", "build_month_season", "XAGUSD", "D1", dict()))
    j.append(("winter_dec_jan", "build_month_season", "XAUUSD", "D1", dict(months=(12, 1))))
    j.append(("autumn_sep_nov_sl2", "build_month_season", "XAUUSD", "D1", dict(sl_atr=2.0)))
    j.append(("gold_calendar", "build_gold_calendar", "XAUUSD", "H1", dict()))
    j.append(("gold_calendar_fsl1", "build_gold_calendar", "XAUUSD", "H1", dict(fomc_sl=1.0)))
    j.append(("gold_calendar_tom0", "build_gold_calendar", "XAUUSD", "H1", dict(tom_days_before=0)))
    j.append(("gold_calendar", "build_gold_calendar", "XAGUSD", "H1", dict()))
    return j



def b_imom():
    """Gao, Han, Li & Zhou (2018) intraday momentum; commodity-futures version
    (COMEX gold day session 08:20-13:30 ET = server 15:20-20:30)."""
    j = []
    for sym in ("XAUUSD", "XAGUSD"):
        j.append(("imom_comex_m30", "build_intraday_momentum", sym, "M30",
                  dict(signal_close="16:00", entry_close="20:00", exit_close="20:30", ref_close="20:30")))
        j.append(("imom_comex_h1", "build_intraday_momentum", sym, "H1",
                  dict(signal_close="16:00", entry_close="20:00", exit_close="21:00", ref_close="21:00")))
        j.append(("imom_nyclose_m30", "build_intraday_momentum", sym, "M30", dict()))
        j.append(("imom_nyclose_h1", "build_intraday_momentum", sym, "H1", dict()))
    for sym in ("EURUSD", "GBPUSD", "USDJPY"):
        j.append(("imom_nyclose_m30", "build_intraday_momentum", sym, "M30", dict()))
        j.append(("imom_nyclose_h1", "build_intraday_momentum", sym, "H1", dict()))
    j.append(("imom_comex_m30_sl1", "build_intraday_momentum", "XAUUSD", "M30",
              dict(signal_close="16:00", entry_close="20:00", exit_close="20:30", ref_close="20:30", sl_datr=1.0)))
    j.append(("imom_comex_m30_sig1630", "build_intraday_momentum", "XAUUSD", "M30",
              dict(signal_close="16:30", entry_close="20:00", exit_close="20:30", ref_close="20:30")))
    return j



def b_gcal():
    j = []
    for db in (0, 1):
        for hd in (2, 3, 4, 6):
            for fsl in (1.0, 1.5):
                j.append((f"gcal_db{db}_hd{hd}_fsl{fsl}", "build_gold_calendar", "XAUUSD", "H1",
                          dict(tom_days_before=db, tom_hold=hd, fomc_sl=fsl)))
    j.append(("gcal_db0_hd4", "build_gold_calendar", "XAGUSD", "H1", dict(tom_days_before=0)))
    j.append(("gcal_tom_only_db0", "build_gold_calendar", "XAUUSD", "H1", dict(fomc=False, tom_days_before=0)))
    return j



def b_eqcal():
    j = []
    for sym in ("US500", "US30", "USTEC", "DE40"):
        j.append(("eqcal_all", "build_equity_calendar", sym, "H1", dict()))
        for sl in (1.0, 2.0):
            j.append((f"eqcal_sl{sl}", "build_equity_calendar", sym, "H1", dict(sl_datr=sl)))
        j.append(("eqcal_db0", "build_equity_calendar", sym, "H1", dict(tom_days_before=0)))
        j.append(("eqcal_hd2", "build_equity_calendar", sym, "H1", dict(tom_hold=2)))
    for sym in ("US500", "US30"):
        j.append(("overnight_22to15_sl1", "build_overnight", sym, "H1", dict(sl_datr=1.0)))
        j.append(("overnight_22to16", "build_overnight", sym, "H1", dict(exit_hour=16)))
        j.append(("fomc_cycle_even", "build_fomc_cycle", sym, "H1", dict()))
        j.append(("gap_fade_0.4", "build_gap_fade", sym, "H1", dict(min_gap_datr=0.4)))
    return j



def b_eqcal2():
    j = []
    for sym in ("US500", "US30", "DE40"):
        for hd in (2, 3, 6):
            j.append((f"eqcal_db0_hd{hd}", "build_equity_calendar", sym, "H1", dict(tom_days_before=0, tom_hold=hd)))
        for sl in (1.0, 2.0):
            j.append((f"eqcal_db0_sl{sl}", "build_equity_calendar", sym, "H1", dict(tom_days_before=0, sl_datr=sl)))
        j.append(("tom_only_db0_hd4", "build_turn_of_month", sym, "H1", dict(days_before=0, hold_days=4)))
        for off in (0, 3, 6):
            j.append((f"control_every8_off{off}", "build_control_long", sym, "H1",
                      dict(every=8, offset=off, hold_days=4)))
    for off in (0, 3, 6):
        j.append((f"control_every8_off{off}", "build_control_long", "XAUUSD", "H1",
                  dict(every=8, offset=off, hold_days=4)))
    return j
BATCHES = {k[2:]: v for k, v in dict(globals()).items() if k.startswith("b_")}
