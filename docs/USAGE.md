# Usage and environment

## Responsibilities and dependencies

Codex follows the skill instructions and reads evidence. Python scripts extract, calculate, and plot. Running PDF extraction alone produces a cache, not a reviewed literature synthesis. Excel export requires Node and a host-provided `@oai/artifact-tool`; CSV requires only Python.

Python 3.11 is recommended. The statistical workflow was exercised with scikit-learn 1.2.2, networkx 3.1, and matplotlib 3.8, alongside installed NumPy/SciPy. Dependency ranges are compatibility targets, not a lockfile. PDF and statistical processing used existing runtimes; a fresh combined installation has not been validated.

Copy the entire skill directory to your configured Codex skills location. Nested modules depend on shared resources and should not be installed separately.

## WoS command-line workflow

Export full records and cited references. Tab-separated and tagged plain text are supported; TI, PY, and CR are required. Quote paths containing spaces.

```bash
python literature-review-map/scripts/wos_analysis.py --input "data/savedrecs.txt" --output "output/wos"
python literature-review-map/scripts/test_wos.py --output "output/wos"
python literature-review-map/scripts/wos_figures.py --output "output/wos"
python literature-review-map/scripts/prepare_export.py --input "output/wos" --output "output/wos"
# Optional: a runtime directory from which @oai/artifact-tool can be resolved
node literature-review-map/scripts/export_tables.mjs "output/wos" "PATH_TO_NODE_RUNTIME"
# Refresh the report and artifact hashes after all outputs are saved
python literature-review-map/scripts/wos_report.py --output "output/wos"
```

Skip the Node step if the Excel dependency is unavailable. Defaults: `--top-n 80 --min-citations 3 --min-pair 3 --s 2 --gamma 1 --min-duration 1`. After changing parameters, regenerate figures, exports, and reports. Keep each configuration in its own output folder; do not present only the most attractive parameter setting.

## PDFs

```bash
python literature-review-map/scripts/ingest.py --input "data/pdfs" --output "output/pdf" --backend pdfium
```

Ask the corresponding skill to inspect the cached text and pages, then create curated records. See the [PDF module](../literature-review-map/skills/literature-pdf-abstract/SKILL.md) and [schema](../literature-review-map/references/records.md). Full-text reading includes relevant sections and visual checks of tables, equations, and figures when needed. Extraction does not prove reading completeness.

Leave unavailable affiliations empty; keep author keywords separate from inferred themes. Review OCR against the page. Windows OCR requires installed language support.

## Zotero

Use the [Zotero screening module](../literature-review-map/skills/literature-zotero-screen/SKILL.md). Match metadata and attachments before screening. Read-only database access requires authorization. Do not terminate Zotero to bypass a lock; disclose the date and coverage when using a backup. Screening outputs do not establish full-text methods or findings, and author names alone cannot establish affiliations.

## Export and plotting

prepare_export.py accepts library.json, screening-records.json, or a WoS analysis directory. Missing values are not filled with invented summaries. The WoS Selected references worksheet contains only network-selected nodes; full references remain in references.csv and references.json.

Plots reuse analysis data and retain the distinction between full networks and displayed edges. Adjust spacing, curves, labels, and transparency without inventing relationships.

## Troubleshooting

| Symptom | Action |
|---|---|
| Module not visible | Check folder nesting; start a new session or use the router |
| Missing Python module | Confirm the active interpreter and install requirements |
| artifact-tool unavailable | Supply a valid host runtime or use CSV |
| No PDF text | Check for scanned, damaged, or HTML files mislabeled as PDF |
| Missing CR field | Export full records and cited references again |
| No bursts | Inspect dates, thresholds, and sensitivity; zero can be a valid result |
| Poor multilingual topics | Adapt feature extraction and stopwords, then validate manually |
