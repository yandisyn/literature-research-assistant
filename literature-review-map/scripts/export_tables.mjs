import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const root=path.resolve(process.argv[2]);
const require=createRequire(path.join(path.resolve(process.argv[3]||root),'package.json'));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const tables=JSON.parse(await fs.readFile(path.join(root,'tables.json'),'utf8'));
const wb=Workbook.create();
await fs.mkdir(path.join(root,'preview'),{recursive:true});
for(const [i,t] of tables.entries()){
 const sheet=wb.worksheets.add(t.name);sheet.showGridLines=false;
 const matrix=[t.headers,...t.rows];
 const range=sheet.getRangeByIndexes(0,0,matrix.length,t.headers.length);range.values=matrix;
 range.format.font={name:'Arial',size:10,color:'#24364B'};range.format.wrapText=true;range.format.verticalAlignment='top';range.format.rowHeight=62;
 sheet.getRangeByIndexes(0,0,1,t.headers.length).format={fill:'#234B69',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:32};
 const widths=t.headers.map(h=>h==='abstract'?100:['title','label_candidates'].includes(h)?55:['authors','doi'].includes(h)?36:22);
 t.headers.forEach((h,c)=>{sheet.getRangeByIndexes(0,c,matrix.length,1).format.columnWidth=widths[c];});
 for(let r=1;r<matrix.length;r++){
  const lines=Math.max(...matrix[r].map((v,c)=>String(v??'').split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(line.length/(widths[c]*.8))),0)));
  sheet.getRangeByIndexes(r,0,1,t.headers.length).format.rowHeight=Math.min(409,Math.max(34,lines*14+12));
 }
 sheet.freezePanes.freezeRows(1);
 if(t.rows.length)sheet.tables.add(range.address,true,'Data'+i).showFilterButton=true;
 for(let c=0;c<t.headers.length;c+=4){
  const col=n=>String.fromCharCode(65+n);
  const preview=await wb.render({sheetName:t.name,range:`${col(c)}1:${col(Math.min(c+3,t.headers.length-1))}${Math.min(5,matrix.length)}`,scale:1,format:'png'});
  await fs.writeFile(path.join(root,'preview',`${i}-${c}.png`),new Uint8Array(await preview.arrayBuffer()));
 }
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'literature-summary.xlsx'));
console.log(JSON.stringify(tables.map(t=>({sheet:t.name,records:t.rows.length}))));
