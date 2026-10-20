from research.search.jpy_session.run import run, get
for sym in ["CHFJPY","EURJPY","GBPJPY","AUDJPY","NZDJPY","USDJPY","CADJPY"]:
    try:
        df=get(sym); print(sym, df.time.min(), df.time.max(), len(df), df.attrs.get('source'))
        run(f"live_h0_hold12_{sym}", sym, fn="build_chfjpy_live")
    except FileNotFoundError as e:
        print("SKIP", e)
