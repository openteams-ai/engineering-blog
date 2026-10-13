---
title: "What's New in Polars 2.0: Streaming by Default, Map Columns, and Stricter Types"
slug: polars-2-whats-new
date: 2026-10-12
topic: python-tooling
authors:
- khuyen-tran
meta_description: Polars 2.0 makes streaming the default, adds a Map dtype, and tightens types. See what changes in your code, with 1.x and 2.0 outputs side by side on real data.
focus_keyword: Polars 2.0
---

[Polars 2.0](https://pola.rs/posts/release-polars-2) was released on October 6, 2026. The Polars team calls it a "boring" release on purpose: the version bump exists to change defaults, not to add a long list of new APIs.

Boring does not mean nothing breaks. Some of the new defaults change your results without raising an error. This post covers the changes you're most likely to notice, and for each one shows how Polars 1.x behaved and what 2.0 does instead.

## Streaming by Default: Faster Lazy Queries

### Faster collect() With No Code Changes

Polars has two engines for running lazy queries:

```text
in-memory   loads the data it needs, then runs each step on all of it
streaming   splits the data into chunks and processes them in parallel
```

In Polars 1.x, `collect()` used the in-memory engine unless you passed `engine="streaming"`. In 2.0, `collect()` uses the streaming engine by default.

To see the difference, install Polars 2.0 and download one month of [NYC Yellow Taxi trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) plus the taxi zone lookup table:

```bash
pip install polars==2.0.0
curl -o taxi.parquet https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
curl -o taxi_zones.csv https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

*This post uses polars v2.0.0. The 1.x comparisons use polars v1.44.2.*

The query below joins about 3 million trips to their pickup zones, then summarizes tips and trip lengths by borough and hour:

```python
import polars as pl

trips = pl.scan_parquet("taxi.parquet")
zones = pl.scan_csv("taxi_zones.csv")

query = (
    trips.filter(pl.col("fare_amount") > 0, pl.col("trip_distance") > 0)
    .join(zones, left_on="PULocationID", right_on="LocationID")
    .with_columns(
        tip_rate=pl.col("tip_amount") / pl.col("fare_amount"),
        hour=pl.col("tpep_pickup_datetime").dt.hour(),
        minutes=(
            pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime")
        ).dt.total_minutes(),
    )
    .group_by("Borough", "hour")
    .agg(
        pl.len().alias("trips"),
        pl.col("tip_rate").median(),
        pl.col("minutes").quantile(0.9),
        pl.col("total_amount").sum(),
    )
    .sort("Borough", "hour")
)

summary = query.collect()
```

Running `query.collect()` 5 times in fresh processes on each version and taking the median gives:

```text
                 time     peak memory
polars 1.44.2    75 ms    564 MB
polars 2.0.0     52 ms    797 MB    <- 1.4x faster, but more memory
```

The same code runs about 1.4 times faster after the upgrade. On six months of data (about 20 million trips), the gap grows to about 1.7 times.

Peak memory went up, not down, on this machine (64 GB of RAM). The streaming engine keeps buffers for many chunks at once, and with plenty of RAM free, it uses that room. Where streaming helps with memory is when the data no longer fits: see [spill-to-disk](#spill-to-disk-is-on) below.

### Joins No Longer Keep Row Order

The streaming engine finishes chunks in whatever order they're ready. Because of that, a join or group-by no longer returns rows in the input order.

To see this, number each trip with `with_row_index`, join it to the zones, and look at the first 5 rows:

```python
joined = (
    trips.with_row_index("row")
    .join(zones, left_on="PULocationID", right_on="LocationID")
    .select("row", "tpep_pickup_datetime", "Zone")
)
joined.head(5).collect()
```

Polars 1.44.2 returns the first 5 trips of the file:

```text
┌─────┬──────────────────────┬──────────────────────────────┐
│ row ┆ tpep_pickup_datetime ┆ Zone                         │
╞═════╪══════════════════════╪══════════════════════════════╡
│ 0   ┆ 2024-01-01 00:57:55  ┆ Penn Station/Madison Sq West │
│ 1   ┆ 2024-01-01 00:03:00  ┆ Lenox Hill East              │
│ 2   ┆ 2024-01-01 00:17:06  ┆ Upper East Side North        │
│ 3   ┆ 2024-01-01 00:36:38  ┆ East Village                 │
│ 4   ┆ 2024-01-01 00:46:51  ┆ SoHo                         │
└─────┴──────────────────────┴──────────────────────────────┘
```

Polars 2.0 returns rows from the middle of the month. Running it twice gave two different answers:

```text
first run                                  second run
row      tpep_pickup_datetime              row       tpep_pickup_datetime
734007   2024-01-09 20:06:43               1572923   2024-01-18 19:27:34
734013   2024-01-09 20:41:13               1572933   2024-01-18 19:56:27
734033   2024-01-09 20:43:48               1572977   2024-01-18 19:30:55
...                                        ...
```

No error is raised. Code that takes `.head()` after a join, or lines up two results by position, now quietly works on different rows.

To keep the order of the left table, pass `maintain_order="left"`:

```python
ordered = (
    trips.with_row_index("row")
    .join(
        zones,
        left_on="PULocationID",
        right_on="LocationID",
        maintain_order="left",
    )
    .select("row", "tpep_pickup_datetime", "Zone")
)
ordered.head(5).collect()
```

```text
┌─────┬──────────────────────┬──────────────────────────────┐
│ row ┆ tpep_pickup_datetime ┆ Zone                         │
╞═════╪══════════════════════╪══════════════════════════════╡
│ 0   ┆ 2024-01-01 00:57:55  ┆ Penn Station/Madison Sq West │
│ 1   ┆ 2024-01-01 00:03:00  ┆ Lenox Hill East              │
│ 2   ┆ 2024-01-01 00:17:06  ┆ Upper East Side North        │
│ 3   ┆ 2024-01-01 00:36:38  ┆ East Village                 │
│ 4   ┆ 2024-01-01 00:46:51  ┆ SoHo                         │
└─────┴──────────────────────┴──────────────────────────────┘
```

`group_by` takes `maintain_order=True` for the same purpose. If the order only matters at the end, sorting the result explicitly with `.sort()` works too.

### Switch Back to the In-Memory Engine

If a query depends on the old behavior and you can't change it yet, choose the engine per query:

```python
summary = query.collect(engine="in-memory")
```

Or for the whole session:

```python
pl.Config.set_engine_affinity("in-memory")
```

Eager `DataFrame` code, such as `pl.read_parquet(...).filter(...)`, is not affected by any of this. It runs on the in-memory engine as before.

## Stricter Types: Fewer Silent Conversions

Polars 1.x converted between some types on its own, sometimes losing information along the way. Polars 2.0 either asks you to convert explicitly or picks a type that keeps the exact value.

### Casting Strings to Dates

Say a column of pickup dates arrived as strings:

```python
dates = pl.DataFrame({"pickup_date": ["2024-01-15", "2024-01-16"]})
dates.with_columns(pl.col("pickup_date").cast(pl.Date))
```

Polars 1.44.2 converts it, with a deprecation warning. Polars 2.0 raises an error that names the fix:

```text
InvalidOperationError: casting from string to date is not supported.
It was removed in Polars 2.0. Use `str.to_date()` instead.
```

`str.to_date` takes the format, so a file with `01/15/2024` style dates fails loudly instead of being guessed:

```python
dates.with_columns(pl.col("pickup_date").str.to_date("%Y-%m-%d"))
```

```text
┌─────────────┐
│ pickup_date │
│ ---         │
│ date        │
╞═════════════╡
│ 2024-01-15  │
│ 2024-01-16  │
└─────────────┘
```

### Mixing Int64 and UInt64

Adding a signed and an unsigned 64-bit integer used to produce a float. A float can't store every integer above 2^53 exactly, so large IDs were rounded:

```python
ids = pl.DataFrame({
    "trip_id": pl.Series([2**53 + 1], dtype=pl.Int64),
    "offset": pl.Series([0], dtype=pl.UInt64),
})
ids.select(pl.col("trip_id") + pl.col("offset")).item()
```

```text
polars 1.44.2   9007199254740992.0   Float64   <- off by one
polars 2.0.0    9007199254740993     Int128    <- exact
```

Polars 2.0 uses `Int128`, which holds both ranges exactly. The values are now correct, but the column type downstream changes too. A schema check that expects `Float64` will need updating.

### Matching Integers Against Floats in is_in

`is_in` now requires the values to match the column's type. A common way to hit this: zone IDs read from a pandas column that had missing values, which turns them into floats.

```python
trips_sample = pl.DataFrame(
    {"PULocationID": [132, 138, 161]}, schema={"PULocationID": pl.Int32}
)
airport_ids = [132.0, 138.0]  # floats from a pandas column with NaN
trips_sample.filter(pl.col("PULocationID").is_in(airport_ids))
```

Polars 1.44.2 converts the values and filters. Polars 2.0 stops:

```text
InvalidOperationError: 'is_in' cannot check for Int32 values in List(Float64) data.
```

Convert the IDs to integers first, so a value like `138.5` can't slip in unnoticed:

```python
airport_ids = [int(zone_id) for zone_id in airport_ids]
trips_sample.filter(pl.col("PULocationID").is_in(airport_ids))
```

```text
┌──────────────┐
│ PULocationID │
│ ---          │
│ i32          │
╞══════════════╡
│ 132          │
│ 138          │
└──────────────┘
```

## Map Columns: Look Up Keys Without Exploding

Some data stores a dictionary per row. A common example is experiment tracking, where each run logs a different set of metrics:

```text
run        metrics
baseline   {"accuracy": 0.91, "f1": 0.88}
xgboost    {"accuracy": 0.87, "auc": 0.93}
small_lr   {"f1": 0.79}
```

Parquet and Arrow store this as a map type. To follow along, write the table above to Parquet with PyArrow:

```python
import pyarrow as pa
import pyarrow.parquet as pq

metrics = pa.array(
    [
        [("accuracy", 0.91), ("f1", 0.88)],
        [("accuracy", 0.87), ("auc", 0.93)],
        [("f1", 0.79)],
    ],
    type=pa.map_(pa.string(), pa.float64()),
)
table = pa.table({
    "run": ["baseline", "xgboost", "small_lr"],
    "metrics": metrics,
    "primary_metric": ["f1", "auc", "f1"],
})
pq.write_table(table, "runs.parquet")
```

*This section also uses pyarrow v26.0.0.*

Polars 1.x read a map column as a list of key-value structs:

```text
metrics: List(Struct({'key': String, 'value': Float64}))

[{"accuracy",0.91}, {"f1",0.88}]
```

Getting one metric out meant filtering that list:

```python
runs.with_columns(
    accuracy=pl.col("metrics")
    .list.eval(
        pl.element()
        .filter(pl.element().struct.field("key") == "accuracy")
        .struct.field("value")
    )
    .list.first()
)
```

Polars 2.0 reads it as a `Map`:

```python
runs = pl.read_parquet("runs.parquet")
runs
```

```text
┌──────────┬─────────────────────────────────┬────────────────┐
│ run      ┆ metrics                         ┆ primary_metric │
│ ---      ┆ ---                             ┆ ---            │
│ str      ┆ map[str, f64]                   ┆ str            │
╞══════════╪═════════════════════════════════╪════════════════╡
│ baseline ┆ {"accuracy": 0.91, "f1": 0.88}  ┆ f1             │
│ xgboost  ┆ {"accuracy": 0.87, "auc": 0.93} ┆ auc            │
│ small_lr ┆ {"f1": 0.79}                    ┆ f1             │
└──────────┴─────────────────────────────────┴────────────────┘
```

Look up a key with `map.get`, just like a Python dict. A run without that key gets `null`:

```python
runs.with_columns(accuracy=pl.col("metrics").map.get("accuracy")).select(
    "run", "accuracy"
)
```

```text
┌──────────┬──────────┐
│ run      ┆ accuracy │
│ ---      ┆ ---      │
│ str      ┆ f64      │
╞══════════╪══════════╡
│ baseline ┆ 0.91     │
│ xgboost  ┆ 0.87     │
│ small_lr ┆ null     │
└──────────┴──────────┘
```

The key can also come from another column. Here each run reports the metric named in its `primary_metric` column:

```python
runs.with_columns(
    primary=pl.col("metrics").map.get(pl.col("primary_metric"))
).select("run", "primary_metric", "primary")
```

```text
┌──────────┬────────────────┬─────────┐
│ run      ┆ primary_metric ┆ primary │
│ ---      ┆ ---            ┆ ---     │
│ str      ┆ str            ┆ f64     │
╞══════════╪════════════════╪═════════╡
│ baseline ┆ f1             ┆ 0.88    │
│ xgboost  ┆ auc            ┆ 0.93    │
│ small_lr ┆ f1             ┆ 0.79    │
└──────────┴────────────────┴─────────┘
```

`map.keys`, `map.len`, and `map.contains_key` cover the other dict operations. For example, to keep only the runs that logged AUC:

```python
runs.filter(pl.col("metrics").map.contains_key("auc")).select("run")
```

```text
┌─────────┐
│ run     │
│ ---     │
│ str     │
╞═════════╡
│ xgboost │
└─────────┘
```

## Smaller Changes Worth Knowing

### Spill-to-Disk Is On

When memory use reaches about 80% of RAM, Polars 2.0 now writes intermediate data to disk to finish the query instead of crashing. This covers sorts, window functions, and many expressions, with a default disk budget of 64 GB. Joins and group-bys can't spill yet; the Polars team lists them as next.

### SQL Runs on the Streaming Engine

`pl.sql` and `SQLContext` existed in 1.x. In 2.0, SQL queries also run on the streaming engine by default, so the speed-up and the row-order change above apply to them too. Add `ORDER BY` if you rely on the order of the result.

### read_csv Loses Old Arguments

`pl.read_csv` now runs `pl.scan_csv(...).collect()` under the hood. The `n_threads`, `batch_size`, `sample_size`, and `rechunk` arguments are gone, and `dtypes` now raises:

```text
polars 1.44.2   pl.read_csv(path, dtypes={...})   DeprecationWarning, still works
polars 2.0.0    pl.read_csv(path, dtypes={...})   ArgumentRemovedError: ... renamed to 'schema_overrides'
```

### explode Drops Empty Lists

`explode` used to turn an empty list into a `null` row. In 2.0, the row disappears:

```python
stops = pl.DataFrame({"trip": [1, 2], "stops": [[10, 11], []]})
stops.explode("stops")
```

```text
polars 1.44.2         polars 2.0.0
trip  stops           trip  stops
1     10              1     10
1     11              1     11
2     null            <- trip 2 is gone
```

Pass `empty_as_null=True` to keep the old behavior, for example when counting trips after an explode.

### cut and qcut Are Deprecated

`cut` still works but warns. Its replacement, `bin_intervals`, closes bins on the left by default, while `cut` closed them on the right. A fare of exactly 10 lands in a different bin:

```python
fares = pl.DataFrame({"fare": [5.0, 10.0, 80.0]})
fares.with_columns(
    cut=pl.col("fare").cut([10, 50]),
    bin_intervals=pl.col("fare").bin_intervals(
        [10, 50], labels=["short", "medium", "long"]
    ),
)
```

```text
┌──────┬────────────┬───────────────┐
│ fare ┆ cut        ┆ bin_intervals │
╞══════╪════════════╪═══════════════╡
│ 5.0  ┆ (-inf, 10] ┆ short         │
│ 10.0 ┆ (-inf, 10] ┆ medium        │  <- different bin
│ 80.0 ┆ (50, inf]  ┆ long          │
└──────┴────────────┴───────────────┘
```

Pass `right_closed=True` to `bin_intervals` to match the old `cut` bins.

### LazyFrame.profile() Is Removed

`profile()` timed each step of the in-memory engine. The streaming engine runs steps at the same time, so per-step timings would be misleading, and the method is gone.

## Final Thoughts

After upgrading to Polars 2.0, here are some things to check:

- Search your code for `.head()`, `.first()`, or position-based logic after a `join` or `group_by`, and add `maintain_order` or a `.sort()` where order matters.
- Run your test suite and replace each `.cast(pl.Date)` on a string column with `str.to_date()` and an explicit format.
- If you read Parquet or Arrow files with map columns, replace the `list.eval` lookups with `map.get`.
- If a query has to behave exactly as before while you migrate, run it with `collect(engine="in-memory")`.

## References

- **[Release of Polars 2.0](https://pola.rs/posts/release-polars-2)** (Ritchie Vink, 2026): release date, spill-to-disk threshold and disk budget, Map dtype, and SQL changes.
- **[Pre-release of Polars 2.0](https://pola.rs/posts/announcing-polars-2)** (Ritchie Vink, 2026): why the version bump, and which operations lose row order on the streaming engine.
- **[Polars 2 upgrade guide](https://docs.pola.rs/releases/upgrade/2/)** (Polars, 2026): the full list of breaking changes covered in this article.
- **[py-2.0.0 release notes](https://github.com/pola-rs/polars/releases/tag/py-2.0.0)** (Polars, 2026): changelog and performance changes.
- **[TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)** (NYC Taxi and Limousine Commission): the January 2024 Yellow Taxi data and zone lookup used in the examples, published under the NYC Open Data terms of use.
