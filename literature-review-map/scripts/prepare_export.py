"""Normalize existing evidence into English-labelled export tables; never infer findings."""
import argparse,csv,json
from pathlib import Path

def prepare(source,out):
 out.mkdir(parents=True,exist_ok=True)
 def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
 def table(name,records,fields):
  def cell(v):
   if v is None:return ''
   if isinstance(v,(list,dict)):return json.dumps(v,ensure_ascii=False)
   if isinstance(v,str) and v.startswith(('=','+','-','@')):return "'"+v
   return v
  return dict(name=name,headers=fields,rows=[[cell(r.get(f)) for f in fields] for r in records])
 if source.is_dir():
  specs=[('Documents',read(source/'documents.json'),['id','title','year','authors','journal','doi','abstract']),('Bursts',read(source/'bursts.json'),['label','reference_id','begin','end','duration','strength_loglik_gain','right_censored']),('Clusters',read(source/'clusters.json'),['cluster','nodes','label_candidates','annual_citing_counts']),('Selected references',read(source/'cocitation-network.json')['nodes'],['id','label','doi','frequency','annual_counts','cluster']),('Sensitivity',read(source/'sensitivity.json'),['s','gamma','min_duration','references_with_bursts'])]
 else:
  data=read(source)
  if not isinstance(data,list):raise ValueError('Expected a JSON array of structured records')
  fields=['id','title','year','authors','journal','doi','evidence_scope']
  extras=sorted({k for r in data for k in r}-set(fields))
  specs=[('Documents',data,fields)]
  for i in range(0,len(extras),5):specs.append((f'Evidence {i//5+1}',data,['id','title']+extras[i:i+5]))
 tables=[table(*spec) for spec in specs]
 (out/'tables.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2),encoding='utf-8')
 for t in tables:
  with (out/(t['name'].replace(' ','-')+'-export.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(t['headers']);w.writerows(t['rows'])
 print(json.dumps({t['name']:len(t['rows']) for t in tables}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();prepare(Path(a.input),Path(a.output))
