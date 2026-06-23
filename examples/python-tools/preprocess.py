#!/usr/bin/env python3
"""Aggregate one ERA5 bi-monthly GRIB slab into daily basin-mean features.

Args:
    slab_path:   path to the .grib slab
    output_path: path to write the per-slab daily NetCDF
"""
import sys

import xarray as xr


def daily_basin_mean(ds, var, level, pl_coord):
    return (
        ds[var]
        .sel({pl_coord: level})
        .drop_vars(pl_coord, errors="ignore")
        .mean(dim=["latitude", "longitude"])
        .resample(time="1D")
        .mean()
        .rename(f"{var}{level}")
    )


def main(slab_path: str, output_path: str) -> None:
    ds = xr.open_dataset(
        slab_path,
        engine="cfgrib",
        backend_kwargs={"indexpath": ""},
    )
    pl = "isobaricInhPa" if "isobaricInhPa" in ds.coords else "level"

    t1000_basin = (
        ds["t"]
        .sel({pl: 1000})
        .drop_vars(pl, errors="ignore")
        .mean(dim=["latitude", "longitude"])
    )
    t1000_daily_max = (
        t1000_basin.resample(time="1D").max().rename("t1000_basin_max")
    )

    out = xr.merge([
        t1000_daily_max,
        daily_basin_mean(ds, "z", 500, pl),
        daily_basin_mean(ds, "q", 700, pl),
        daily_basin_mean(ds, "u", 500, pl),
        daily_basin_mean(ds, "v", 500, pl),
    ])
    out.attrs["source_slab"] = slab_path
    out.to_netcdf(output_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
