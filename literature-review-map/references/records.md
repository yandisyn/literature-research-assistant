# Structured record schema

curated*.json contains a JSON array, usually one record per PDF. For multi-paper volumes, establish article boundaries and distinct identifiers first.

| Field | Meaning |
|---|---|
| file | PDF path relative to the input folder; integer n abbreviates n.pdf |
| source_sha256 | Required hash copied from the current manifest; reread changed PDFs before updating |
| extraction_status | Defaults to agent_reviewed; use agent_visual_checked only after visual verification |
| title | Transcribed source title |
| year | Publication-volume year or null; explain preprint date choices in issues |
| journal / doi | String or null; transcription is not online DOI verification |
| authors | Names in source order |
| institutions | Author affiliations, normalized to parent institutions by default |
| author_institutions | One list per author, containing zero-based institution indices; [] if unknown |
| keywords | Original author keywords, not automatically extracted terms |
| themes | Inferred themes grounded in the material read; use consistent English labels by default |
| methods / finding | Summaries grounded in actual reading; no unverified numerical claims |
| source_page | One-based primary PDF page; defaults to 1 |
| evidence | Per-field page/section locations; expand for multi-page evidence |
| evidence_scope | first_page, abstract, partial_abstract, or full_text; never mislabel partial reading |
| publication_type | journal_article by default; preprint where applicable |
| issues | Missing values, ambiguous dates, OCR uncertainty, and unverified conditions |
| limitations / references | Optional; null without supporting evidence |

Example schema fragment, not a real paper; add source_sha256 from the manifest before use:

```json
{"file":"subfolder/paper.pdf","title":"Source title","year":null,"journal":null,"doi":null,"authors":["Author A"],"institutions":["Institution A"],"author_institutions":[[0]],"keywords":[],"themes":["Inferred theme"],"methods":"Evidence-based method summary","finding":"Evidence-based finding summary","issues":["Year and keywords unavailable"]}
```

Retain source PDFs, page text, rendered pages, and raw OCR. library.json adds provenance and status. Summaries are paraphrases; do not infer unstated limitations. Numerical claims require specific source text and page evidence.

keyword-aliases.json maps lowercase original terms to supported canonical equivalents. Do not merge a specific method into an overly broad technology category. Name normalization does not prove author identity; formal disambiguation may require ORCID, email, or career information.
