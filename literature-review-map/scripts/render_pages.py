"""Render PDFs for visual review/OCR without changing source files."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--first-only', action='store_true')
    p.add_argument('--scale', type=float, default=2)
    a = p.parse_args()
    import pypdfium2
    root = Path(a.output).resolve()
    pages = root / 'pages'
    pages.mkdir(exist_ok=True)
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        if item['status'] != 'extracted':
            continue
        doc = pypdfium2.PdfDocument(item['path'])
        count = min(1,len(doc)) if a.first_only else len(doc)
        for i in range(count):
            target = pages / (item['document_id'] + f'-p{i+1:04d}.png')
            if target.exists():
                continue
            page = doc[i]
            bitmap = page.render(scale=a.scale)
            bitmap.to_pil().save(target)
            bitmap.close()
            page.close()
        doc.close()
        print(Path(item['path']).name, count, flush=True)


if __name__ == '__main__':
    main()
