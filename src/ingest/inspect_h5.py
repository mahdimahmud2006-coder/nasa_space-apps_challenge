"""Inspect actual HDF5 datasets without loading large science arrays."""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def native(value):
    if isinstance(value, h5py.Reference):
        return '<HDF5 reference>'
    if isinstance(value, complex):
        return {'real': native(value.real), 'imag': native(value.imag)}
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    if isinstance(value, np.ndarray):
        return native(value.tolist())
    if isinstance(value, np.generic):
        return native(value.item())
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    if isinstance(value, dict):
        return {str(k): native(v) for k, v in value.items()}
    if isinstance(value, float) and not np.isfinite(value):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def inspect(path):
    result = {'filename': path.name, 'size_bytes': path.stat().st_size,
              'groups': [], 'datasets': []}
    with h5py.File(path, 'r') as file:
        result['top_level_groups'] = list(file.keys())
        def visit(name, obj):
            if isinstance(obj, h5py.Group):
                result['groups'].append('/' + name)
                return
            item = {'path': '/' + name, 'shape': list(obj.shape),
                    'dtype': str(obj.dtype), 'attrs': native(dict(obj.attrs)),
                    'fillvalue': native(obj.fillvalue)}
            if obj.size <= 32:
                item['value'] = native(obj[()])
            elif name.rsplit('/', 1)[-1] in ('xCoordinates', 'yCoordinates'):
                item['first'] = native(obj[0])
                item['last'] = native(obj[-1])
                item['step'] = native(obj[1] - obj[0])
            result['datasets'].append(item)
        file.visititems(visit)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', default='.')
    parser.add_argument('--output', default='data/derived/audit.json')
    args = parser.parse_args()
    files = sorted(Path(args.directory).glob('*.h5'))
    if not files:
        parser.error('No .h5 files found')
    audits = []
    for path in files:
        audit = inspect(path)
        audits.append(audit)
        print(f"FILE {path.name}: {audit['size_bytes']:,} bytes", flush=True)
        for ds in audit['datasets']:
            print(f"  {ds['path']} {ds['shape']} {ds['dtype']}"
                  f" value={ds.get('value', '')}", flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audits, indent=2, allow_nan=False))
    print(f'Audit saved to {output}')


if __name__ == '__main__':
    main()
