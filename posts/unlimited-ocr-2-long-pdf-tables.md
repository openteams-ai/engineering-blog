---
title: "Parse Long PDFs Without Breaking Tables Using Unlimited-OCR-2"
slug: unlimited-ocr-2-long-pdf-tables
date: 2026-11-02
topic: ai-engineering
authors:
  - khuyen-tran
meta_description: "Unlimited-OCR-2 reads many PDF pages in one request, so tables split across pages come back as one DataFrame. Run it on a Mac and check what it misses."
focus_keyword: "Unlimited-OCR-2"
---

Have you ever pulled a table out of a long PDF report, only to find it split into two DataFrames because it crossed a page break? The second half usually starts with a title like "Table 5.3—continued" and the column headers again, sitting in your data as ordinary rows.

This happens because most OCR models read one page at a time. Each page is parsed on its own, so the model has no idea that the table at the top of page 72 is the rest of the table at the bottom of page 71.

Fixing it by hand means finding every continued table, deleting the repeated title and header rows, and concatenating the pieces. In a 200-page report with a dozen split tables, that adds up quickly.

In this article, you will learn Unlimited-OCR-2's features by parsing the Federal Reserve's 2024 Annual Report on a Mac.

> 💻 **Get the Code**: The scripts for every example are on [GitHub](https://github.com/khuyentran1401/codecut-blog/tree/main/unlimited-ocr-2-vs-deepseek-ocr-2).

## What Is Unlimited-OCR-2?

[Unlimited-OCR-2](https://huggingface.co/baidu/Unlimited-OCR-2) is an open-source document parsing model from Baidu that reads many pages in one request.

It is built on DeepSeek-OCR and has the same size as [DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2), with 3B parameters and 0.5B active per token. The difference is how they read a document.

```text
DeepSeek-OCR-2     page 71 -> request 1
                   page 72 -> request 2        <- each page alone

Unlimited-OCR-2    page 71 + page 72 -> one request   <- sees where the table continues
```

Throughout this article, DeepSeek-OCR-2 serves as the page-by-page baseline, so you can see what reading the whole document changes.

## Setup

Baidu's own inference code needs an NVIDIA GPU. On a Mac, the MLX conversions of both models run through [mlx-vlm](https://github.com/Blaizzy/mlx-vlm).

```bash
pip install mlx-vlm==0.7.11 pymupdf pandas lxml
```

*This article uses mlx-vlm v0.7.11, PyMuPDF v2.0, and pandas v3.1.0.*

The running example is the [Federal Reserve's 2024 Annual Report](https://www.federalreserve.gov/publications/files/2024-annual-report.pdf), a 214-page public domain report with 16 pages where a table continues from the previous page. Each page is rendered to a PNG with PyMuPDF before it goes to the model.

Baidu's Markdown converter is a single Python file that you download next to your code. Follow the rest of the setup instructions, including downloading the report and the converter, in the [example README](https://github.com/khuyentran1401/codecut-blog/tree/main/unlimited-ocr-2-vs-deepseek-ocr-2#setup).

## Parse Many Pages in One Request

Table 5.3 of the report starts on page 71 and continues on page 72, with its header repeated.

![Table 5.3 split across pages 71 and 72](images/unlimited-ocr-2-long-pdf-tables/case1-table-5-3-break.png)

To parse both pages together, pass both images to `mlx_vlm.generate` with the prompt `Multi page parsing.`

```bash
mlx_vlm.generate --model mlx-community/Unlimited-OCR-2-8bit \
  --image p071.png p072.png \
  --prompt "Multi page parsing." --max-tokens 60000 --temperature 0
```

The output has one `<PAGE>` section per image. Each block on a page gets a label, its position on a 0 to 1000 scale, and its content. Long lines are trimmed here.

```text
<PAGE><BLOCK>header[555, 46, 854, 61]<FORK>Payment System and Reserve Bank Oversight
<BLOCK>page_number[871, 47, 892, 59]<FORK>65
...
<BLOCK>table[144, 460, 855, 817]<FORK><table><tr><td>Item</td><td>2024</td><td>2023</td></tr>...
<BLOCK>text[786, 821, 853, 833]<FORK>(continued)
<BLOCK>page_footnote[143, 860, 813, 873]<FORK>$ ^{15} $  The Reserve Banks transferred ...
<PAGE><BLOCK>page_number[106, 48, 127, 59]<FORK>66
<BLOCK>header[145, 47, 331, 61]<FORK>111th Annual Report | 2024
<BLOCK>other[154, 120, 294, 133]<FORK>Table 5.3—continued
<BLOCK>append_table[145, 137, 855, 535]<FORK><table><tr><td>Item</td><td>2024</td><td>2023</td></tr>...
```

The table on page 72 is labeled `append_table`, which means the model recognized it as the rest of the table on page 71.

This is nice for several reasons:

- The page number of every block is known from its `<PAGE>` section
- Labels like `header`, `page_number`, and `page_footnote` let you drop page clutter by type
- The `append_table` label marks the continuation, so nothing has to be guessed from the layout

## Merge a Table Split Across Pages

The raw output is not Markdown yet. Baidu's converter, [`process_unlimitedOCR2.py`](https://github.com/baidu/Unlimited-OCR/tree/main/utils), turns it into Markdown and joins each `append_table` onto the table before it, dropping the repeated header.

To load the result into pandas, read every HTML table in the Markdown.

```python
import re
from io import StringIO

import pandas as pd
from process_unlimitedOCR2 import convert


def load_tables(markdown):
    tables = re.findall(r"<table>.*?</table>", markdown, re.S)
    return [pd.read_html(StringIO(table))[0] for table in tables]


raw = open("results/case1-table-5-3/unlimited-raw.txt").read()
markdown = convert(raw[raw.index("<PAGE>"):])
tables = load_tables(markdown)
print([table.shape for table in tables])
```

```text
[(36, 3)]
```

The two pages come back as one DataFrame. The rows on either side of the page break sit next to each other.

```python
print(tables[0].iloc[19:23].to_string(header=False))
```

```text
19                                      For currency costs    1242     1047
20  For Consumer Financial Protection Bureau \( costs^3 \)     663      721
21                 Reserve Bank net (loss) from operations  -77606  -114386
22    Consolidated variable interest entities: Income, net      22     1124
```

Row 20 is the last row of page 71, and row 21 is the first row of page 72.

For comparison, DeepSeek-OCR-2 parses each page separately and returns two DataFrames, with the page title and the header repeated as data.

```text
[(21, 3), (20, 3)]

table 2, first 3 rows
0                      Table 5.3—continued  Table 5.3—continued  Table 5.3—continued
1                                     Item                 2024                 2023
2  Reserve Bank net (loss) from operations               -77606              -114386
```

Both models read every value correctly. The difference is that with Unlimited-OCR-2 there is nothing left to clean up.

## Merge a Table Across Four Pages

Some tables run much longer. Table G.10 lists the Federal Reserve Banks' income and expenses for every year from 1914 to 2024, across four pages.

![Table G.10 running across pages 206 to 209](images/unlimited-ocr-2-long-pdf-tables/case3-table-g10-four-pages.png)

Pass all four pages in one request, then load the tables the same way.

```python
raw = open("results/case3-table-g10/unlimited-raw.txt").read()
tables = load_tables(convert(raw[raw.index("<PAGE>"):]))
print([table.shape for table in tables])
```

```text
[(129, 13)]
```

All three page breaks were labeled `append_table`, so the full history comes back as one DataFrame. The years on either side of the first two breaks line up.

```python
income = tables[0].iloc[:, :3]
print(income[income.iloc[:, 0].isin(["1949", "1950", "1986", "1987"])].to_string(header=False))
```

```text
37  1949    316537    67931
38  1950    275839    69822
74  1986  17464528  1156868
76  1987  17633012  1146911
```

Row 75 between 1986 and 1987 is the header again. The model wrote a footnote marker in the header differently on page 208, so it no longer matched the header on page 206, and the converter only drops an exact match.

```text
page 206 header   Net additions or deductions (-)1
page 208 header   Net additions or deductions $ (-)^{1} $
```

So one row needs deleting by hand. DeepSeek-OCR-2 returns four DataFrames for the same table, and three of them start with "Table G.10—continued" and the header rows.

## Join Paragraphs Across Pages

Text that crosses a page break gets the same treatment. The model labels the first half `cross_text` and the second half `append_text`.

This paragraph in the Federal Reserve's [June 2025 Monetary Policy Report](https://www.federalreserve.gov/monetarypolicy/files/20250620_mprfullreport.pdf) ends mid-sentence on page 54 and continues on page 55.

![A paragraph that ends with "highly accommodative" on page 54 and continues on page 55](images/unlimited-ocr-2-long-pdf-tables/case4-mpr-paragraph-break.png)

```text
<BLOCK>cross_text[162, 853, 834, 910]<FORK>Figure A shows historical prescriptions ... called for highly accommodative
<PAGE>...
<BLOCK>append_text[161, 154, 834, 251]<FORK>monetary policy in response to the pandemic-driven recession ...
```

After the converter, the two halves are one paragraph.

```text
PDF              "...called for highly accommodative monetary policy in response..."
DeepSeek-OCR-2   "...called for highly accommodative"  [Box 4—continued]  "monetary policy in response..."
Unlimited-OCR-2  "...called for highly accommodativemonetary policy in response..."
```

The sentence is whole, though the space at the page break is lost.

Paragraphs are less reliable than tables. In two other paragraph breaks I tested, the converter had nothing to join. One second half came back as plain `text` instead of `append_text`, and the other break got no continuation labels at all.

## Send a Whole Section at Once

So far, each request held only the pages around one break. In practice, you would send a whole section of a report and let the model find the breaks.

To test that, I sent 10- and 30-page windows of the Annual Report in one request each and checked every table break inside them.

```bash
mlx_vlm.generate --model mlx-community/Unlimited-OCR-2-8bit \
  --image pages/p185.png pages/p186.png ... pages/p214.png \
  --prompt "Multi page parsing." --max-tokens 150000 --temperature 0
```

| Request size | Table breaks labeled `append_table` |
| --- | --- |
| 2 to 4 pages | 7 of 7 |
| 10 pages | 11 of 12 |
| 30 pages | 20 of 22 |

Merging held up as the requests grew. The one table that kept failing was Table 5.3, which merged when sent as two pages but split in both the 10- and 30-page requests.

On a MacBook Pro with an M5 Pro chip, a 30-page request took 3 to 5.5 minutes and peaked at about 17 GB of memory.

## Check the Numbers

Merging tables is only useful if the values are right. On Table G.9, an 8-column table split across pages 204 and 205, Unlimited-OCR-2 kept all 336 numbers printed on the two pages, while DeepSeek-OCR-2 misread one.

```text
row "Foreign currency denominated investments, net", 3rd value
  PDF               7,380
  DeepSeek-OCR-2    7,360    <- misread
  Unlimited-OCR-2   7,380
```

Merging can also lose data without any error. In Table G.10, Unlimited-OCR-2 kept all 13 columns on pages 206 to 208 but dropped the last column on page 209. Because the merged DataFrame still has 13 columns, pandas fills the gap with `NaN`.

Comparing the 12 Reserve Bank rows with the table's Total row catches it. This continues from the G.10 `tables` loaded above.

```python
BANKS = ["Boston", "New York", "Philadelphia", "Cleveland", "Richmond", "Atlanta",
         "Chicago", "St. Louis", "Minneapolis", "Kansas City", "Dallas", "San Francisco"]

g10 = tables[0]
g10 = g10.set_index(g10.columns[0])
banks = g10.loc[BANKS].apply(pd.to_numeric, errors="coerce")
total = pd.to_numeric(g10.loc["Total"], errors="coerce")

check = pd.DataFrame({"sum of banks": banks.sum(min_count=1), "Total row": total})
check["missing"] = banks.isna().sum()
print(check.tail(3))
```

```text
    sum of banks     Total row  missing
10  1.198433e+09  1.198433e+09        0
11 -5.000000e+00 -4.000000e+00        0
12           NaN           NaN       12
```

Column 12 is empty for all 12 banks and the total. The gap of 1 in column 11 is rounding in the source table.

A check like this is worth running on any merged table that has a total row.

## Final Thoughts

What I like about Unlimited-OCR-2 is that it fixes the most tedious part of pulling tables out of reports. A table that crosses a page break comes back as one DataFrame. Across all my runs, 38 of 41 table breaks were labeled as continuations, including a table across four pages.

It also runs on a laptop. With mlx-vlm, a 30-page request fits in about 17 GB of memory, so private documents never leave the machine.

But it is not a drop-in replacement for every OCR job:

- On single pages, Baidu's own report shows it scoring below the best single-page models, so a page-by-page model is a fine choice when nothing crosses a page break
- Paragraphs across pages merged in only 1 of 3 tests, so check text that matters
- A merge can drop a column or keep a repeated header without an error, so validate merged tables against their totals
- For documents of 100 pages or more, Baidu's SGLang server on an NVIDIA GPU processes the document in windows and keeps memory flat, which the Mac path does not do

## References

- **[Unlimited-OCR-2 model card](https://huggingface.co/baidu/Unlimited-OCR-2)** (Baidu, 2026): multi-page usage, the `Multi page parsing.` prompt, and the SGLang page-window settings.
- **[Unlimited OCR Works 2 technical report](https://huggingface.co/baidu/Unlimited-OCR-2/blob/main/Unlimited-OCR-2.pdf)** (Baidu ERNIE Team, 2026): built on DeepSeek-OCR, single-page and long-document benchmark scores, and memory savings on the SGLang server.
- **[DeepSeek-OCR-2 model card](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2)** (DeepSeek, 2026): the page-by-page baseline and its grounding prompt.
- **[Baidu post-processing README](https://github.com/baidu/Unlimited-OCR/tree/main/utils)** (Baidu, 2026): how `cross_*` and `append_*` blocks are merged and repeated headers dropped.
- **[mlx-vlm PR #2601](https://github.com/Blaizzy/mlx-vlm/pull/2601)** (2026): Unlimited-OCR-2 support in mlx-vlm 0.7.11.
- **[Federal Reserve 2024 Annual Report](https://www.federalreserve.gov/publications/files/2024-annual-report.pdf)** (Board of Governors of the Federal Reserve System, 2025): the running example, a U.S. government work in the public domain.
- **[Monetary Policy Report, June 2025](https://www.federalreserve.gov/monetarypolicy/files/20250620_mprfullreport.pdf)** (Board of Governors of the Federal Reserve System, 2025): the paragraph example, public domain.
