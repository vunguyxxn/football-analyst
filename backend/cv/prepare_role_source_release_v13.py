"""Supplement v12 with independently grouped small upright keeper/far assistant sources."""
import argparse
import json
from pathlib import Path

from backend.cv.evaluate_role_detector import checked
from backend.cv.prepare_role_source_release_v12 import prepare


def validate_supplement(packet, prior):
    """Require new scene groups and genuine small primaries in native wide context."""
    if packet['kind'] != 'reviewed_role_source_release_v13':
        raise ValueError('Expected v13 supplement')
    refs = packet['additional_references']
    if len(refs) != 1 or refs[0]['directory'] != 'data/processed/role_source_release_v12' or len(refs[0]['manifest_sha256']) != 64:
        raise ValueError('Prior v12 release must be screened')
    old_families = {s['scene_family'] for s in prior['sources']}
    old_hashes = {s['sha256'] for s in prior['sources']}
    new = {s['id']:s for s in packet['sources']}
    if len(new) != len(packet['sources']) or any(s['scene_family'] in old_families or s['sha256'] in old_hashes for s in new.values()):
        raise ValueError('Supplement reuses prior parent or scene group')
    categories = {}
    for obs in packet['primary_observations']:
        source = new[obs['source_id']]
        region = next(r for r in source['regions'] if r['id'] == obs['region_id'])
        obj = next(d for d in source['decisions'] if d['source_index'] == obs['source_index'])
        a,b,c,d = region['roi']
        if obj['action'] != 'target' or region['negative'] or c-a != source['width'] or c-a < 1920:
            raise ValueError('Primary must retain native wide context')
        if not 0 < (obj['xyxy'][3]-obj['xyxy'][1])*640/max(c-a,d-b) < 24:
            raise ValueError('Primary not truly small at640')
        if obs['pose'] not in {'upright','upright_moving'}:
            raise ValueError('Lying/seated keeper does not cover upright gap')
        if obj.get('role') == 'goalkeeper' and obs['location'] == 'goal' and obs['shirt_color'] in {'blue','cyan','light_gray_white','pink_light'}:
            category = 'small_upright_blue_light_keeper'
        elif obj.get('role') == 'referee' and obs['location'] == 'far_touchline' and obs['shirt_color'] == 'dark':
            category = 'small_dark_far_assistant'
        else:
            raise ValueError('Primary does not cover requested gap')
        categories.setdefault(category,set()).add(source['scene_family'])
    if set(categories) != {'small_upright_blue_light_keeper','small_dark_far_assistant'} or len(set.union(*categories.values())) < 2:
        raise ValueError('Both gaps need distinct new scene groups')
    return {k:sorted(v) for k,v in categories.items()}


def run(root, packet_path, output):
    packet = json.loads(packet_path.read_text(encoding='utf-8'))
    prior = json.loads(checked(root, packet['prior_packet'], packet['prior_packet_sha256']).read_text())
    validate_supplement(packet, prior)
    return prepare(root, packet_path, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', default='docs/fixtures/role_sources_review_v13.json')
    parser.add_argument('--output', default='data/processed/role_source_release_v13')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    result = run(root, root/args.packet, root/args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))
