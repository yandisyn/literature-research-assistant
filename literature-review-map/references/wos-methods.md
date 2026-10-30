# WoS methods and reproducibility

## Inputs and identity

Read WoS tab-separated exports or tagged plain text, retaining source SHA-256. Publication years come from PY, citations from CR, source documents from UT (DOI/title fallback only when UT absent). TC is a global accumulated count and is not used as an annual citation series.

Reference variants with one unambiguous DOI merge case-insensitively. Multiple distinct DOI claims remain raw keys. References without DOI merge only after Unicode/whitespace/case normalization; fuzzy bibliographic matching is deliberately not automatic. Thus unresolved aliases may split references and should be audited before publication. A reference counts at most once in each citing document.

## Co-citation

For reference pair a,b, count distinct source documents citing both. Normalize weight as count(a,b)/sqrt(count(a)*count(b)). This follows the cosine definition described by [CiteSpace](https://citespace.podia.com/glossary-cocitations).

The default graph selects top 80 references with local frequency ≥3 and edges supported by ≥3 documents. Store every edge's source-document list. Run Louvain with seed 42 on cosine weights and report modularity. Labels are candidate phrases from in-group minus out-group mean TF-IDF of citing-paper titles, excluding generic corpus terms; they are not validated scientific interpretations.

Drawing uses the top three incident similarities per node plus a maximum spanning forest. This is display-only filtering. Exported JSON/GraphML and clustering retain all analysis edges. Cluster timeline counts distinct citing documents; documents may contribute to several clusters.

## Burst model

Use the two-state, batched-document binomial formulation motivated by Section 4 of [Kleinberg (2002)](https://www.cs.cornell.edu/home/kleinber/bhs.pdf). This is a transparent local implementation, not a claim of numerical equivalence to a particular CiteSpace release.

For each year t, n_t is the number of source documents and r_t the number citing a reference. Set p0 = sum(r)/sum(n), p1 = s*p0. If p1 ≥1, the implementation retains only the baseline state. Omit the binomial coefficient from emission costs because it is common to both states. Emission cost is -r_t log(p_i) -(n_t-r_t) log(1-p_i). An upward 0→1 transition costs gamma*log(T), where T is the number of yearly bins; downward transitions are free and the initial state is 0. Dynamic programming finds the minimum-cost path.

Intervals in state 1 are candidate bursts. Strength is the sum of baseline-minus-burst emission costs over the interval, in natural-log units; net gain additionally subtracts the entry penalty. Minimum duration filters the resulting intervals, rather than re-optimizing a duration-constrained state model. Parameter defaults are s=2, gamma=1, duration=1. Report sensitivity at gamma=.5/1/2 and duration=1/2. These scores are not p-values or multiple-testing-adjusted significance claims.

Normalize by annual corpus size; preserve zero-source years as gaps and interpret any interval spanning them cautiously. First/last-window intervals are left/right censored. For short windows, partial terminal years and small samples, do not infer durable trends from one-year spikes. Reference publication age does not lengthen the source-document observation window.

## Frontier candidates

References with bursts touching the final observed year enter frontier-candidates.json. Their cluster can be null when outside the top-N network; do not force them into an analyzed cluster. Inspect their citing-paper context and supporting sources before interpreting a research front. A result of no robust frontier is valid. The latest year in a historical export does not mean the current calendar year.

## Outputs and validation

JSON: documents, references with raw variants, graph with provenance, clusters, bursts, sensitivity, parameters and quality. CSV: document catalog, all references, clusters and bursts. Figures: co-citation map, burst bars, cluster time profiles. Excel can be created separately by literature-export.

Run test_wos.py for DOI handling, constant-rate controls, burst cases, exhaustive state-path comparison and parser cases; use --output OUTPUT to verify real counts, source hashes and every edge's supporting-document set. The analysis does not download reference full texts or verify DOI resolution online.
