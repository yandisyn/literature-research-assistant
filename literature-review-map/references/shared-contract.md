# Shared execution contract

- Input folders, PDFs and Zotero are read-only unless the user explicitly asks for a specific write. Store outputs separately; keep source paths, hashes and evidence locations.
- Distinguish metadata, automated screening, abstract reading and full-text review in every output. Missing evidence stays empty with a reason. Do not infer academic findings from filenames or clustering.
- Save corrected source records separately from derived outputs. Refreshing caches is not permission to overwrite personal annotations. Use a new output directory when switching source corpus.
- Default to English static PNG (450 DPI), SVG and PDF for figures; no website unless requested. Journal compliance requires its actual specifications.
- Prefer local deterministic processing and cached text; load only relevant evidence into model context. No invented token-saving percentage.
- Validate applicable counts, duplicates, source hashes, evidence links and graph weights; inspect rendered figures/workbooks before delivery.
- Scripts are in the package root's scripts directory; nested module paths resolve via ../../scripts. Use available Python dependencies or an explicit environment. PDF: pypdf/pypdfium2. Statistics: numpy/scipy/scikit-learn/networkx/matplotlib. Excel: Node and @oai/artifact-tool. No dedicated virtual environment is currently bundled.
