"""Render curved, clustered static maps from saved, traceable screening data."""
import argparse,json,math
from pathlib import Path
import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch,Polygon,Ellipse
from scipy.spatial import ConvexHull
from matplotlib.transforms import Bbox
import matplotlib.patheffects as pe

COLORS=['#2C7BB6','#D87A29','#179B88','#9256AC','#C3A62E','#55AEC4','#CE637C','#6577B1']
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();root=Path(a.output);out=root/'figures'
 data=json.loads((root/'phrase-network.json').read_text(encoding='utf-8'));records=json.loads((root/'screening-records.json').read_text(encoding='utf-8'));report=json.loads((root/'benchmark-report.json').read_text(encoding='utf-8'))
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'svg.fonttype':'none','pdf.fonttype':42})
 def save(fig,name):
  for ext in ['png','svg','pdf']:fig.savefig(out/(name+'.'+ext),dpi=450,facecolor='white',bbox_inches='tight')
  plt.close(fig)
 G=nx.Graph();G.add_nodes_from((n['id'],n) for n in data['nodes']);G.add_weighted_edges_from((e['source'],e['target'],e['weight']) for e in data['edges'])
 groups=sorted(nx.community.greedy_modularity_communities(G,weight='weight'),key=len,reverse=True);cluster={n:i for i,c in enumerate(groups) for n in c}
 components=sorted(nx.connected_components(G),key=len,reverse=True);pos={}
 # Layout the connected core independently so distant isolates cannot collapse it.
 for ci,component in enumerate(components):
  sub=G.subgraph(component)
  if ci==0:
   local=nx.kamada_kawai_layout(sub,weight=None,scale=1)
   for n,xy in local.items():pos[n]=xy*np.array([1.12,.9])+[-.35,0]
  else:
   local=nx.circular_layout(sub,scale=.19 if len(sub)>1 else 0)
   center=np.array([1.30,.85-(ci-1)*.36])
   for n,xy in local.items():pos[n]=xy+center
 fig,ax=plt.subplots(figsize=(12,8.3));fig.subplots_adjust(left=.04,right=.97,top=.86,bottom=.12);ax.set_xlim(-1.75,1.9);ax.set_ylim(-1.18,1.2);ax.axis('off')
 for ci,c in enumerate(groups):
  pts=np.array([pos[n] for n in c]);color=COLORS[ci%8]
  if len(pts)>=3:
   try:
    hull=pts[ConvexHull(pts).vertices];center=hull.mean(axis=0);hull=center+(hull-center)*1.14
    ax.add_patch(Polygon(hull,closed=True,facecolor=color,alpha=.085,edgecolor=color,linewidth=.7,zorder=0))
   except Exception:pass
  elif len(pts)==2:
   center=pts.mean(axis=0);delta=pts[1]-pts[0]
   ax.add_patch(Ellipse(center,np.linalg.norm(delta)+.15,.20,angle=np.degrees(np.arctan2(delta[1],delta[0])),facecolor=color,alpha=.08,edgecolor='none'))
 for i,(u,v,d) in enumerate(G.edges(data=True)):
  same=cluster[u]==cluster[v];color=COLORS[cluster[u]%8] if same else '#7D91A2'
  rad=(.10+.035*(i%3))*(1 if i%2 else -1)
  ax.add_patch(FancyArrowPatch(pos[u],pos[v],arrowstyle='-',connectionstyle=f'arc3,rad={rad}',linewidth=.35+math.sqrt(d['weight'])*.18,color=color,alpha=.32 if same else .13,zorder=1))
 for n in G:
  x,y=pos[n];size=28+G.nodes[n]['frequency']*8;color=COLORS[cluster[n]%8]
  ax.scatter(x,y,s=size*1.35,c=color,alpha=.13,linewidths=0,zorder=2)
  ax.scatter(x,y,s=size,c=color,edgecolors='white',linewidths=1.05,zorder=3)
 fig.canvas.draw();renderer=fig.canvas.get_renderer();occupied=[]
 ranked=sorted(G,key=lambda n:G.nodes[n]['frequency'],reverse=True)
 # Bounding-box label placement keeps labels close to nodes, with short leaders only when needed.
 for n in ranked:
  x,y=pos[n];size=G.nodes[n]['frequency'];font=8.5 if size>=12 else 7.1
  best=None
  for dx,dy in [(8,9),(8,-12),(-8,9),(-8,-12),(0,17),(0,-20),(18,24),(-18,24),(18,-26),(-18,-26)]:
   ha='left' if dx>0 else 'right' if dx<0 else 'center'
   t=ax.annotate(n,(x,y),xytext=(dx,dy),textcoords='offset points',ha=ha,fontsize=font)
   box=t.get_window_extent(renderer).expanded(1.04,1.18);t.remove()
   overlap=sum(max(0,min(box.x1,b.x1)-max(box.x0,b.x0))*max(0,min(box.y1,b.y1)-max(box.y0,b.y0)) for b in occupied)
   score=overlap*100+dx*dx+dy*dy
   if best is None or score<best[0]:best=(score,dx,dy,ha,box)
  _,dx,dy,ha,box=best;occupied.append(box)
  t=ax.annotate(n,(x,y),xytext=(dx,dy),textcoords='offset points',ha=ha,fontsize=font,color='#24344A',zorder=5,arrowprops=dict(arrowstyle='-',color='#8795A4',lw=.4,alpha=.6) if abs(dy)>20 else None)
  t.set_path_effects([pe.withStroke(linewidth=2.5,foreground='white',alpha=.95)])
 fig.text(.045,.94,'Research landscape',fontsize=19,fontweight='bold',color='#203147')
 fig.text(.045,.902,f'{len(records)} records  ·  {len(G)} phrases  ·  {G.number_of_edges()} co-occurrence links',fontsize=10,color='#64748B')
 fig.text(.045,.045,'Node area: document frequency   |   Color: modularity community   |   Curves: shared-document relations\nTop 45 bigrams from titles / available abstracts; edge threshold ≥ 3 documents. Peripheral components placed separately.\nShaded envelopes indicate layout groups, not confidence regions. No citation, burst or centrality-ring inference.',fontsize=8,color='#536477')
 save(fig,'research_landscape_curved')
 years=report['years'];labels=report['nmf_topics'];counts=np.array(report['topic_counts']);bins=list(range(min(years)//5*5,max(years)//5*5+1,5))
 fig,ax=plt.subplots(figsize=(13,7));fig.subplots_adjust(left=.30,right=.97,top=.83,bottom=.19)
 for i in range(len(bins)):ax.axvspan(i-.5,i+.5,color='#F0F4F8' if i%2==0 else '#FAFBFC',zorder=0)
 for j,label in enumerate(labels):
  active=[]
  for i,y in enumerate(bins):
   n=int(sum(counts[j,q] for q,year in enumerate(years) if y<=year<y+5))
   if n:active.append((i,n))
  for (x,n),(xx,nn) in zip(active,active[1:]):
   ax.add_patch(FancyArrowPatch((x,j),(xx,j),arrowstyle='-',connectionstyle='arc3,rad=.10',lw=1.25,color=COLORS[j],alpha=.36,zorder=1))
  for x,n in active:
   ax.scatter(x,j,s=95+n*17,color=COLORS[j],edgecolor='white',linewidth=1.1,zorder=3);ax.text(x,j,str(n),ha='center',va='center',color='white',fontsize=8,zorder=4)
 ax.set_yticks(range(len(labels)),[f'T{j+1}  '+s for j,s in enumerate(labels)]);ax.invert_yaxis();ax.set_xlim(-.5,len(bins)-.5);ax.set_ylim(len(labels)-.45,-.65)
 ax.set_xticks(range(len(bins)),[f'{y}–{str(min(y+4,max(years)))[-2:]}' for y in bins],rotation=45,ha='right',fontsize=8);ax.tick_params(axis='both',length=0,pad=9);ax.spines[:].set_visible(False)
 fig.text(.04,.94,'Thematic trajectories',fontsize=19,fontweight='bold',color='#203147');fig.text(.04,.895,'Local corpus  |  Five-year periods  |  Last period is incomplete',fontsize=10,color='#64748B')
 fig.text(.04,.045,'Bubble area and labels: document counts. Curves connect observations of the same topic, not citations or causal influence.\nEight exploratory NMF topics from titles and available abstracts; one dominant topic per record. One record has no usable English features.\nUnequal abstract coverage and library selection affect the pattern; this is not field-wide frontier or burst analysis.',fontsize=8,color='#536477')
 save(fig,'thematic_trajectories_curved')
 (out/'curved-layout.json').write_text(json.dumps(dict(positions={n:list(map(float,p)) for n,p in pos.items()},communities=[sorted(c) for c in groups],layout='Kamada-Kawai within connected core; peripheral components placed separately',edge_style='curved; no edges added or removed',source='phrase-network.json'),indent=2),encoding='utf-8')
 print('Saved refined maps; source graph unchanged:',len(G),G.number_of_edges())
if __name__=='__main__':main()
