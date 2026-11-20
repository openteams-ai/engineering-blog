---
title: "Write One DataFrame Function for pandas, Polars, DuckDB, and DataFusion with Narwhals"
slug: narwhals-one-function-any-dataframe
date: 2026-11-15
topic: python-tooling
authors:
- khuyen-tran
meta_description: "Write one Narwhals function for pandas, Polars, DuckDB, or DataFusion. Test it on every backend, turn it into SQL, and keep it working across upgrades."
focus_keyword: narwhals
---

Let's say you write a small helper that fills missing sales values for each store. You write it in pandas, and it works.

Then a teammate wants to call it on a Polars DataFrame. Another one keeps their data in DuckDB. A third one just moved to DataFusion. Each new caller adds another branch.

```python
def ffill_by_store(df):
    if isinstance(df, pd.DataFrame):
        ...  # pandas code
    elif isinstance(df, pl.DataFrame):
        ...  # Polars code
    elif isinstance(df, duckdb.DuckDBPyRelation):
        ...  # SQL
    elif ...:
        ...  # one more library, one more branch
```

Every branch is code to maintain and test. And when the branches disagree in a small way, nobody notices until a number looks wrong.

In this article, you will learn Narwhals's features by building a store-sales helper that works with any of these libraries and keeps working when those libraries change.

