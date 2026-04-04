---
title: Markdown Rendering Test - Please Delete
slug: markdown-rendering-test
author: Khuyen Tran
categories:
- Engineering
tags:
- test
meta_description: A comprehensive test of all markdown elements for WordPress rendering.
wordpress_url: https://openteams.com/markdown-rendering-test/
wordpress_id: 21825
last_synced: '2026-04-04T15:10:44Z'
---

## Introduction

This article tests **bold text**, *italic text*, ***bold italic***, `inline code`, and [hyperlinks](https://openteams.com). It also tests ~~strikethrough~~ text.

## Code Blocks

### Python (with Line Highlighting)

```python
#| highlight: 3-5
import pandas as pd
from pathlib import Path

def load_and_transform(path: str) -> pd.DataFrame:
    """Load CSV and apply transformations."""
    df = pd.read_csv(path)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["year"] = df["created_at"].dt.year
    return df.dropna(subset=["email"])

if __name__ == "__main__":
    result = load_and_transform("data/users.csv")
    print(f"Processed {len(result)} records")
```

### Bash (Command-Line with Output)

```bash
#| command-line data-user=dev data-host=openteams
#| data-output: 2-5
ls -la posts/
total 8
drwxr-xr-x 4 dev dev 4096 Apr  3 10:00 .
drwxr-xr-x 2 dev dev 4096 Apr  3 10:00 building-ml-pipelines
drwxr-xr-x 2 dev dev 4096 Apr  3 10:00 markdown-test
```

### Bash (Command-Line with Filter Output)

```bash
#| command-line
#| data-filter-output: (out)
echo "Hello from OpenTeams!"
(out)Hello from OpenTeams!
uv run scripts/wordpress/publish.py posts/test/index.md
(out)Title: Test Article
(out)Slug: test-article
(out)Mode: create (new draft)
```

### SQL (with Line Highlighting)

```sql
#| highlight: 6-7
SELECT
    u.name,
    COUNT(o.id) AS order_count,
    SUM(o.total) AS lifetime_value
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at >= '2025-01-01'
GROUP BY u.name
HAVING COUNT(o.id) > 5
ORDER BY lifetime_value DESC
LIMIT 10;
```

### Root Command-Line

```bash
#| command-line data-user=root data-host=server
apt-get update && apt-get install -y python3
systemctl restart nginx
```

### Custom Prompt (MySQL)

```sql
#| command-line data-prompt="mysql>"
#| data-output: 2-5
SELECT name, email FROM users LIMIT 3;
+-------+-------------------+
| name  | email             |
+-------+-------------------+
| Alice | alice@example.com |
```

### YAML

```yaml
services:
  api:
    image: openteams/api:latest
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgres://db:5432/app
      REDIS_URL: redis://cache:6379
    depends_on:
      - db
      - cache
```

### JSON

```json
{
  "name": "engineering-blog",
  "version": "0.1.0",
  "dependencies": {
    "markdown": ">=3.8",
    "pydantic": ">=2.0",
    "requests": ">=2.32"
  }
}
```

## Tables

| Feature | Tool A | Tool B | Tool C |
|---------|--------|--------|--------|
| Speed | Fast | Medium | Slow |
| Memory usage | 120 MB | 450 MB | 2.1 GB |
| Parallel execution | Yes | No | Yes |

## Lists

- First item with **bold text**
- Second item with `inline code`
  - Nested item one
  - Nested item two

1. Install dependencies
2. Configure the environment
3. Run the pipeline

## Blockquote

> The best code is no code at all.
> — Jeff Atwood

## Mermaid Diagram

```mermaid
graph LR
    A[Write Article] --> B[Open PR]
    B --> C{Review}
    C -->|Approved| D[Merge to Main]
    C -->|Changes Needed| A
    D --> E[GitHub Actions]
    E --> F[Publish to WordPress]
```

---

## Mixed Content

Use `pd.read_csv()` to load data, then call **`transform()`** to process it.

```text
Processing 1,000,000 records...
Transformation complete in 2.3s
Results saved to output/results.parquet
```
