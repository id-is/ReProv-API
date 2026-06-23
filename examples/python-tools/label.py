#!/usr/bin/env python3
"""Add a binary heatwave label using the 90th-percentile / 3-consecutive-day rule.

The threshold is calibrated on the 1997-2018 climatology subset so the
label is comparable across the entire 1997-2025 record.

Args:
    merged_path: path to the merged daily NetCDF
    output_path: path to write the labeled NetCDF
"""
import sys

import numpy as np
import xarray as xr


def main(merged_path: str, output_path: str) -> None:
    ds = xr.open_dataset(merged_path)
    clim = ds["t1000_basin_max"].sel(time=slice("1997", "2018"))
    threshold = float(clim.quantile(0.90).values)

    hot_day = (ds["t1000_basin_max"] > threshold).astype("int8").values
    heatwave = np.zeros_like(hot_day)
    run = 0
    for i, v in enumerate(hot_day):
        run = run + 1 if v else 0
        if run >= 3:
            heatwave[i - 2 : i + 1] = 1

    ds = ds.assign(heatwave=("time", heatwave))
    ds.attrs["heatwave_threshold_K"] = threshold
    ds.attrs["heatwave_rule"] = "T1000_basin_max > P90(1997-2018) for >=3 consecutive days"
    ds.to_netcdf(output_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
