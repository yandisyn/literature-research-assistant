import itertools,json,math,tempfile,unittest
from pathlib import Path
import numpy as np
from wos_analysis import burst_states,canonical_reference,read_wos

class WosTests(unittest.TestCase):
 def test_doi_alias_and_ambiguity(self):
  a,_=canonical_reference('Smith J, 2020, J TEST, DOI 10.1234/ABC')
  b,_=canonical_reference('SMITH, 2021, JOURNAL TEST, DOI 10.1234/abc')
  self.assertEqual(a,b)
  key,info=canonical_reference('X, 2000, DOI [10.1234/a, DOI 10.1234/b]')
  self.assertTrue(key.startswith('raw:'));self.assertEqual(len(info['ambiguous_dois']),2)
 def test_constant_proportion(self):
  states,_=burst_states([1,2,4,8],[10,20,40,80]);self.assertEqual(states,[0]*4)
 def test_peak(self):
  states,segs=burst_states([1]*10+[30]*3+[1]*7,[100]*20)
  self.assertTrue(all(states[10:13]));self.assertTrue(segs)
 def test_dynamic_program_matches_exhaustive(self):
  r=np.array([0,3,14,1]);n=np.array([20]*4);p=r.sum()/n.sum();penalty=math.log(4)
  def cost(path):
   probs=np.array([p*(2**state) for state in path]);emission=float((-r*np.log(probs)-(n-r)*np.log1p(-probs)).sum());prev=0
   for state in path:emission+=penalty*max(0,state-prev);prev=state
   return emission
  states,_=burst_states(r,n);best=min(cost(path) for path in itertools.product([0,1],repeat=4));self.assertAlmostEqual(cost(states),best)
 def test_tagged_and_tsv(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'input.txt';p.write_text('PT J\nTI A title\nPY 2020\nCR X, 1990\n   Y, 1991\nER\nEF\n');r=read_wos(p);self.assertEqual(r[0]['CR'],'X, 1990; Y, 1991')
   p.write_text('TI\tPY\tCR\n"Two\nlines"\t2021\tX\n');r=read_wos(p);self.assertEqual(r[0]['TI'].replace('\r\n','\n'),'Two\nlines')

def verify_run(root):
 docs=json.loads((root/'documents.json').read_text(encoding='utf-8'));refs={r['id']:r for r in json.loads((root/'references.json').read_text(encoding='utf-8'))};network=json.loads((root/'cocitation-network.json').read_text(encoding='utf-8'));params=json.loads((root/'parameters.json').read_text(encoding='utf-8'))
 import hashlib
 assert hashlib.sha256(Path(params['source']).read_bytes()).hexdigest()==params['source_sha256']
 for rid,r in refs.items():
  expected={d['id'] for d in docs if rid in d['reference_ids']};assert expected==set(r['papers']);assert len(expected)==r['frequency']==sum(r['annual_counts'])
 for e in network['edges']:
  expected=set(refs[e['source']]['papers'])&set(refs[e['target']]['papers']);assert expected==set(e['papers']);assert len(expected)==e['weight']
  assert abs(e['cosine']-len(expected)/math.sqrt(refs[e['source']]['frequency']*refs[e['target']]['frequency']))<1e-12
 result=dict(documents=len(docs),references=len(refs),edges=len(network['edges']),source_unchanged=True,status='passed');(root/'validation.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':
 import sys
 if len(sys.argv)>1 and sys.argv[1]=='--output':verify_run(Path(sys.argv[2]))
 else:unittest.main()
