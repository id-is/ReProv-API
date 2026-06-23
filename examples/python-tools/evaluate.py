#!/usr/bin/env python3
"""Evaluate the heatwave classifier on the held-out 2019-2025 period.

Args:
    labeled_path: path to the labeled NetCDF
    model_path:   path to the joblib bundle from train.py
    results_path: path to write the human-readable metrics file
"""
import sys

import joblib
import xarray as xr
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from features import engineer


def _test_window(ds):
    """Return the held-out subset. 2019-2025 if present, else last 20%."""
    test = ds.sel(time=slice("2019", "2025"))
    if len(test.time) < 2:
        cut = max(2, int(0.8 * len(ds.time)))
        test = ds.isel(time=slice(cut, None))
    return test


def main(labeled_path: str, model_path: str, results_path: str) -> None:
    bundle = joblib.load(model_path)
    model = bundle["model"]
    feature_names = bundle["features"]

    ds = xr.open_dataset(labeled_path)
    test = _test_window(ds)
    X, y, _ = engineer(test)

    proba = model.predict_proba(X)[:, 1]
    pred = (proba >= 0.5).astype(int)

    importances = dict(
        zip(
            feature_names,
            [round(float(x), 4) for x in model.feature_importances_],
        )
    )

    if len(set(y.tolist())) < 2:
        auc = "n/a (single-class test set)"
    else:
        auc = f"{roc_auc_score(y, proba):.4f}"

    with open(results_path, "w") as fh:
        fh.write(f"n_test_days={len(y)}\n")
        fh.write(f"positive_rate={y.mean():.4f}\n")
        fh.write(f"roc_auc={auc}\n")
        fh.write(f"precision={precision_score(y, pred, zero_division=0):.4f}\n")
        fh.write(f"recall={recall_score(y, pred, zero_division=0):.4f}\n")
        fh.write(f"f1={f1_score(y, pred, zero_division=0):.4f}\n")
        fh.write(f"feature_importances={importances}\n")
        fh.write(f"best_params={bundle.get('best_params')}\n")
        fh.write(f"cv_best_score={bundle.get('cv_best_score')}\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
