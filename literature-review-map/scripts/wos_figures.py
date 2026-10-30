"""Curved co-citation map, citation burst intervals and cluster time profiles."""
import argparse,json,math
from pathlib import Path
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch,Polygon
from scipy.spatial import ConvexHull
import matplotlib.patheffects as pe
COLORS=['#2889A8','#D78939','#9166B0','#419B7C','#CA6480','#7E91C9']
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.output);out=root/'figures';out.mkdir(exist_ok=True)
 def load(name):return json.loads((root/(name+'.json')).read_text(encoding='utf-8'))
 graph=load('cocitation-network');refs={r['id']:r for r in load('references')};clusters=load('clusters');bursts=load('bursts');params=load('parameters');quality=load('quality-report');years=params['years']
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'none','pdf.fonttype':42})
 def save(fig,name):
  for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),dpi=450,bbox_inches='tight',facecolor='white')
  plt.close(fig)
 G=nx.Graph();G.add_nodes_from(r['id'] for r in graph['nodes']);G.add_weighted_edges_from((e['source'],e['target'],e['cosine']) for e in graph['edges'])
 # Only display filtering; clustering and exports use every thresholded analysis edge.
 display=nx.maximum_spanning_tree(G,weight='weight');display.add_nodes_from(G)
 for n in G:
  neighbors=sorted(G[n],key=lambda v:(-G[n][v]['weight'],v))[:3]
  for v in neighbors:display.add_edge(n,v,**G[n][v])
 pos={};centers={};k=len(clusters)
 for c in clusters:
  ci=c['cluster'];angle=math.pi/2+ci*2*math.pi/max(k,1);center=np.array([math.cos(angle)*1.05,math.sin(angle)*.8]) if k>1 else np.zeros(2);centers[ci]=center
  local=nx.kamada_kawai_layout(G.subgraph(c['reference_ids']),weight=None,scale=.68)
  for n,xy in local.items():pos[n]=xy+center
 fig,ax=plt.subplots(figsize=(11,9));fig.subplots_adjust(left=.04,right=.96,top=.86,bottom=.13);ax.axis('off');ax.set_xlim(-2.15,2.15);ax.set_ylim(-1.55,1.95)
 for c in clusters:
  pts=np.array([pos[n] for n in c['reference_ids']]);color=COLORS[c['cluster']%6]
  if len(pts)>=3:
   hull=pts[ConvexHull(pts).vertices];mid=hull.mean(axis=0);ax.add_patch(Polygon(mid+(hull-mid)*1.16,facecolor=color,edgecolor=color,alpha=.09,lw=1))
 for i,(u,v,d) in enumerate(display.edges(data=True)):
  same=refs[u]['cluster']==refs[v]['cluster'];color=COLORS[refs[u]['cluster']%6] if same else '#8C99AA'
  ax.add_patch(FancyArrowPatch(pos[u],pos[v],arrowstyle='-',connectionstyle=f'arc3,rad={(.10+.04*(i%3))*(-1 if i%2 else 1)}',color=color,alpha=.3 if same else .10,lw=.3+1.5*d['weight']))
 burst_ids={b['reference_id'] for b in bursts}
 for n in G:
  x,y=pos[n];size=18+refs[n]['frequency']*2.5;color=COLORS[refs[n]['cluster']%6];ax.scatter(x,y,s=size,facecolor=color,edgecolor='#C83E52' if n in burst_ids else 'white',linewidth=1.3,zorder=3)
 selected=[]
 for c in clusters:selected+=sorted(c['reference_ids'],key=lambda n:-refs[n]['frequency'])[:5]
 fig.canvas.draw();renderer=fig.canvas.get_renderer();boxes=[]
 for n in selected:
  best=None;xy=pos[n];label=refs[n]['label']
  for dx,dy in [(7,8),(-7,8),(7,-13),(-7,-13),(0,20),(0,-23),(14,30),(-14,-30)]:
   ha='left' if dx>0 else 'right' if dx<0 else 'center';t=ax.annotate(label,xy,xytext=(dx,dy),textcoords='offset points',ha=ha,fontsize=8);box=t.get_window_extent(renderer).expanded(1.05,1.2);t.remove();overlap=sum(box.overlaps(b) for b in boxes);score=overlap*10000+dx*dx+dy*dy
   if best is None or score<best[0]:best=(score,dx,dy,ha,box)
  _,dx,dy,ha,box=best;boxes.append(box);t=ax.annotate(label,xy,xytext=(dx,dy),textcoords='offset points',ha=ha,fontsize=8,color='#26364B',zorder=5);t.set_path_effects([pe.withStroke(linewidth=3,foreground='white')])
 fig.text(.05,.95,'Co-citation structure',fontsize=19,fontweight='bold',color='#24364B');fig.text(.05,.907,f"{quality['records']} citing papers | {len(G)} selected references | {k} exploratory clusters | Q = {quality['modularity'] if quality['modularity'] is not None else float('nan'):.3f}",fontsize=10,color='#62748B')
 legend='   '.join(f"C{c['cluster']}: {c['nodes']} references" for c in clusters)
 fig.text(.05,.065,legend+'\n'+f"Colors: Louvain clusters. Node area: local citations. Curves: co-citation cosine similarity.\nDisplay: {display.number_of_edges()} links (top-3 neighbors + maximum spanning forest); analysis: {G.number_of_edges()} links.\nRed outlines: default-model burst candidates. Interpret clusters with the reported modularity and observation window.",fontsize=8,color='#536477');save(fig,'cocitation_clusters')
 shown=bursts[:20];fig,ax=plt.subplots(figsize=(11,8));fig.subplots_adjust(left=.38,right=.92,top=.83,bottom=.16)
 for i,b in enumerate(shown):
  ax.plot([years[0]-.35,years[-1]+.35],[i,i],color='#DCE6F1',lw=7,solid_capstyle='round');ax.plot([b['begin']-.32,b['end']+.32],[i,i],color='#C74962',lw=7,solid_capstyle='round');ax.text(years[-1]+.53,i,f"{b['strength_loglik_gain']:.2f}",va='center',fontsize=8)
 ax.set_yticks(range(len(shown)),[b['label']+'  ['+b['reference_id'][:4]+']' for b in shown]);ax.invert_yaxis();ax.set_xticks(years);ax.set_xlim(years[0]-.5,years[-1]+.8);ax.tick_params(length=0,pad=10);ax.spines[:].set_visible(False)
 if not shown:ax.text(.5,.5,'No bursts at the configured parameters',transform=ax.transAxes,ha='center')
 fig.text(.04,.95,'Citation burst candidates',fontsize=19,fontweight='bold',color='#24364B');fig.text(.04,.90,f"Top {len(shown)} of {len(bursts)} intervals | s = {params['s']:g}, gamma = {params['gamma']:g}, minimum duration = {params['min_duration']} year(s)",fontsize=10,color='#62748B')
 fig.text(.04,.055,'Two-state binomial model; strengths are log-likelihood gains, not CiteSpace-equivalent scores.\nLocal citing-document counts normalized by annual corpus size; end-year bursts are right-censored.\nCheck sensitivity.json for persistence under alternative penalties and minimum durations.',fontsize=8,color='#536477');save(fig,'citation_bursts')
 fig,ax=plt.subplots(figsize=(10,5));fig.subplots_adjust(left=.20,right=.94,top=.80,bottom=.22)
 for c in clusters:
  ci=c['cluster'];counts=c['annual_citing_counts'];color=COLORS[ci%6]
  for i,y in enumerate(years):
   if i:ax.add_patch(FancyArrowPatch((years[i-1],ci),(y,ci),connectionstyle='arc3,rad=.1',arrowstyle='-',color=color,lw=2,alpha=.35))
   ax.scatter(y,ci,s=counts[i]*7+30,color=color,edgecolor='white',zorder=3);ax.text(y,ci,str(counts[i]),color='white',ha='center',va='center',zorder=4)
 ax.set_yticks(range(k),[f"C{c['cluster']} ({c['nodes']} references)" for c in clusters]);ax.set_xticks(years);ax.set_xlim(years[0]-.4,years[-1]+.4);ax.set_ylim(k-.4,-.6);ax.spines[:].set_visible(False);ax.tick_params(length=0,pad=10)
 fig.text(.04,.93,'Cluster attention over time',fontsize=18,fontweight='bold',color='#24364B');fig.text(.04,.045,'Counts: distinct sample papers citing at least one reference in each cluster; clusters can overlap in citing papers.\nCurves connect the same cluster across years; they do not represent citation flows or causal transitions.\nExport date(s): '+', '.join(quality['export_dates']),fontsize=8,color='#536477');save(fig,'cluster_timeline')
 (out/'display-network.json').write_text(json.dumps(dict(nodes=sorted(display.nodes()),edges=[dict(source=u,target=v,cosine=d['weight']) for u,v,d in display.edges(data=True)],positions={n:list(map(float,xy)) for n,xy in pos.items()}),indent=2),encoding='utf-8')
 print('Saved 3 figures as PNG, SVG and PDF')
if __name__=='__main__':main()