> 💻 **Get the Code**: The functions and tests are on [GitHub](https://github.com/khuyentran1401/codecut-blog/tree/main/narwhals-one-function-any-dataframe).

## What Is Narwhals?

[Narwhals](https://github.com/narwhals-dev/narwhals) is a lightweight layer that lets you write dataframe code once and run it on many libraries.

You write your logic with a subset of the Polars API. Narwhals translates it into each library's own calls, so pandas code runs as pandas and DuckDB code runs as SQL.

For more background, see [Narwhals: Unified DataFrame Functions for pandas, Polars, and PySpark](https://codecut.ai/unified-dataframe-functions-pandas-polars-pyspark/) and [Writing Portable DataFrame Code for Eager and Lazy Execution](https://codecut.ai/eager-to-lazy-dataframes-with-narwhals/).

## Setup

Install Narwhals with the libraries used in this article.

```bash
pip install "narwhals>=2.28" pandas polars duckdb pyarrow sqlparse datafusion narwhals-datafusion
```

*This article uses narwhals v2.28.0, pandas v3.1.1, polars v2.1.0, duckdb v2.0.0, datafusion v55.0.0, and narwhals-datafusion v0.2.0.*

Narwhals 2.28 or later covers every feature in this article.

The examples use six rows of store sales. Two `sales` values are missing.

```python
from datetime import datetime

data = {
    "sale_date": [datetime(2025, 5, day) for day in (22, 23, 24, 22, 23, 24)],
    "store": ["Thimphu"] * 3 + ["Paro"] * 3,
    "sales": [1100, None, 1450, 501, 500, None],
}
```

Create the same data in each library.

```python
import duckdb
import pandas as pd
import polars as pl

df_pandas = pd.DataFrame(data)
df_polars = pl.DataFrame(data)
lf_polars = pl.LazyFrame(data)
duckdb_rel = duckdb.sql("SELECT * FROM df_polars")
```

## Accept Any DataFrame

Start with a forward-fill function. It fills each missing `sales` value with the previous value from the same store.

```python
import narwhals as nw
from narwhals.typing import IntoFrameT

def ffill_by_store(df_native: IntoFrameT) -> IntoFrameT:
    return (
        nw.from_native(df_native)
        .with_columns(
            nw.col("sales")
            .fill_null(strategy="forward")
            .over("store", order_by="sale_date")
        )
        .to_native()
    )
```

The function has three steps:

- `from_native` wraps whatever dataframe the caller passes in
- The Narwhals expression does the work
- `to_native` hands back the caller's own type

If you prefer less boilerplate, the `@nw.narwhalify` decorator does the wrapping and unwrapping for you.

```text
 caller passes              Narwhals                caller gets back
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ pandas DataFrame │    │                  │    │ pandas DataFrame │
│ Polars DataFrame │ ─> │  ffill_by_store  │ ─> │ Polars DataFrame │
│ Polars LazyFrame │    │   (one version)  │    │ Polars LazyFrame │
│ DuckDB relation  │    │                  │    │ DuckDB relation  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

Each input comes back as the same type it went in.

```python
for df in [df_pandas, df_polars, lf_polars, duckdb_rel]:
    print(type(ffill_by_store(df)))
```

```text
<class 'pandas.DataFrame'>
<class 'polars.dataframe.frame.DataFrame'>
<class 'polars.lazyframe.frame.LazyFrame'>
<class 'duckdb._relation.DuckDBPyRelation'>
```

Lazy inputs stay lazy. The Polars LazyFrame and the DuckDB relation are not computed until the caller asks for the result.

The `order_by="sale_date"` part tells lazy backends which row comes before which. [Aggregate in a Fixed Order](#aggregate-in-a-fixed-order) shows why that matters.

## Filter Rows by Group

A common question is "what is each store's most recent row?" Every library answers it differently:

- In pandas, you compute the max date with `groupby().transform()` and build a mask
- In SQL, you need a subquery or `QUALIFY`
- In Polars, you filter with a window expression

With Narwhals, you write it once as a filter with a window expression. `max().over("store")` gives each row its store's latest date, and the filter keeps the rows that match.

```python
def latest_sale_per_store(df_native: IntoFrameT) -> IntoFrameT:
    return (
        nw.from_native(df_native)
        .filter(nw.col("sale_date") == nw.col("sale_date").max().over("store"))
        .to_native()
    )
```

Run it on DuckDB.

```python
latest_sale_per_store(duckdb_rel)
```

```text
┌─────────────────────┬─────────┬───────┐
│      sale_date      │  store  │ sales │
│      timestamp      │ varchar │ int64 │
├─────────────────────┼─────────┼───────┤
│ 2025-05-24 00:00:00 │ Paro    │  NULL │
│ 2025-05-24 00:00:00 │ Thimphu │  1450 │
└─────────────────────┴─────────┴───────┘
```

The same function gives the same rows on pandas.

```python
latest_sale_per_store(df_pandas)
```

```text
   sale_date    store   sales
2 2025-05-24  Thimphu  1450.0
5 2025-05-24     Paro     NaN
```

This is nice for several reasons:

- One expression replaces a pandas mask and a SQL subquery
- On DuckDB, Narwhals turns it into SQL, so the data never leaves the database
- Ordered windows work too, such as `cum_sum().over("store", order_by="sale_date")`

## Aggregate in a Fixed Order

Now let's say you want each store's last sales value. In pandas, `last()` works because the rows have a fixed order. On DuckDB, the same call has no clear meaning, since the rows can come back in any order.

Narwhals refuses to guess. Calling `last()` on DuckDB raises an error that tells you how to fix it.

```python
nw.from_native(duckdb_rel).group_by("store").agg(nw.col("sales").last())
```

```text
InvalidOperationError: Order-dependent expressions are not supported for use in LazyFrame.

Hint: To make the expression valid, specify `order_by`.
...
 - Instead of `nw.col('price').first()` write `nw.col('price').first().over(order_by='date')`
   or `nw.col('price').first(order_by='date')`.
```

Pass `order_by` to say which column defines "last". The same rule is why `ffill_by_store` passes `order_by="sale_date"`: "the previous value" only means something once you say which column sets the order.

```python
def last_sale_per_store(df_native: IntoFrameT) -> IntoFrameT:
    return (
        nw.from_native(df_native)
        .group_by("store")
        .agg(nw.col("sales").last(order_by="sale_date"))
        .sort("store")
        .to_native()
    )

last_sale_per_store(duckdb_rel)
```

```text
┌─────────┬───────┐
│  store  │ sales │
│ varchar │ int64 │
├─────────┼───────┤
│ Paro    │  NULL │
│ Thimphu │  1450 │
└─────────┴───────┘
```

Paro's last sale is missing in the raw data. Since both functions take and return any dataframe, you can fill the gaps first and then take the last value.

```python
last_sale_per_store(ffill_by_store(duckdb_rel))
```

```text
┌─────────┬───────┐
│  store  │ sales │
│ varchar │ int64 │
├─────────┼───────┤
│ Paro    │   500 │
│ Thimphu │  1450 │
└─────────┴───────┘
```

This is nice for several reasons:

- The result is the same on every backend, because the order is stated in the code
- Code that quietly relied on pandas row order fails loudly on a lazy backend instead of giving a different answer
- Small functions like these chain together, and the whole chain stays lazy on DuckDB

## Test the Function on Every Backend

A function that claims to support four libraries needs a test that runs on all four. Each library has its own assert helper, but none of them compare a pandas result with a DuckDB result.

Narwhals has one that does. `narwhals.testing.assert_frame_equal` compares two Narwhals frames from any backend.

To compare results from different libraries, the test first converts each result to Polars with `.lazy().collect(backend="polars")`. `check_row_order=False` skips the row-order check, since DuckDB may return rows in any order.

```python
from narwhals.testing import assert_frame_equal

expected = nw.from_native(
    pl.DataFrame({**data, "sales": [1100, 1100, 1450, 501, 500, 500]})
)
backends = {
    "pandas": df_pandas,
    "polars": df_polars,
    "polars lazy": lf_polars,
    "duckdb": duckdb_rel,
}

for name, df in backends.items():
    result = nw.from_native(ffill_by_store(df)).lazy().collect(backend="polars")
    try:
        assert_frame_equal(result, expected, check_row_order=False)
        print(f"{name}: OK")
    except AssertionError as error:
        print(f"{name}: {error}")
```

```text
pandas: DataFrames are different (dtypes do not match)
[left]: [Datetime(time_unit='us', time_zone=None), String, Float64]
[right]: [Datetime(time_unit='us', time_zone=None), String, Int64]
polars: OK
polars lazy: OK
duckdb: OK
```

The test caught something the printed output would hide. pandas stores the missing values as `NaN`, which turns the whole `sales` column into floats. The values match, but pandas callers get `1100.0` while everyone else gets `1100`.

There are two ways to make this test pass:

- Pass `check_dtypes=False` to the test, which accepts the difference
- Cast the column in the function, which removes the difference

I prefer the cast. Callers should get the same type no matter which library they use. Add `.cast(nw.Int64)` after the fill.

```python
def ffill_by_store(df_native: IntoFrameT) -> IntoFrameT:
    return (
        nw.from_native(df_native)
        .with_columns(
            nw.col("sales")
            .fill_null(strategy="forward")
            .over("store", order_by="sale_date")
            .cast(nw.Int64)
        )
        .to_native()
    )
```

Running the same loop again, every backend passes.

```text
pandas: OK
polars: OK
polars lazy: OK
duckdb: OK
```

The [example repo](https://github.com/khuyentran1401/codecut-blog/tree/main/narwhals-one-function-any-dataframe) turns this loop into a pytest suite with `pytest.mark.parametrize`, one test case per backend.

This is nice for several reasons:

- One test covers every library the function claims to support
- The error message names the problem, such as `dtypes do not match` or `value mismatch for column "sales"`
- Differences between libraries show up in the test instead of in a teammate's report

## Add a Library with a Plugin

So far, the function works with the libraries Narwhals supports out of the box. But the list is not fixed. Any package can add a new backend to Narwhals as a plugin, and Narwhals finds it when it is installed.

[DataFusion](https://datafusion.apache.org/python/) is a good example. It is a fast query engine from the Apache Arrow project, and Narwhals itself points to its plugin. Pass a DataFusion DataFrame to the function without the plugin, and Narwhals tells you what to install.

```python
from datafusion import SessionContext

ctx = SessionContext()
datafusion_df = ctx.from_pydict(data)
ffill_by_store(datafusion_df)
```

```text
TypeError: Unsupported dataframe type, got: <class 'datafusion.dataframe.DataFrame'>

Hint: it looks like you passed a `datafusion.DataFrame` but don't have `narwhals-datafusion` installed.
Please refer to https://github.com/s5dsn-eqee/narwhals-datafusion for installation instructions.
```

Install the plugin.

```bash
pip install narwhals-datafusion
```

*This article uses narwhals-datafusion v0.2.0.*

Now the same function, with no edits, accepts the DataFusion DataFrame and returns one.

```python
from datafusion import col

result = ffill_by_store(datafusion_df)
print(type(result))
result.sort(col("store"), col("sale_date"))
```

```text
<class 'datafusion.dataframe.DataFrame'>
+---------------------+---------+-------+
| sale_date           | store   | sales |
+---------------------+---------+-------+
| 2025-05-22T00:00:00 | Paro    | 501   |
| 2025-05-23T00:00:00 | Paro    | 500   |
| 2025-05-24T00:00:00 | Paro    | 500   |
| 2025-05-22T00:00:00 | Thimphu | 1100  |
| 2025-05-23T00:00:00 | Thimphu | 1100  |
| 2025-05-24T00:00:00 | Thimphu | 1450  |
+---------------------+---------+-------+
```

The other two functions work the same way.

```python
last_sale_per_store(ffill_by_store(datafusion_df))
```

```text
+---------+-------+
| store   | sales |
+---------+-------+
| Paro    | 500   |
| Thimphu | 1450  |
+---------+-------+
```

This is nice for several reasons:

- Supporting a new library takes one `pip install`, with no change to your functions
- Your existing tests can add the new backend as one more case
- Library authors can build their own plugins instead of waiting for Narwhals to add support

The plugin system is still marked experimental, so expect some details to change between releases.

## Generate SQL from the Same Code

Sometimes the logic has to live in SQL, such as a dbt model or a warehouse view. Usually that means writing it a second time by hand.

`narwhals.sql` gives you a table with a schema and no data. You write the same Narwhals expression on it, and `to_sql()` returns the query.

```python
from narwhals.sql import table

sales = table(
    "sales",
    {"sale_date": nw.Datetime(), "store": nw.String(), "sales": nw.Int64()},
)
query = sales.with_columns(
    nw.col("sales").fill_null(strategy="forward").over("store", order_by="sale_date")
)
print(query.to_sql(pretty=True))
```

```text
SELECT "sale_date",
       "store",
       (last_value("sales"
                   IGNORE nulls) OVER (PARTITION BY "store"
                                       ORDER BY "sale_date" ASC NULLS FIRST ROWS BETWEEN UNBOUNDED PRECEDING AND 0 FOLLOWING)) AS "sales"
FROM "sales"
```

This is nice for several reasons:

- You don't need any data or a database connection to get the query
- The window frame (`ROWS BETWEEN UNBOUNDED PRECEDING ...`) is written for you, and it is easy to get wrong by hand
- The same expression still runs as Python on any backend

`narwhals.sql` needs DuckDB installed, and the query follows DuckDB's SQL. Check that it runs on your warehouse before you ship it. `pretty=True` needs `sqlparse`.

## Upgrade Engines Without Changing Your Code

Polars 2.0 and DuckDB 2.0 came out in October 2026, two weeks apart. Both changed behavior that existing code relied on.

Narwhals code is protected from part of that. Narwhals translates your code into each library's calls, so when a library changes, the Narwhals maintainers update the translation and you upgrade Narwhals.

Take `explode` in Polars 2.0. A list column with an empty list used to produce a row with a null. Now that row disappears, with no warning.

```python
promos = pl.DataFrame(
    {"store": ["Thimphu", "Paro"], "promo": [["spring", "loyalty"], []]}
)
promos.explode("promo")
```

```text
┌─────────┬─────────┐
│ store   ┆ promo   │
│ ---     ┆ ---     │
│ str     ┆ str     │
╞═════════╪═════════╡
│ Thimphu ┆ spring  │
│ Thimphu ┆ loyalty │
└─────────┴─────────┘
```

Paro is gone. The same call through Narwhals keeps it:

```python
nw.from_native(promos).explode("promo").to_native()
```

```text
┌─────────┬─────────┐
│ store   ┆ promo   │
│ ---     ┆ ---     │
│ str     ┆ str     │
╞═════════╪═════════╡
│ Thimphu ┆ spring  │
│ Thimphu ┆ loyalty │
│ Paro    ┆ null    │
└─────────┴─────────┘
```

On Polars 1.44, both calls return the three rows. Narwhals added this fix in version 2.23, before Polars 2.0 came out.

DuckDB 2.0 changed how relations reference columns, which broke joins in Narwhals 2.27. Narwhals 2.28 fixed it and kept DuckDB 1.x working. The join code itself did not change:

```python
sales = duckdb.sql("SELECT * FROM (VALUES ('Paro', 500), ('Thimphu', 1450)) t(store, sales)")
stores = duckdb.sql("SELECT * FROM (VALUES ('Paro', 'West'), ('Thimphu', 'Central')) t(store, region)")

nw.from_native(sales).join(nw.from_native(stores), on="store").to_native()
```

```text
narwhals 2.27.1 + duckdb 2.0.0   BinderException: Referenced column "lhs."store"" not found
narwhals 2.28.0 + duckdb 2.0.0   [('Paro', 500, 'West'), ('Thimphu', 1450, 'Central')]
```

There is a limit. Narwhals translates method calls, but it does not change a library's type rules. Polars 2.0 no longer casts strings to dates, so `nw.col("date").cast(nw.Date)` fails the same way it does in plain Polars. Use `nw.col("date").str.to_date("%Y-%m-%d")`, which works on both versions.

## Protect Your Users with stable.v2

The previous section is about Polars and DuckDB changing. Narwhals changes too. If other people install your code, a Narwhals upgrade should not break it either.

Narwhals promises never to change or remove any public function in `narwhals.stable.v2`. Breaking changes go to the main `narwhals` namespace first. To get that promise, change one import:

```python
import narwhals.stable.v2 as nw
```

`ffill_by_store` and `latest_sale_per_store` work unchanged with this import. New features reach the main namespace first, though. At the time of writing, `last()` in `stable.v2` does not accept `order_by` yet:

```text
TypeError: Expr.last() got an unexpected keyword argument 'order_by'
```

A simple rule: libraries and shared packages import `narwhals.stable.v2`, while scripts and notebooks import `narwhals` to get the newest methods.

## Final Thoughts

What I like about Narwhals is that it lets me write a function once without deciding for my users which library they should use. pandas users stay in pandas, DuckDB users keep their data in the database, and nobody waits for a conversion they did not ask for.

The test helper is the part I would not skip. It caught a dtype difference that I would never have spotted by reading the output.

For code other people run, the upgrade story matters just as much. `stable.v2` keeps Narwhals' own API fixed, and the Narwhals maintainers keep up with releases like Polars 2.0 and DuckDB 2.0 so you don't have to.

Narwhals is not the right fit for everything. If your work is mostly SQL against a database rather than functions that accept any dataframe, [Ibis](https://codecut.ai/ibis-vs-narwhals-vs-fugue-dataframe-portability/) is a better fit.

## References

- **[Perfect backwards compatibility policy](https://narwhals-dev.github.io/narwhals/backcompat/)** (Narwhals docs): the promise never to change or remove public functions in `stable.v1` and `stable.v2`, with breaking changes going to the main namespace first.
- **[Order dependence](https://narwhals-dev.github.io/narwhals/concepts/order_dependence/)** (Narwhals docs): why lazy backends need `order_by` for ordered operations.
- **[narwhals.testing API reference](https://narwhals-dev.github.io/narwhals/api-reference/testing/)** (Narwhals docs): `assert_frame_equal` options such as `check_row_order` and `check_dtypes`.
- **[Extensions and plugins](https://narwhals-dev.github.io/narwhals/extending/)** (Narwhals docs): how a package registers a backend through the `narwhals.plugins` entry point.
- **[Narwhals 2.16.0 release notes](https://github.com/narwhals-dev/narwhals/releases/tag/v2.16.0)** (Narwhals, 2026): window functions in `filter`, `order_by` in `first` and `last`, and `assert_frame_equal`, which set the minimum version in Setup.
- **[narwhals-datafusion](https://github.com/s5dsn-eqee/narwhals-datafusion)** (2026): the DataFusion backend plugin used in the plugin section.
- **[narwhals.sql API reference](https://narwhals-dev.github.io/narwhals/api-reference/sql/)** (Narwhals docs): `table()` and `to_sql()`, and the DuckDB requirement.
- **[Polars 2.0 upgrade guide](https://docs.pola.rs/releases/upgrade/2/)** (Polars, 2026): the `explode` default change and the removed string-to-date casts.
- **[fix: explicitly use `empty_as_null=True` in `explode` for Polars (#3718)](https://github.com/narwhals-dev/narwhals/pull/3718)** (Narwhals, 2026): why Narwhals keeps the old `explode` behavior on Polars 2.0.
- **[fix: support DuckDB 2.0 in joins, time zone lookup and `from_native` typing (#4099)](https://github.com/narwhals-dev/narwhals/pull/4099)** (Narwhals, 2026): the DuckDB 2.0 join fix in Narwhals 2.28.
