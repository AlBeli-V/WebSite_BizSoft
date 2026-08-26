#!/usr/bin/env python3
import argparse, json, os, sys, xml.etree.ElementTree as ET, hashlib


def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Validate BIZSoft SVG asset package")
    ap.add_argument("root")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    errors, warnings = [], []
    svg_files = []
    for base, _, files in os.walk(root):
        for name in files:
            if name.lower().endswith('.svg'):
                svg_files.append(os.path.join(base, name))
    if not svg_files:
        errors.append("No SVG files found")
    for p in svg_files:
        rel = os.path.relpath(p, root)
        try:
            tree = ET.parse(p)
            el = tree.getroot()
        except Exception as e:
            errors.append(f"{rel}: invalid XML: {e}")
            continue
        vb = el.attrib.get('viewBox') or el.attrib.get('viewbox')
        if vb != '0 0 512 512':
            errors.append(f"{rel}: expected viewBox='0 0 512 512', got {vb!r}")
        if el.attrib.get('width') not in (None, '512', '512px', '256', '256px', '128', '128px'):
            warnings.append(f"{rel}: unusual width={el.attrib.get('width')}")
        text = open(p, encoding='utf-8', errors='ignore').read().lower()
        if '<rect' in text and ('fill="#fff"' in text or 'fill="white"' in text or 'fill="#ffffff"' in text):
            warnings.append(f"{rel}: contains white rectangle; verify background transparency")
    for required in ('manifest.json',):
        matches = []
        for base, _, files in os.walk(root):
            if required in files:
                matches.append(os.path.join(base, required))
        if not matches:
            warnings.append(f"Missing {required}")
    hashes = {}
    for p in svg_files:
        h = hash_file(p)
        hashes.setdefault(h, []).append(os.path.relpath(p, root))
    dupes = [v for v in hashes.values() if len(v) > 1]
    for group in dupes:
        warnings.append("Identical SVG payloads: " + ", ".join(group))
    print(json.dumps({"root": root, "svg_count": len(svg_files), "errors": errors, "warnings": warnings, "status": "PASS" if not errors else "FAIL"}, ensure_ascii=False, indent=2))
    sys.exit(1 if errors else 0)

if __name__ == '__main__':
    main()
