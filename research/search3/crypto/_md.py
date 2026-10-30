import pandas as pd
def md(self, index=False):
    cols=list(self.columns); rows=[[str(v) for v in r] for r in self.itertuples(index=False)]
    out=["| "+" | ".join(cols)+" |","|"+"|".join("---" for _ in cols)+"|"]
    out+=["| "+" | ".join(r)+" |" for r in rows]
    return "\n".join(out)
pd.DataFrame.to_markdown = md
