"""Bind an immutable curated dataset snapshot to a separate training protocol."""
import json
from pathlib import Path
import shutil

from backend.cv.balance_role_dataset import protected_rows
from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import verify_dataset, yaml_text


def prepare(root, protocol_path):
    protocol = json.loads(protocol_path.read_text())
    source = checked(root, protocol['curated_dataset']+'/manifest.json', protocol['curated_manifest_sha256']).parent
    data_protocol = checked(root, protocol['curation_protocol'], protocol['curation_protocol_sha256'])
    original = verify_dataset(root, source, data_protocol)
    destination = (root/protocol['dataset']).resolve()
    if not destination.is_relative_to(root) or destination.exists():
        raise ValueError('Training snapshot must be a new workspace directory')
    if original['images'] != protocol['expected_images']:
        raise ValueError('Curated image count changed')
    destination.mkdir(parents=True)
    for row in original['files']:
        for kind in ['image', 'label']:
            target = destination/row[kind]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(checked(source, row[kind], row[kind+'_sha256']), target)
    result = {**original, 'kind': 'curated_role_training_snapshot', 'protocol_sha256': digest(protocol_path),
              'curated_manifest_sha256': protocol['curated_manifest_sha256']}
    (destination/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    (destination/'data.yaml').write_text(yaml_text(destination))
    verify_dataset(root, destination, protocol_path)
    if protected_rows(result) != protected_rows(original):
        raise ValueError('Protected rows changed')
    plan = {'protocol_sha256': digest(protocol_path), 'manifest_sha256': digest(destination/'manifest.json'),
            'images': result['images'], 'curated_manifest_sha256': protocol['curated_manifest_sha256'],
            'all_image_label_records_unchanged': result['files'] == original['files'], 'training_started': False}
    checked(source, 'manifest.json', protocol['curated_manifest_sha256'])
    plan_path = (root/protocol['plan']).resolve()
    if not plan_path.is_relative_to(root) or plan_path.exists():
        raise ValueError('Plan must be a new workspace file')
    plan_path.write_text(json.dumps(plan, indent=2)+'\n')
    return plan


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(prepare(root, root/'docs/fixtures/role_sources_training_protocol_v11.json'), indent=2))
