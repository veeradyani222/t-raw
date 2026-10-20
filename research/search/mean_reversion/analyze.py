"""Helpers to rank screen results by an estimated prop $/month and by
robustness across symbols. Estimate only; the harness is the judge."""
import json
import numpy as np
import pandas as pd


def est(d, months):
    dd = d.ddR.abs() * 1.3 + 1.0           # intrabar + slack
    wd = d.wdR.abs() * 1.2 + 0.5
    risk = np.minimum(0.02, np.minimum(0.06 / dd, 0.03 / wd))
    risk = np.floor(risk / 0.0025) * 0.0025
    return d.R * risk * 10000 / months


def load(path, months_by_sym):
    d = pd.read_csv(path)
    d["months"] = d.symbol.map(months_by_sym).fillna(108)
    d["est"] = est(d, d["months"])
    d["key"] = d.name + "|" + d.tf + "|" + d.params
    return d
