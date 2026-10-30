import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const root=path.resolve(process.argv[2]);
const runtime=path.resolve(process.argv[3]||root);
const require=createRequire(path.join(runtime,'package.json'));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const data=JSON.parse(await fs.readFile(path.join(root,'workbook-data.json'),'utf8'));
const wb=Workbook.create();
const specs=[{name:'Catalog',cols:[0,1,2,3,4,5,10,11],widths:[8,68,8,40,52,52,44,20]},
{name:'Reading notes',cols:[0,6,7,8,9,12,13,14],widths:[8,50,30,48,70,50,10,54]}];
for(const spec of specs){
 const sheet=wb.worksheets.add(spec.name);sheet.showGridLines=false;
 const matrix=[spec.cols.map(i=>data.headers[i]),...data.rows.map(r=>spec.cols.map(i=>r[i]))];
 const range=sheet.getRange(`A1:H${matrix.length}`);range.values=matrix;
 range.format.font={name:'Microsoft YaHei',size:10,color:'#253648'};
 range.format.wrapText=true;range.format.verticalAlignment='top';
 sheet.getRange('A1:H1').format={fill:'#234B69',font:{name:'Microsoft YaHei',size:10,bold:true,color:'#FFFFFF'},rowHeight:30};
 sheet.getRange('A1:H1').format.horizontalAlignment='center';
 for(let i=0;i<8;i++)sheet.getRangeByIndexes(0,i,matrix.length,1).format.columnWidth=spec.widths[i];
 for(let r=1;r<matrix.length;r++){
  const lines=Math.max(...matrix[r].map((v,c)=>Math.ceil([...String(v??'')].reduce((n,ch)=>n+(ch.charCodeAt(0)>255?1.8:1),0)/(spec.widths[c]*.9))));
  sheet.getRangeByIndexes(r,0,1,8).format.rowHeight=Math.max(42,lines*15+12);
 }
 sheet.getRange(`A2:A${matrix.length}`).setNumberFormat('0');
 if(spec.name==='Catalog')sheet.getRange(`C2:C${matrix.length}`).setNumberFormat('0');
 sheet.freezePanes.freezeRows(1);sheet.freezePanes.freezeColumns(2);
 const table=sheet.tables.add(`A1:H${matrix.length}`,true,spec.name==='Catalog'?'LiteratureCatalog':'ReadingNotes');table.showFilterButton=true;
}
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:'Catalog!A1:D4',include:'values',tableMaxRows:4,tableMaxCols:4,maxChars:2000})).ndjson);
await fs.mkdir(path.join(root,'preview'),{recursive:true});
for(const spec of specs){
 const preview=await wb.render({sheetName:spec.name,range:'A1:D6',scale:1,format:'png'});
 await fs.writeFile(path.join(root,'preview',spec.name+'.png'),new Uint8Array(await preview.arrayBuffer()));
 const right=await wb.render({sheetName:spec.name,range:'E1:H6',scale:1,format:'png'});
 await fs.writeFile(path.join(root,'preview',spec.name+'-right.png'),new Uint8Array(await right.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(path.join(root,'literature-records.xlsx'));
console.log('Exported workbook: '+data.rows.length+' records');
