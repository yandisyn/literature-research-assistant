"""Verify record integrity, graph provenance and unchanged source PDFs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from build_catalog import networks


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    root=Path(p.parse_args().output)
    records=json.loads((root/'library.json').read_text(encoding='utf-8'))
    graphs=json.loads((root/'networks.json').read_text(encoding='utf-8'))
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['sha256'], 'Source PDF changed'
    ids={r['id'] for r in records}
    assert len(ids)==len(records)
    for r in records:
        assert (root/'notes'/f"{r['id']}.md").is_file()
        if r.get('source_image'):
            assert (root/r['source_image']).is_file()
    for name,g in graphs.items():
        nodes={n['id']:n for n in g['nodes']}
        for n in nodes.values():
            assert n['weight']==len(set(n['papers'])) and set(n['papers'])<=ids
        for e in g['edges']:
            assert e['source']!=e['target']
            assert e['weight']==len(set(e['papers']))
            assert set(e['papers'])==set(nodes[e['source']]['papers'])&set(nodes[e['target']]['papers'])
        assert (root/'graphs'/f'{name}.graphml').is_file()
    with (root/'literature.csv').open(encoding='utf-8-sig',newline='') as f:
        assert len(list(csv.DictReader(f)))==len(records)
    # Synthetic regression cases: repeated synonyms count once, homonyms stay separate,
    # unknown affiliations remain paper-specific, one-node networks have no self-loops.
    test=[dict(id='a',authors=['Same Name'],institutions=['A'],author_institutions=[[0]],keywords=['SVI','street view','SVI'],themes=['T']),
          dict(id='b',authors=['Same Name'],institutions=['B'],author_institutions=[[0]],keywords=['SVI','other'],themes=['T']),
          dict(id='c',authors=['Unknown'],institutions=[],author_institutions=[[]],keywords=[],themes=[]),
          dict(id='d',authors=['Unknown'],institutions=[],author_institutions=[[]],keywords=[],themes=[])]
    g=networks(test,{'svi':'street view'})
    assert len(g['authors']['nodes'])==4
    assert len(g['themes']['nodes'])==1 and not g['themes']['edges']
    assert len(g['keywords']['edges'])==1 and g['keywords']['edges'][0]['weight']==1
    assert next(n for n in g['keywords']['nodes'] if n['label']=='street view')['weight']==2
    result={'records_checked':len(records),'source_hashes_checked':len(manifest['files']),
            'graph_types_checked':len(graphs),'synthetic_regression_cases':'passed','result':'passed'}
    (root/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
