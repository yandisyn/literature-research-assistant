# Network definitions

Default PDF-derived networks are undirected, with paper IDs supporting every edge.

- Author collaboration: provisional name-plus-affiliation identity. Missing affiliations keep authors paper-specific. Affiliation changes may split one person; same-name colleagues may merge. Do not claim fully resolved identities.
- Institutional collaboration: parent institutions co-listed on a paper, including multiple affiliations of one author. This does not establish project or funding relationships.
- Keyword co-occurrence: original author keywords only, normalized through explicit aliases; count each term once per paper.
- Theme co-occurrence: model-assigned themes grounded in read evidence. This is an interpretation layer, not author keywords or citation bursts.

Node weight counts supporting documents; edge weight counts documents containing both endpoints. Layout distances are not geography, causality, or confidence. Preserve complete networks separately from display filtering.

For co-citation and bursts, use literature-wos-analysis with WoS CR records. Bibliographic coupling is not implemented. Disclose short windows and convenience samples rather than presenting them as systematic retrieval.

Generic GraphML is exported; no native CiteSpace project or proprietary VOSviewer format is claimed.
