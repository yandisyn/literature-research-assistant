"""Validate agent-reviewed records and produce a traceable local literature catalog.

Semantic extraction is performed by the invoking agent, not by this script.
All writes are derived outputs. Manual corrections belong in curated*.json.
"""
import argparse
import csv
import hashlib
import itertools
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def identifier(kind, key):
    return kind + '_' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]


def keyword_key(term, aliases):
    key = ' '.join(term.lower().split())
    return aliases.get(key, key)


def networks(records, aliases):
    graphs = {}
    for kind in ['authors', 'institutions', 'keywords', 'themes']:
        nodes = {}
        edges = defaultdict(set)
        for record in records:
            did = record['id']
            items = []
            for index, label in enumerate(record[kind]):
                detail = ''
                if kind == 'authors':
                    affiliations = [record['institutions'][j] for j in record['author_institutions'][index]]
                    detail = '; '.join(sorted(affiliations)) or 'Unknown affiliation; paper-specific identity'
                    # Conservative provisional identity; does not claim ORCID-level resolution.
                    key = label.casefold() + '|' + (detail if affiliations else did)
                elif kind == 'keywords':
                    key = keyword_key(label, aliases)
                    label = key
                else:
                    key = label
                nid = identifier(kind, key)
                node = nodes.setdefault(nid, {'id': nid, 'label': label, 'detail': detail, 'papers': set()})
                node['papers'].add(did)
                items.append(nid)
            for a, b in itertools.combinations(sorted(set(items)), 2):
                edges[a, b].add(did)
        graphs[kind] = {
            'nodes': [dict(n, papers=sorted(n['papers']), weight=len(n['papers'])) for n in nodes.values()],
            'edges': [{'source': a, 'target': b, 'weight': len(p), 'papers': sorted(p)} for (a, b), p in sorted(edges.items())]
        }
    return graphs


