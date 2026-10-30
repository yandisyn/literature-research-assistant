"""WoS TSV/tagged input, reference co-citation and explicit two-state burst model."""
import argparse,csv,hashlib,itertools,json,math,re,unicodedata,io
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import networkx as nx

def dump(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def table(path,rows,fields):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader()
  for row in rows:
   clean={k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k,'') for k in fields}
   w.writerow({k:"'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for k,v in clean.items()})
def read_wos(path):
 raw=path.read_bytes()
 try:text=raw.decode('utf-8-sig')
 except UnicodeDecodeError:text=raw.decode('utf-16')
 if '\t' in text.splitlines()[0]:
  rows=list(csv.DictReader(io.StringIO(text),delimiter='\t'))
 else:
  rows=[];r={};tag=None
  for line in text.splitlines():
   if line[:2]=='ER':rows.append(r);r={};tag=None
   elif re.match(r'^[A-Z0-9]{2} ',line):tag=line[:2];r[tag]=line[3:]
   elif line.startswith('   ') and tag:r[tag]+=('; ' if tag in ['CR','AU','AF','C1'] else ' ')+line.strip()
  if r.get('TI'):rows.append(r)
 required={'TI','PY','CR'}
 if not rows or not required<=set(rows[0]):raise ValueError('Missing WoS fields: TI, PY, CR required')
 if any(None in r for r in rows):raise ValueError('Malformed TSV row: excess columns')
 return rows
def canonical_reference(raw):
 raw=unicodedata.normalize('NFKC',raw).strip()
 dois=sorted(set(x.lower().rstrip('.,;]') for x in re.findall(r'10\.\d{4,9}/[^\s,;\]]+',raw,re.I)))
 year=re.search(r'(?:^|,\s*)((?:18|19|20)\d{2})(?:,|\b)',raw)
 author=raw.split(',')[0].strip();label=author+' '+(year[1] if year else 'n.d.')
 # Multiple distinct DOI claims remain unresolved rather than arbitrarily merged.
 key='doi:'+dois[0] if len(dois)==1 else 'raw:'+re.sub(r'\s+',' ',raw).casefold()
 return key,dict(label=label,year=int(year[1]) if year else None,doi=dois[0] if len(dois)==1 else None,ambiguous_dois=dois if len(dois)>1 else [])
def burst_states(r,n,s=2.,gamma=1.):
 """Two-state binomial adaptation; initial state 0, upward cost gamma*log(T)."""
 r=np.asarray(r,float);n=np.asarray(n,float);T=len(n)
 if T<2 or n.sum()==0 or r.sum()==0:return [0]*T,[]
 if (r>n).any() or (r<0).any():raise ValueError('Invalid binomial counts')
 base=r.sum()/n.sum()
 if base*s>=1:return [0]*T,[]
 probs=np.clip([base,base*s],1e-9,1-1e-9)
 costs=np.array([-r*np.log(p)-(n-r)*np.log1p(-p) for p in probs]).T
 penalty=gamma*math.log(T);dp=np.full((T,2),np.inf);back=np.zeros((T,2),int)
 dp[0]=costs[0]+[0,penalty]
 for t in range(1,T):
  for state in range(2):
   candidates=dp[t-1]+[penalty if state==1 else 0,0];prev=int(np.argmin(candidates));back[t,state]=prev;dp[t,state]=candidates[prev]+costs[t,state]
 state=int(np.argmin(dp[-1]));states=[state]
 for t in range(T-1,0,-1):state=int(back[t,state]);states.append(state)
 states=states[::-1];segments=[];start=None
 for t in range(T+1):
  if t<T and states[t] and start is None:start=t
  if start is not None and (t==T or not states[t]):
   gain=float((costs[start:t,0]-costs[start:t,1]).sum());segments.append(dict(start_index=start,end_index=t-1,duration=t-start,strength_loglik_gain=gain,net_gain=gain-penalty,left_censored=start==0,right_censored=t==T));start=None
 return states,segments
def analyze(source,out,top_n=80,min_count=3,min_pair=3,s=2.,gamma=1.,duration=1):
 out.mkdir(parents=True,exist_ok=True);rows=read_wos(source);docs=[];seen=set();duplicates=[];refs={};raw_count=0;within_duplicates=0
 for row in rows:
  year=re.fullmatch(r'\d{4}',str(row.get('PY','')).strip())
  if not year:raise ValueError('Invalid publication year for '+str(row.get('UT')))
  uid=row.get('UT') or row.get('DI') or hashlib.sha256((row['TI']+row['PY']).encode()).hexdigest()[:16]
  if uid in seen:duplicates.append(uid);continue
  seen.add(uid);reference_ids=set()
  for raw in (row.get('CR') or '').split('; '):
   if not raw.strip():continue
   raw_count+=1;key,info=canonical_reference(raw);rid=hashlib.sha256(key.encode()).hexdigest()[:16]
   ref=refs.setdefault(rid,dict(id=rid,key=key,**info,variants=set(),papers=set()));ref['variants'].add(raw)
   if rid in reference_ids:within_duplicates+=1
   reference_ids.add(rid);ref['papers'].add(uid)
  docs.append(dict(id=uid,title=row['TI'],year=int(year[0]),authors=(row.get('AF') or row.get('AU') or '').split('; '),journal=row.get('SO'),doi=row.get('DI'),abstract=row.get('AB'),keywords=(row.get('DE') or '').split('; '),institutions=row.get('C1'),reference_ids=sorted(reference_ids),source=str(source),export_date=row.get('DA'),global_times_cited=row.get('TC')))
 years=list(range(min(d['year'] for d in docs),max(d['year'] for d in docs)+1));by_year=Counter(d['year'] for d in docs);doc_index={d['id']:d for d in docs};n=[by_year[y] for y in years]
 for ref in refs.values():
  ref['variants']=sorted(ref['variants']);ref['papers']=sorted(ref['papers']);ref['frequency']=len(ref['papers']);ref['annual_counts']=[sum(doc_index[p]['year']==y for p in ref['papers']) for y in years]
 candidates=sorted([r for r in refs.values() if r['frequency']>=min_count],key=lambda r:(-r['frequency'],r['key']))
 selected=candidates[:top_n];ids={r['id'] for r in selected};pairs=defaultdict(set)
 for d in docs:
  for a,b in itertools.combinations(sorted(ids.intersection(d['reference_ids'])),2):pairs[a,b].add(d['id'])
 edges=[dict(source=a,target=b,weight=len(support),cosine=len(support)/math.sqrt(refs[a]['frequency']*refs[b]['frequency']),papers=sorted(support)) for (a,b),support in pairs.items() if len(support)>=min_pair]
 G=nx.Graph();G.add_nodes_from(sorted(ids));G.add_weighted_edges_from((e['source'],e['target'],e['cosine']) for e in edges)
 groups=sorted(nx.community.louvain_communities(G,weight='weight',seed=42),key=lambda c:(-len(c),sorted(c)[0])) if edges else [{r} for r in sorted(ids)]
 from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
 corpus=[d['title'] for d in docs];vector=TfidfVectorizer(stop_words=sorted(set(ENGLISH_STOP_WORDS)|{'street','view','urban','imagery','images','using','based','study','image'}),ngram_range=(1,2),min_df=1,max_df=1.);X=vector.fit_transform(corpus);terms=vector.get_feature_names_out();clusters=[]
 for ci,group in enumerate(groups):
  citing=sorted({p for rid in group for p in refs[rid]['papers']});indices=[i for i,d in enumerate(docs) if d['id'] in set(citing)];other=[i for i,d in enumerate(docs) if d['id'] not in set(citing)];scores=np.asarray(X[indices].mean(axis=0)).ravel()
  if other:scores-=np.asarray(X[other].mean(axis=0)).ravel()
  labels=list(terms[np.argsort(scores)[-5:][::-1]])
  for rid in group:refs[rid]['cluster']=ci
  clusters.append(dict(cluster=ci,nodes=len(group),reference_ids=sorted(group),citing_papers=citing,label_candidates=labels,label_source='in-group minus out-group mean title TF-IDF; generic corpus terms excluded; not validated topic names',annual_citing_counts=[sum(doc_index[p]['year']==y for p in citing) for y in years]))
 bursts=[];sensitivity=[]
 for ref in candidates:
  states,segments=burst_states(ref['annual_counts'],n,s,gamma)
  for segment in segments:
   if segment['duration']>=duration:bursts.append(dict(reference_id=ref['id'],label=ref['label'],doi=ref['doi'],cluster=ref.get('cluster'),frequency=ref['frequency'],annual_counts=ref['annual_counts'],begin=years[segment['start_index']],end=years[segment['end_index']],**segment))
 for gam in [.5,1.,2.]:
  for dur in [1,2]:
   found=sum(any(seg['duration']>=dur for seg in burst_states(r['annual_counts'],n,s,gam)[1]) for r in candidates);sensitivity.append(dict(s=s,gamma=gam,min_duration=dur,references_with_bursts=found))
 bursts.sort(key=lambda b:-b['strength_loglik_gain'])
 ongoing=[b for b in bursts if b['end']==years[-1]]
 q=nx.community.modularity(G,groups,weight='weight') if edges else None
 config=dict(top_n=top_n,min_citations=min_count,min_pair=min_pair,seed=42,clustering='Louvain on cosine-normalized co-citation weights',burst_model='two-state binomial adaptation of Kleinberg; not CiteSpace-equivalent',s=s,gamma=gamma,min_duration=duration,years=years,year_document_counts=n,short_window=len(years)<5,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source=str(source))
 quality=dict(records=len(docs),duplicate_records=duplicates,raw_reference_occurrences=raw_count,within_document_reference_duplicates=within_duplicates,unique_reference_keys=len(refs),doi_normalized_references=sum(bool(r['doi']) for r in refs.values()),ambiguous_multi_doi=sum(bool(r['ambiguous_dois']) for r in refs.values()),eligible_burst_references=len(candidates),selected_network_nodes=len(ids),network_edges=len(edges),clusters=len(groups),modularity=q,burst_intervals=len(bursts),ongoing_burst_candidates=len(ongoing),export_dates=sorted({d['export_date'] for d in docs if d['export_date']}))
 for name,obj in [('documents.json',docs),('references.json',list(refs.values())),('cocitation-network.json',dict(nodes=selected,edges=edges)),('clusters.json',clusters),('bursts.json',bursts),('frontier-candidates.json',ongoing),('sensitivity.json',sensitivity),('parameters.json',config),('quality-report.json',quality)]:dump(out/name,obj)
 table(out/'documents.csv',docs,['id','title','year','authors','journal','doi','abstract','keywords','source'])
 table(out/'references.csv',sorted(refs.values(),key=lambda r:-r['frequency']),['id','label','year','doi','frequency','annual_counts','cluster','variants'])
 table(out/'bursts.csv',bursts,['reference_id','label','doi','frequency','annual_counts','begin','end','duration','strength_loglik_gain','net_gain','left_censored','right_censored','cluster'])
 table(out/'clusters.csv',clusters,['cluster','nodes','label_candidates','annual_citing_counts','citing_papers'])
 for node in G:G.nodes[node].update(label=refs[node]['label'],frequency=refs[node]['frequency'],cluster=refs[node]['cluster'])
 nx.write_graphml(G,out/'cocitation.graphml')
 print(json.dumps(dict(quality=quality,parameters=config),ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--top-n',type=int,default=80);p.add_argument('--min-citations',type=int,default=3);p.add_argument('--min-pair',type=int,default=3);p.add_argument('--s',type=float,default=2.);p.add_argument('--gamma',type=float,default=1.);p.add_argument('--min-duration',type=int,default=1);a=p.parse_args()
 if a.s<=1 or a.gamma<0 or min(a.top_n,a.min_citations,a.min_pair,a.min_duration)<1:p.error('Invalid parameters')
 analyze(Path(a.input).resolve(),Path(a.output).resolve(),a.top_n,a.min_citations,a.min_pair,a.s,a.gamma,a.min_duration)
