"""Read-only metadata join by attachment key. Never changes Zotero."""
import argparse,json,sqlite3,re
from pathlib import Path
from datetime import datetime
p=argparse.ArgumentParser();p.add_argument('--database',required=True);p.add_argument('--storage',required=True);p.add_argument('--output',required=True);a=p.parse_args()
db=Path(a.database).resolve();c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=5);c.execute('PRAGMA query_only=ON')
assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
fields={}
for item,key,value in c.execute('SELECT d.itemID,f.fieldName,v.value FROM itemData d JOIN fields f ON f.fieldID=d.fieldID JOIN itemDataValues v ON v.valueID=d.valueID'):
 fields.setdefault(item,{})[key]=value
authors={}
for item,first,last in c.execute('SELECT ic.itemID,c.firstName,c.lastName FROM itemCreators ic JOIN creators c ON c.creatorID=ic.creatorID JOIN creatorTypes t ON t.creatorTypeID=ic.creatorTypeID WHERE t.creatorType="author" ORDER BY ic.itemID,ic.orderIndex'):
 authors.setdefault(item,[]).append(' '.join(x for x in [first,last] if x))
attachments={key:parent for key,parent in c.execute('SELECT i.key,a.parentItemID FROM items i JOIN itemAttachments a ON a.itemID=i.itemID')}
records=[]
for pdf in Path(a.storage).rglob('*'):
 if pdf.suffix.lower()!='.pdf' or not pdf.is_file():continue
 parent=attachments.get(pdf.parent.name);f=fields.get(parent,{})
 year=re.search(r'\b(19|20)\d{2}\b',f.get('date',''))
 records.append(dict(path=str(pdf),attachment_key=pdf.parent.name,parent_item_id=parent,matched=bool(f),title=f.get('title'),authors=authors.get(parent,[]),year=int(year[0]) if year else None,journal=f.get('publicationTitle'),doi=f.get('DOI'),abstract=f.get('abstractNote',''),metadata_source=str(db)))
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
(out/'zotero-metadata.json').write_text(json.dumps(dict(database=str(db),database_mtime=datetime.fromtimestamp(db.stat().st_mtime).isoformat(),records=records),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(pdf=len(records),matched=sum(r['matched'] for r in records),authors=sum(bool(r['authors']) for r in records),year=sum(bool(r['year']) for r in records),abstract=sum(bool(r['abstract']) for r in records))))
