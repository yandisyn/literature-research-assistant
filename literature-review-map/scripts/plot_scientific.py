"""Reproducible static corpus maps. Requires matplotlib, networkx and numpy."""
import argparse,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.patches import Ellipse

THEMES=dict(zip(['\u57ce\u5e02\u611f\u77e5\u6d4b\u5ea6','\u89c6\u89c9\u8981\u7d20\u4e0e\u611f\u77e5','\u591a\u6a21\u6001\u4e0e\u7a7a\u95f4\u8868\u5f81','\u793e\u4f1a\u7ecf\u6d4e\u4e0e\u7a7a\u95f4\u516c\u5e73','\u6062\u590d\u6027\u4e0e\u5065\u5eb7','\u9a91\u884c\u4e0e\u6b65\u884c\u73af\u5883','\u89c4\u5212\u8bbe\u8ba1\u4e0e\u66f4\u65b0','\u591a\u611f\u5b98\u4e0e\u58f0\u666f','\u53ef\u89e3\u91ca\u6027\u4e0e\u65b9\u6cd5\u8bc4\u4f30','\u6570\u636e\u8d28\u91cf\u4e0e\u65f6\u7a7a\u504f\u5dee','\u5efa\u7b51\u80fd\u6548\u4e0e\u51cf\u78b3','\u751f\u6210\u5f0f\u8bbe\u8ba1','\u70ed\u73af\u5883\u4e0e\u6c14\u5019','\u591c\u95f4\u7167\u660e\u4e0e\u611f\u77e5'],['Urban perception','Visual features','Multimodal representation','Socioeconomic equity','Restoration and health','Walking and cycling','Planning and renewal','Multisensory environments','Interpretability and evaluation','Data quality and temporal bias','Building energy and carbon','Generative design','Thermal environment','Night lighting']))
COLORS=['#0077BB','#EE7733','#009988','#AA4499','#CCBB44','#66CCEE','#CC6677','#4477AA']

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.output);out=root/'figures';out.mkdir(exist_ok=True)
 records=json.loads((root/'library.json').read_text(encoding='utf-8'));graphs=json.loads((root/'networks.json').read_text(encoding='utf-8'))
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'svg.fonttype':'none','pdf.fonttype':42})
 def save(fig,name):
  for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),dpi=450,facecolor='white',bbox_inches='tight')
  plt.close(fig)
 manifest=[]
 for kind,data in graphs.items():
  G=nx.Graph();G.add_nodes_from((n['id'],n) for n in data['nodes']);G.add_weighted_edges_from((e['source'],e['target'],e['weight']) for e in data['edges'])
  communities=list(nx.community.greedy_modularity_communities(G,weight='weight')) if G.number_of_edges() else [{n} for n in G]
  communities.sort(key=len,reverse=True);membership={n:i for i,c in enumerate(communities) for n in c}
  pos={}
  columns=math.ceil(math.sqrt(len(communities)))
  for ci,community in enumerate(communities):
   local=nx.spring_layout(G.subgraph(community),seed=42,iterations=150,weight=None,scale=.7)
   for node,xy in local.items():pos[node]=xy+np.array([(ci%columns)*2.5,-(ci//columns)*2.4])
  fig,ax=plt.subplots(figsize=(10,8));ax.axis('off')
  for i,c in enumerate(communities):
   if len(c)<3:continue
   xy=np.array([pos[n] for n in c]);center=xy.mean(axis=0);width,height=np.ptp(xy,axis=0)+.12
   ax.add_patch(Ellipse(center,width,height,facecolor=COLORS[i%8],alpha=.07,edgecolor='none',zorder=0))
  nx.draw_networkx_edges(G,pos,ax=ax,alpha=.22,width=[.4+.4*math.sqrt(d['weight']) for _,_,d in G.edges(data=True)],edge_color='#64748B')
  nx.draw_networkx_nodes(G,pos,ax=ax,node_size=[22+36*G.nodes[n]['weight'] for n in G],node_color=[COLORS[membership[n]%8] for n in G],edgecolors='white',linewidths=.7)
  ranked=sorted(G,key=lambda n:G.nodes[n]['weight'],reverse=True);chosen=ranked[:min(16,len(G))]
  if kind=='themes':chosen=ranked
  used=[]
  for j,n in enumerate(chosen):
   label=THEMES.get(G.nodes[n]['label'],G.nodes[n]['label']);label=label if len(label)<48 else label[:45]+'...'
   x,y=pos[n]
   ty=y+.14
   while any(abs(x-xx)<1.2 and abs(ty-yy)<.24 for xx,yy in used):ty+=.25
   used.append((x,ty));ax.annotate(label,(x,y),xytext=(x,ty),fontsize=6.5,ha='center',arrowprops=dict(arrowstyle='-',color='#94A3B8',lw=.5),bbox=dict(facecolor='white',alpha=.8,edgecolor='none',pad=1))
  title={'authors':'Co-authorship network','institutions':'Institution co-occurrence network','keywords':'Author-keyword co-occurrence network','themes':'Inferred-theme co-occurrence network'}[kind]
  ax.set_title(title,loc='left',fontsize=14,fontweight='bold',pad=18)
  fig.text(.12,.035,f'N = {len(records)} documents | Node area: document frequency | Edges: shared documents\nColors: greedy-modularity communities (colors repeat beyond 8); pale envelopes are visual aids.\nLocal corpus; provisional author identities; themes are analyst-inferred.',fontsize=7,color='#475569')
  fig.subplots_adjust(bottom=.15);save(fig,kind+'_network')
  manifest.append(dict(figure=kind+'_network',nodes=len(G),edges=G.number_of_edges(),communities=[list(c) for c in communities],seed=42))
 years=sorted({r['year'] for r in records if isinstance(r.get('year'),int)})
 themes=sorted({t for r in records for t in r['themes']},key=lambda t:sum(t in r['themes'] for r in records),reverse=True)
 matrix=[[sum(t in r['themes'] and r['year']==year for r in records) for year in years] for t in themes]
 fig,ax=plt.subplots(figsize=(10,6.5))
 for j,t in enumerate(themes):
  active=[(year,matrix[j][i]) for i,year in enumerate(years) if matrix[j][i]]
  if active:ax.plot([v[0] for v in active],[j]*len(active),color=COLORS[j%8],alpha=.35,linewidth=1)
  for year,count in active:ax.scatter(year,j,s=count*95,color=COLORS[j%8],edgecolor='white',zorder=3);ax.text(year,j,str(count),ha='center',va='center',fontsize=7,color='white')
 ax.set_yticks(range(len(themes)),[THEMES.get(t,t) for t in themes]);ax.invert_yaxis();ax.set_xticks(years);ax.set_xlabel('Publication year');ax.set_title('Thematic timeline of the local literature corpus',loc='left',fontsize=13,pad=18)
 ax.grid(axis='x',alpha=.15);ax.spines[['top','right','left']].set_visible(False)
 fig.text(.02,.015,'Circle area and labels: document counts. Lines connect observations of the same inferred theme; they do not imply influence.\nThis is a corpus-level descriptive timeline, not burst detection or evidence of field-wide research fronts.',fontsize=7)
 fig.tight_layout(rect=[0,.07,1,1]);save(fig,'thematic_timeline')
 (out/'plot-data.json').write_text(json.dumps(dict(networks=manifest,years=years,themes=themes,counts=matrix),ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'data-manifest.md').write_text('Real corpus data: ../library.json and ../networks.json.\nScript: plot_scientific.py. Seed: 42. PNG: 450 DPI; SVG/PDF: vector.\nCommunity method: weighted greedy modularity. No CiteSpace burst or centrality-ring claims.\nTimeline: document counts by publication year and inferred theme; no causal edges.\n',encoding='utf-8')
 print('Saved five figures in PNG, SVG and PDF:',out)
if __name__=='__main__':main()
