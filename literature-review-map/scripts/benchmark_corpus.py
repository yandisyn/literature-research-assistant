"""Low-token screening: local caches, Zotero metadata and transparent text models."""
import argparse,json,re,hashlib,itertools
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer,ENGLISH_STOP_WORDS
from sklearn.decomposition import NMF
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.output)
manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'));meta=json.loads((root/'zotero-metadata.json').read_text(encoding='utf-8'));lookup={str(Path(r['path'])):r for r in meta['records']}
records=[];seen={};duplicates=[];failed=[]
for f in manifest['files']:
 if f['status']!='extracted':failed.append(f);continue
 if f['sha256'] in seen:duplicates.append(dict(path=f['path'],same_as=seen[f['sha256']]));continue
 seen[f['sha256']]=f['path'];r=dict(lookup[str(Path(f['path']))]);data=json.loads(Path(f['text_file']).read_text(encoding='utf-8'));text='\n'.join(p['text'] for p in data['pages']);head='\n'.join(p['text'] for p in data['pages'][:2])
 abstract=r['abstract'];origin='zotero_abstract'
 if not abstract:
  m=re.search(r'(?is)\babstract\b\s*[:.—-]?\s*(.{100,5000}?)(?=\n\s*(?:keywords|key words|1[.\s]+introduction|introduction)\b)',head)
  abstract=m[1] if m else '';origin='pdf_abstract_candidate' if m else 'title_only'
 supplemental=bool(re.search(r'(?im)^\s*(?:supplementary\s+(?:material|information|materials)|supporting\s+information)\s*$',data['pages'][0]['text']))
 r.update(id=f['document_id'],sha256=f['sha256'],pages=f['pages'],sparse_pages=f['sparse_pages'],text_characters=len(text),analysis_abstract=abstract,analysis_source=origin,supplemental=supplemental,evidence_scope='automated_screening_not_fulltext_review')
 records.append(r)
attachment_records=records[:];excluded=[];grouped=defaultdict(list)
for r in records:
 if r['supplemental']:excluded.append(dict(id=r['id'],reason='supplemental_attachment'));continue
 grouped[r['parent_item_id'] or r['id']].append(r)
records=[]
for group in grouped.values():
 group.sort(key=lambda r:(r['analysis_source']!='title_only',r['text_characters']),reverse=True)
 records.append(group[0]);excluded.extend(dict(id=r['id'],reason='additional_attachment_same_zotero_item') for r in group[1:])
overrides_path=root/'audit-overrides.json'
if overrides_path.exists():
 overrides=json.loads(overrides_path.read_text(encoding='utf-8'))
 for r in records:
  if r['id'] in overrides:r.update(overrides[r['id']])
