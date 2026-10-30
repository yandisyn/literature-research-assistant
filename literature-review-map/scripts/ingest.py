"""Read-only PDF ingestion with content-addressed, page-level evidence cache."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--backend',choices=['pypdf','pdfium'],default='pypdf')
    args = parser.parse_args()
    source, output = Path(args.input).resolve(), Path(args.output).resolve()
    if not source.is_dir():
        parser.error('Input folder does not exist')
    if output == source or source in output.parents:
        parser.error('Output must be outside the input folder')
    from pypdf import PdfReader
    cache = output / 'text'
    cache.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in sorted(source.rglob('*')):
        if path.suffix.lower() != '.pdf' or not path.is_file():
            continue
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        entry = {'path': str(path), 'sha256': sha, 'document_id': sha[:16]}
        target = cache / (sha[:16] + '.json')
        try:
            with path.open('rb') as source_stream:
                if b'%PDF-' not in source_stream.read(1024):
                    raise ValueError('File extension is .pdf but header is not PDF; possibly an HTML download page')
            if target.exists():
                data = json.loads(target.read_text(encoding='utf-8'))
                if data['sha256'] != sha:
                    raise ValueError('Hash collision')
            else:
                if args.backend=='pdfium':
                    import pypdfium2
                    reader = pypdfium2.PdfDocument(path)
                    metadata = reader.get_metadata_dict()
                    source_pages = reader
                else:
                    reader = PdfReader(path)
                    metadata = dict(reader.metadata or {})
                    source_pages = reader.pages
                pages = []
                for number, page in enumerate(source_pages, 1):
                    if args.backend=='pdfium':
                        textpage=page.get_textpage();text=textpage.get_text_range();textpage.close();page.close()
                    else:
                        text = page.extract_text() or ''
                    pages.append({'page': number, 'text': text,
                                  'needs_review': len(text.strip()) < 80})
                if args.backend=='pdfium':reader.close()
                data = {'sha256': sha, 'metadata': metadata, 'pages': pages,'backend':args.backend}
                target.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
            entry.update(status='extracted', pages=len(data['pages']),
                         sparse_pages=[p['page'] for p in data['pages'] if p['needs_review']],
                         text_file=str(target))
        except Exception as exc:
            entry.update(status='failed', error=str(exc))
        entries.append(entry)
        (output / 'manifest.partial.json').write_text(json.dumps({'input_directory':str(source),'files':entries},ensure_ascii=False,indent=2),encoding='utf-8')
        print(path.name, entry['status'], entry.get('pages', 0), flush=True)
    manifest = {'schema_version': 1, 'input_directory': str(source),
                'created_at': datetime.now(timezone.utc).isoformat(), 'files': entries}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
