#!/usr/bin/env python3
"""Train a gradient-boosted classifier for next-day Mediterranean heatwave.

Training period: 1997-2018 inclusive. Today's features (with lags and
3-day rolling means) predict tomorrow's heatwave flag.

Args:
    labeled_path: path to the labeled NetCDF
    model_path:   path to write the joblib bundle
"""
import sys

import joblib
import xarray as xr
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit

from features import engineer

PARAM_GRID = {
    "n_estimators": [1500, 3000, 6000],
    "max_depth": [6, 8],
    "learning_rate": [0.05, 0.1],
}


def _train_window(ds):
    """Return the training subset. 1997-2018 if present, else first 80%."""
    train = ds.sel(time=slice("1997", "2018"))
    if len(train.time) < 2:
        cut = max(2, int(0.8 * len(ds.time)))
        train = ds.isel(time=slice(0, cut))
    return train


def main(labeled_path: str, model_path: str) -> None:
    ds = xr.open_dataset(labeled_path)
    train = _train_window(ds)
    X, y, feature_names = engineer(train)

    base = GradientBoostingClassifier(random_state=42)
    cv = TimeSeriesSplit(n_splits=10)
    search = GridSearchCV(
        base, PARAM_GRID, cv=cv, scoring="roc_auc", n_jobs=1, refit=True
    )
    search.fit(X, y)

    joblib.dump(
        {
            "model": search.best_estimator_,
            "features": feature_names,
            "best_params": search.best_params_,
            "cv_best_score": float(search.best_score_),
        },
        model_path,
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
