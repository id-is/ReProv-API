"""Shared feature engineering for next-day heatwave prediction.

Each of the five raw daily fields is expanded into same-day, n-lag, and
trailing rolling-mean variants. Shifts and rolling windows are computed
within a single year so no feature carries information across the
July-August gap between consecutive yearly slabs.
"""
import numpy as np
import pandas as pd
import xarray as xr

RAW_FEATURES = ["t1000_basin_max", "z500", "q700", "u500", "v500"]


def engineer(ds: xr.Dataset, n_lags: int = 3, roll_window: int = 3):
    """Return (X, y, feature_names) for next-day heatwave prediction.

    X has one column per (raw feature × variant) and one row per day with
    enough history to fill every column. y is the heatwave flag of the
    following day. Rows without a same-year next day are dropped.
    """
    df = ds[RAW_FEATURES + ["heatwave"]].to_dataframe().reset_index()
    df["year"] = pd.DatetimeIndex(df["time"]).year

    cols = {}
    for f in RAW_FEATURES:
        cols[f"{f}_t0"] = df[f]
        for lag in range(1, n_lags + 1):
            cols[f"{f}_lag{lag}"] = df.groupby("year")[f].shift(lag)
        cols[f"{f}_roll{roll_window}"] = (
            df.groupby("year")[f]
            .rolling(roll_window, min_periods=roll_window)
            .mean()
            .reset_index(level=0, drop=True)
        )

    feat_df = pd.DataFrame(cols)
    next_day_label = df.groupby("year")["heatwave"].shift(-1)

    full = pd.concat([feat_df, next_day_label.rename("__label__")], axis=1).dropna()
    return (
        full.drop(columns="__label__").values,
        full["__label__"].astype(int).values,
        list(feat_df.columns),
    )
