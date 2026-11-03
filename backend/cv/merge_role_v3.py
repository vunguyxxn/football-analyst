"""Merge locked reviewed counterexamples once each into the v2 train split."""
import json
import hashlib
import shutil
from collections import Counter
from pathlib import Path

from backend.cv.curate_role_counterexamples import validate
from backend.cv.balance_role_dataset import protected_rows
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import verify_dataset, yaml_text


def prepare(root):
    import cv2
    protocol_path = root / 'docs/fixtures/role_training_protocol_v3.json'
    protocol = json.loads(protocol_path.read_text())
    base = root / protocol['merge_base_dataset']
    checked(base, 'manifest.json', protocol['merge_base_manifest_sha256'])
    original = verify_dataset(root, base, root / 'docs/fixtures/role_balance_protocol_v2.json')
    packet_path = checked(root, protocol['counterexamples'], protocol['counterexamples_sha256'])
    output = root / 'data/processed/role_dataset_v3'
    export = root / 'data/processed/role_training_v3/verified_rois'
    if output.exists() or export.exists():
        raise FileExistsError('Use new output directories; never overwrite experiments')
    validate(root, packet_path, verify_assets=True, export=export)
    packet = json.loads(packet_path.read_text())
    sources = {s['id']: s for s in packet['sources']}
    manifest = json.loads((export / 'manifest.json').read_text())
    rows = list(original['files'])
    for row in original['files']:
        for key in ('image', 'label'):
            target = output / row[key]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(checked(base, row[key], row[key+'_sha256']), target)
    for row in manifest['files']:
        added = dict(row)
        for key in ('image', 'label'):
            relative = str(Path(row[key]).with_name('v3-'+Path(row[key]).name)).replace('\\', '/')
            shutil.copyfile(checked(export, row[key], row[key+'_sha256']), output / relative)
            added[key] = relative
        image = cv2.imread(str(output / added['image']))
        added.update(pixel_sha256=hashlib.sha256(str(image.shape).encode()+image.tobytes()).hexdigest(),
                     family=sources[row['source_id']]['scene_family'], source=sources[row['source_id']]['sha256'], sampling_repeat=1,
                     provenance={'packet': digest(packet_path), 'region': row['region_id']})
        rows.append(added)
    result = {**original, 'kind': 'role_dataset_v3', 'files': rows,
              'protocol_sha256': digest(protocol_path), 'images': dict(Counter(r['split'] for r in rows))}
    if protected_rows(result) != protected_rows(original):
        raise ValueError('Protected validation/test rows changed')
    (output / 'manifest.json').write_text(json.dumps(result, indent=2))
    (output / 'data.yaml').write_text(yaml_text(output))
    verify_dataset(root, output, protocol_path)
    print(result['images'])


if __name__ == '__main__':
    prepare(Path(__file__).resolve().parents[2])
