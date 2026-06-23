#!/usr/bin/env python3
"""Concatenate per-slab daily feature files into one time-sorted dataset.

Args:
    output_path: path for the merged NetCDF
    slab_files:  one or more per-slab .nc files (variadic)
"""
import sys

import numpy as np
import xarray as xr


def main(output_path: str, slab_files: list[str]) -> None:
    datasets = [xr.open_dataset(f) for f in slab_files]
    merged = xr.concat(datasets, dim="time").sortby("time")
    _, idx = np.unique(merged["time"].values, return_index=True)
    merged = merged.isel(time=sorted(idx))
    merged.to_netcdf(output_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