(root/'attachment-screening.json').write_text(json.dumps(attachment_records,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'excluded-attachments.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
docs=[re.sub(r'https?://\S+',' ',r['title']+'. '+r['analysis_abstract']) for r in records]
stop=set(ENGLISH_STOP_WORDS)|{'study','research','paper','results','based','using','used','use','approach','analysis','method','methods','model','models','data','new','different','et','al','abstract','keywords','copyright','elsevier','rights','reserved','journal','article','2023','2024','2025'}
stop.update({'https','http','www','com','github','received','accepted','revised','history','previous','studies','available','online','doi','org','license','licence'})
vec=TfidfVectorizer(stop_words=sorted(stop),min_df=3,max_df=.8,ngram_range=(1,2),max_features=2500,token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z-]{2,}\b')
X=vec.fit_transform(docs);terms=vec.get_feature_names_out();k=min(8,X.shape[0]-1,X.shape[1]-1)
nmf=NMF(n_components=k,init='nndsvda',random_state=42,max_iter=800);W=nmf.fit_transform(X);assignment=W.argmax(axis=1);assignment[np.asarray(X.sum(axis=1)).ravel()==0]=-1;labels=[]
for j,row in enumerate(nmf.components_):labels.append(' / '.join(terms[row.argsort()[-3:][::-1]]))
for i,r in enumerate(records):r['screening_topic']=int(assignment[i]);r['screening_topic_terms']=labels[assignment[i]] if assignment[i]>=0 else 'Unclassified: no usable English features'
figs=root/'figures';figs.mkdir(exist_ok=True)
(figs/'data-manifest.md').write_text('Real local corpus; no synthetic data.\nInputs: ../manifest.json, ../zotero-metadata.json and cached text/*.json.\nOutputs: phrase_network and topic_timeline, PNG (450 DPI), SVG and PDF.\nScript: benchmark_corpus.py. NMF and spring-layout seed: 42.\nNMF uses 8 exploratory topics; title/abstract text coverage differs across records.\nPhrase network: top 45 bigrams by document frequency, at least 3 documents per edge.\nMetadata comes from the explicitly recorded Zotero database snapshot.\n',encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'none','pdf.fonttype':42})
colors=['#0077BB','#EE7733','#009988','#AA4499','#CCBB44','#66CCEE','#CC6677','#4477AA']
def save(fig,name):
 for ext in ['png','svg','pdf']:fig.savefig(figs/(name+'.'+ext),dpi=450,bbox_inches='tight',facecolor='white')
 plt.close(fig)
years=sorted({r['year'] for r in records if r['year']});counts=np.array([[sum(r['year']==y and r['screening_topic']==j for r in records) for y in years] for j in range(k)])
fig,ax=plt.subplots(figsize=(12,6))
bins=list(range(min(years)//5*5,max(years)//5*5+1,5))
for j in range(k):
 for i,y in enumerate(bins):
  n=sum(counts[j,q] for q,year in enumerate(years) if y<=year<y+5)
  if n:ax.scatter(i,j,s=65+n*15,color=colors[j],edgecolor='white');ax.text(i,j,str(n),ha='center',va='center',fontsize=7,color='white')
ax.set_xticks(range(len(bins)),[str(y)+'–'+str(min(y+4,max(years)))[-2:] for y in bins],rotation=45,ha='right')
ax.set_yticks(range(k),[f'T{j+1}: '+s for j,s in enumerate(labels)]);ax.invert_yaxis();ax.set_xlabel('Publication year (Zotero metadata)');ax.set_title('Topic distribution over time | local Zotero corpus',loc='left',fontsize=14);ax.grid(axis='x',alpha=.15);ax.spines[['top','right','left']].set_visible(False)
fig.text(.02,.01,'NMF on titles and available abstracts; one dominant topic per document. Circle labels = document counts.\nExploratory topics, not validated research fronts or citation bursts. Missing abstracts create unequal text coverage.',fontsize=8);fig.tight_layout(rect=[0,.08,1,1]);save(fig,'topic_timeline')
# Select frequent phrases; use true document co-occurrence, not invented citation edges.
binary=(X>0).astype(int);df=np.asarray(binary.sum(axis=0)).ravel();selected=sorted(range(len(terms)),key=lambda i:df[i],reverse=True)
selected=[i for i in selected if ' ' in terms[i]][:45]
G=nx.Graph()
for idx in selected:G.add_node(terms[idx],frequency=int(df[idx]))
C=(binary[:,selected].T@binary[:,selected]).toarray();edge_records=[]
for i,j in itertools.combinations(range(len(selected)),2):
 if C[i,j]>=3:
  G.add_edge(terms[selected[i]],terms[selected[j]],weight=int(C[i,j]));support=[records[q]['id'] for q in range(len(records)) if X[q,selected[i]]>0 and X[q,selected[j]]>0];edge_records.append(dict(source=terms[selected[i]],target=terms[selected[j]],weight=int(C[i,j]),papers=support))
communities=list(nx.community.greedy_modularity_communities(G));membership={n:i for i,c in enumerate(communities) for n in c};pos={}
cols=4
for ci,community in enumerate(communities):
 local=nx.spring_layout(G.subgraph(community),seed=42,iterations=200,weight=None,scale=.65)
 for n,xy in local.items():pos[n]=xy+np.array([(ci%cols)*2.5,-(ci//cols)*2.2])
fig,ax=plt.subplots(figsize=(12,9));ax.axis('off');nx.draw_networkx_edges(G,pos,ax=ax,alpha=.16,width=[.3+np.sqrt(d['weight'])/4 for _,_,d in G.edges(data=True)])
nx.draw_networkx_nodes(G,pos,ax=ax,node_size=[40+G.nodes[n]['frequency']*10 for n in G],node_color=[colors[membership[n]%8] for n in G],edgecolors='white')
occupied=[]
for n in sorted(G,key=lambda n:G.nodes[n]['frequency'],reverse=True)[:24]:
 x,y=pos[n];ty=y+.16
 while any(abs(x-xx)<1.25 and abs(ty-yy)<.22 for xx,yy in occupied):ty+=.23
 occupied.append((x,ty));ax.annotate(n,(x,y),xytext=(x,ty),ha='center',fontsize=7,arrowprops=dict(arrowstyle='-',color='#94A3B8',lw=.5),bbox=dict(facecolor='white',alpha=.8,edgecolor='none',pad=1))
ax.set_ylim(min(v[1] for v in pos.values())-.5,max(y for x,y in occupied)+.4)
ax.set_title('Phrase co-occurrence in titles and available abstracts',loc='left',fontsize=14);fig.text(.12,.035,'Top 45 frequent bigrams; edge threshold: at least 3 shared documents. Node area: document frequency.\nColors: weighted greedy-modularity communities. Phrases are automatically extracted, not author keywords.',fontsize=8);fig.subplots_adjust(bottom=.12);save(fig,'phrase_network')
report=dict(files=len(manifest['files']),unique_records=len(records),duplicates=duplicates,failed=failed,pages=sum(r['pages'] for r in records),text_characters=sum(r['text_characters'] for r in records),files_with_sparse_pages=sum(bool(r['sparse_pages']) for r in records),analysis_sources=dict(Counter(r['analysis_source'] for r in records)),year_range=[min(years),max(years)],database_source=meta['database'],database_mtime=meta['database_mtime'],nmf_topics=labels,topic_counts=counts.tolist(),years=years,network_nodes=len(G),network_edges=G.number_of_edges())
for name,value in [('screening-records.json',records),('benchmark-report.json',report),('phrase-network.json',dict(nodes=[dict(id=n,**G.nodes[n]) for n in G],edges=edge_records))]:(root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
sample=[]
for j in range(k):
 idx=int(W[:,j].argmax());r=records[idx];entry=next(f for f in manifest['files'] if f['document_id']==r['id']);page=json.loads(Path(entry['text_file']).read_text(encoding='utf-8'))['pages'][0]['text'];sample.append(dict(id=r['id'],title=r['title'],year=r['year'],authors=r['authors'],topic=labels[j],first_page=page[:2200]))
(root/'audit-sample.json').write_text(json.dumps(sample,ensure_ascii=False,indent=2),encoding='utf-8')
assert counts.sum()==sum(r['screening_topic']>=0 and bool(r['year']) for r in records)
for e in edge_records:assert e['weight']==len(e['papers'])
print(json.dumps({k:v for k,v in report.items() if k not in ['topic_counts','duplicates','failed']},ensure_ascii=False))
