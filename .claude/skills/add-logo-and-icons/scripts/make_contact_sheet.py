#!/usr/bin/env python3
import argparse, html, os

TEMPLATE = '''<!doctype html><html><head><meta charset="utf-8"><title>BIZSoft Brand Asset Contact Sheet</title>
<style>body{{font-family:system-ui,sans-serif;margin:24px;background:#f5f5f5;color:#111}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px}}.card{{background:white;border:1px solid #ddd;border-radius:12px;padding:12px}}.preview{{height:150px;display:flex;align-items:center;justify-content:center;background:linear-gradient(45deg,#eee 25%,transparent 25%),linear-gradient(-45deg,#eee 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#eee 75%),linear-gradient(-45deg,transparent 75%,#eee 75%);background-size:20px 20px;background-position:0 0,0 10px,10px -10px,-10px 0}}.preview img{{max-width:100%;max-height:100%}}.path{{font-size:11px;word-break:break-all;margin-top:8px}}</style></head><body><h1>BIZSoft Brand Asset Contact Sheet</h1><div class="grid">{cards}</div></body></html>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    outdir = os.path.dirname(os.path.abspath(args.output))
    cards=[]
    for base, _, files in os.walk(root):
        for name in sorted(files):
            if not name.lower().endswith('.svg'):
                continue
            p=os.path.join(base,name)
            rel=os.path.relpath(p,outdir).replace(os.sep,'/')
            label=os.path.relpath(p,root)
            cards.append(f'<div class="card"><div class="preview"><img src="{html.escape(rel)}"></div><div class="path">{html.escape(label)}</div></div>')
    os.makedirs(outdir, exist_ok=True)
    with open(args.output,'w',encoding='utf-8') as f:
        f.write(TEMPLATE.format(cards=''.join(cards)))
    print(args.output)

if __name__ == '__main__':
    main()