def write_graphml(path, graph):
    ns = 'http://graphml.graphdrawing.org/xmlns'
    ET.register_namespace('', ns)
    root = ET.Element('{%s}graphml' % ns)
    for key, scope, typ in [('label', 'node', 'string'), ('weight', 'all', 'int'), ('papers', 'all', 'string')]:
        ET.SubElement(root, '{%s}key' % ns, {'id':key, 'for':scope, 'attr.name':key, 'attr.type':typ})
    g = ET.SubElement(root, '{%s}graph' % ns, {'id':'G', 'edgedefault':'undirected'})
    for node in graph['nodes']:
        n = ET.SubElement(g, '{%s}node' % ns, {'id':node['id']})
        for k in ['label','weight','papers']:
            ET.SubElement(n, '{%s}data' % ns, {'key':k}).text = str(node[k]) if k != 'papers' else ';'.join(node[k])
    for index, edge in enumerate(graph['edges']):
        e = ET.SubElement(g, '{%s}edge' % ns, {'id':str(index), 'source':edge['source'], 'target':edge['target']})
        for k in ['weight','papers']:
            ET.SubElement(e, '{%s}data' % ns, {'key':k}).text = str(edge[k]) if k != 'papers' else ';'.join(edge[k])
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def build(root, scope):
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    source_root = Path(manifest['input_directory'])
    files = {str(Path(f['path']).relative_to(source_root)).replace('\\', '/'): f for f in manifest['files']}
    raw = []
    for path in sorted(root.glob('curated*.json')):
        raw.extend(json.loads(path.read_text(encoding='utf-8')))
    aliases_path = root / 'keyword-aliases.json'
    aliases = json.loads(aliases_path.read_text(encoding='utf-8')) if aliases_path.exists() else {}
    records, seen_files, seen_hashes, seen_dois = [], set(), set(), set()
    duplicate_files, doi_candidates = [], []
    for item in raw:
        filename = str(item['file']) + '.pdf' if isinstance(item['file'], int) else item['file'].replace('\\', '/')
        if filename in seen_files:
            raise ValueError('Repeated curation: ' + filename)
        seen_files.add(filename)
        f = files[filename]
        if f['status'] != 'extracted':
            raise ValueError('Cannot curate failed extraction without resolving it: ' + filename)
        if item.get('source_sha256') != f['sha256']:
            raise ValueError('Curation must match current manifest source_sha256: ' + filename)
        if len(item['authors']) != len(item['author_institutions']):
            raise ValueError('Author-affiliation mapping mismatch: ' + filename)
        for indices in item['author_institutions']:
            if any(not isinstance(i, int) or i < 0 or i >= len(item['institutions']) for i in indices):
                raise ValueError('Invalid institution index: ' + filename)
        doi = item.get('doi')
        if doi and not re.fullmatch(r'10\.\d{4,9}/\S+', doi):
            raise ValueError('Malformed DOI: ' + filename)
        if f['sha256'] in seen_hashes:
            duplicate_files.append(filename)
            continue
        if doi and doi.casefold() in seen_dois:
            doi_candidates.append(filename)
        seen_hashes.add(f['sha256'])
        if doi:
            seen_dois.add(doi.casefold())
        page = item.get('source_page', 1)
        if not isinstance(page, int) or not 1 <= page <= f['pages']:
            raise ValueError('Invalid source page: ' + filename)
        canonical_image = root / 'pages' / (f['document_id']+f'-p{page:04d}.png')
        legacy_image = root / 'pages' / (Path(filename).stem+'.png')
        source_image = canonical_image if canonical_image.exists() else legacy_image if legacy_image.exists() else None
        r = dict(item, id=f['document_id'], source_path=f['path'], sha256=f['sha256'],
                 evidence_scope=item.get('evidence_scope', scope), source_page=page,
                 publication_type=item.get('publication_type', 'journal_article'),
                 themes_origin='agent_inference_from_provided_content',
                 doi_status='transcribed_from_pdf_not_online_verified' if doi else 'not_visible',
                 extraction_status=item.get('extraction_status', 'agent_reviewed'),
                 limitations=item.get('limitations'), references=item.get('references'),
                 source_image=source_image.relative_to(root).as_posix() if source_image else None)
        r['evidence'] = {k: {'page':page, 'section':section} for k, section in {
            'title':'title', 'authors':'author line', 'institutions':'affiliation block',
            'keywords':'keywords block', 'year':'journal header or preprint date',
            'doi':'DOI printed on page', 'methods':'abstract', 'finding':'abstract', 'themes':'title and abstract; inferred'
        }.items() if r.get(k)}
        if item.get('evidence'):
            r['evidence'].update(item['evidence'])
        for field, ev in r['evidence'].items():
            if not isinstance(ev.get('page'), int) or not 1 <= ev['page'] <= f['pages']:
                raise ValueError('Invalid evidence locator: '+filename+' / '+field)
        records.append(r)
    records.sort(key=lambda r: (0, r['file']) if isinstance(r['file'], int) else (1, str(r['file'])))
    if not records:
        raise ValueError('No curated records found. Agent must read and extract papers first.')
    save_json(root / 'library.json', records)
    graphs = networks(records, aliases)
    save_json(root / 'networks.json', graphs)
    graph_dir = root / 'graphs'
    graph_dir.mkdir(exist_ok=True)
    for key, graph in graphs.items():
        write_graphml(graph_dir / (key + '.graphml'), graph)
    notes = root / 'notes'
    notes.mkdir(exist_ok=True)
    for r in records:
        lines = [f"# {r['title']}", '', f"- Record ID: {r['id']}", f"- Year: {r['year']}",
                 f"- Authors: {'; '.join(r['authors'])}", f"- Parent institutions: {'; '.join(r['institutions']) or 'Unavailable'}",
                 f"- Journal: {r['journal'] or 'Not provided'}", f"- DOI: {r['doi'] or 'Unavailable'}",
                 f"- Evidence scope: {r['evidence_scope']}, PDF page {r['source_page']}",
                 f"- Source: [Source PDF]({Path(r['source_path']).as_uri()})", '', '## Author keywords',
                 '; '.join(r['keywords']) or 'Not listed', '', '## Inferred themes',
                 '; '.join(r['themes']), '', '## Methods from reviewed evidence', r['methods'], '',
                 '## Findings from reviewed evidence', r['finding'], '', '## Reading coverage',
                 ('Full experimental details, sampling, limitations, and references remain unverified.' if r['evidence_scope'] != 'full_text' else 'See evidence and issues for reading coverage.'), '', '## Verification notes',
                 *['- '+i for i in r.get('issues', [])], ('- DOI transcribed; not verified online.' if r['doi'] else '- DOI not found on supplied pages.'), '']
        (notes / (r['id'] + '.md')).write_text('\n'.join(lines), encoding='utf-8')
    report = {'files': len(files), 'unique_records':len(records), 'unprocessed':sorted(set(files)-seen_files),
              'duplicate_files_excluded':duplicate_files, 'missing_doi':[r['file'] for r in records if not r['doi']],
              'same_doi_candidates_retained':doi_candidates,
              'missing_institutions':[r['file'] for r in records if not r['institutions']],
              'missing_keywords':[r['file'] for r in records if not r['keywords']],
              'source_pages':sum(f.get('pages',0) for f in files.values()),
              'graphs':{k:{'nodes':len(v['nodes']),'edges':len(v['edges'])} for k,v in graphs.items()},
              'scope':scope, 'generated_at':datetime.now(timezone.utc).isoformat()}
    save_json(root / 'quality-report.json', report)
    # CSV is an interchange view; library.json remains the authoritative structured output.
    headers = ['File','Title','Year','Journal','Authors','Institutions','Author keywords','Inferred themes','Methods from evidence','Findings from evidence','DOI','Evidence scope','Issues','Source page','Source file']
    rows = [[r['file'], r['title'], r['year'], r['journal'], '; '.join(r['authors']), '; '.join(r['institutions']),
             '; '.join(r['keywords']), '; '.join(r['themes']), r['methods'], r['finding'], r['doi'],
             r['evidence_scope'], '; '.join(r.get('issues',[])), r['source_page'], r['source_path']] for r in records]
    with (root / 'literature.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in row] for row in rows])
    save_json(root / 'workbook-data.json', {'headers':headers, 'rows':rows})
    history = root / 'runs.jsonl'
    with history.open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(report,ensure_ascii=False)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--scope', required=True, choices=['first_page','abstract','full_text'])
    args = p.parse_args()
    build(Path(args.output).resolve(), args.scope)
