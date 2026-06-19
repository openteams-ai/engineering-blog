---
title: "PDF Table Extraction Tools Compared"
status: "done"
source_document: "https://openteams.com/docling-vs-marker-vs-llamaparse/"
---

PDF table extraction is hard because the table is not really stored as a table.

The tool has to infer rows, columns, headers, and cell boundaries from text positions on the page. That becomes much harder when the document includes merged cells, nested headers, or packed numeric data.

To compare different approaches, Khuyen Tran tested three Python tools on the same technical PDF:

• Docling, an open-source document converter with a vision-language model pipeline
• Marker, a local PDF-to-Markdown converter built on a multi-stage vision pipeline
• LlamaParse, a cloud-hosted parser that uses an LLM-guided extraction workflow

She evaluated them using two practical criteria: table structure accuracy and processing time.

The article walks through the results with practical examples and diagrams.

**Hashtags:**

#Python #DataEngineering #OpenSource #DocumentAI
