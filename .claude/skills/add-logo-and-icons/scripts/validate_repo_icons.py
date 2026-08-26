#!/usr/bin/env python3
import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET


def list_stems(path):
    if not os.path.isdir(path):
        return set()
    return {os.path.splitext(f)[0] for f in os.listdir(path) if f.lower().endswith('.svg')}


def parse_svg(path, errors):
    try:
        root = ET.parse(path).getroot()
    except Exception as e:
        errors.append(f"invalid SVG XML: {path}: {e}")
        return
    vb = root.attrib.get('viewBox') or root.attrib.get('viewbox')
    if vb != '0 0 512 512':
        errors.append(f"wrong viewBox: {path}: {vb!r}")


def check_pair(root, rel_color, rel_mono, label, errors, warnings):
    cdir = os.path.join(root, rel_color)
    mdir = os.path.join(root, rel_mono)
    c = list_stems(cdir)
    m = list_stems(mdir)
    if not os.path.isdir(cdir) and not os.path.isdir(mdir):
        warnings.append(f"{label}: directories not found; repository layout may have changed")
        return set()
    only_c = sorted(c - m)
    only_m = sorted(m - c)
    if only_c:
        errors.append(f"{label}: missing mono for: {', '.join(only_c)}")
    if only_m:
        errors.append(f"{label}: missing color for: {', '.join(only_m)}")
    for stem in sorted(c & m):
        parse_svg(os.path.join(cdir, stem + '.svg'), errors)
        parse_svg(os.path.join(mdir, stem + '.svg'), errors)
    return c & m


def load_json(path, errors, warnings):
    if not os.path.exists(path):
        warnings.append(f"missing optional/current-snapshot file: {path}")
        return None
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        errors.append(f"invalid JSON: {path}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser(description='Validate BIZSoft vendor/product icon pairs and catalog mapping')
    ap.add_argument('repo_root', nargs='?', default='.')
    args = ap.parse_args()
    root = os.path.abspath(args.repo_root)
    errors, warnings = [], []

    vendor_pairs = check_pair(root,
        'src/assets/vendor-icons/color',
        'src/assets/vendor-icons/mono',
        'vendor-icons', errors, warnings)

    direct_pairs = check_pair(root,
        'src/assets/product-icons/color',
        'src/assets/product-icons/mono',
        'product-icons/direct', errors, warnings)

    catalog_pairs = check_pair(root,
        'src/assets/product-icons/catalog/color',
        'src/assets/product-icons/catalog/mono',
        'product-icons/catalog', errors, warnings)

    pmap_path = os.path.join(root, 'src/data/product-icon-map.json')
    pmap = load_json(pmap_path, errors, warnings)
    if isinstance(pmap, dict):
        missing = sorted({icon_id for icon_id in pmap.values() if isinstance(icon_id, str) and icon_id not in catalog_pairs})
        if missing:
            errors.append('product-icon-map references missing catalog icon pairs: ' + ', '.join(missing))
        bad = [k for k, v in pmap.items() if not isinstance(k, str) or not isinstance(v, str)]
        if bad:
            errors.append(f'product-icon-map contains non-string mapping entries: {len(bad)}')

    for rel in [
        'docs/vendor-icons-manifest.json',
        'docs/catalog-product-icons-manifest.json',
        'docs/catalog-product-icon-map.json',
    ]:
        load_json(os.path.join(root, rel), errors, warnings)

    result = {
        'repo_root': root,
        'counts': {
            'vendor_pairs': len(vendor_pairs),
            'direct_product_pairs': len(direct_pairs),
            'catalog_product_pairs': len(catalog_pairs),
            'product_map_entries': len(pmap) if isinstance(pmap, dict) else None,
        },
        'errors': errors,
        'warnings': warnings,
        'status': 'PASS' if not errors else 'FAIL',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
