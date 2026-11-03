import hashlib
import pytest

from backend.cv.balance_role_dataset import crop_labels
from backend.cv.merge_role_sources import select_rows


def packet_and_release():
    mapping={'10':'train_candidate','20':'heldout_review'}
    frames=[{'id':m+'-f250','match_id':m,'frame':250,'split':s,
             'review_status':'agent_reviewed','roi':[0,0,1280,720],
             'objects':[{'id':'g','role':'goalkeeper','xyxy':[100,100,140,180]}]}
            for m,s in mapping.items()]
    rows=[{k:f[k] for k in ['id','match_id','frame','split']} |
          {'label_sha256':hashlib.sha256(crop_labels(f).encode()).hexdigest()} for f in frames]
    return {'frames':frames},{'files':rows,'locked_match_splits':mapping},mapping


def test_only_train_matches_are_selected_even_with_more_heldout_keepers():
    packet,release,mapping=packet_and_release()
    selected=select_rows(packet,release,mapping)
    assert [r['match_id'] for r,f in selected]==['10']
    release['files'][1]['split']='train_candidate'
    with pytest.raises(ValueError,match='identity'):select_rows(packet,release,mapping)


def test_released_role_label_must_match_frozen_review_geometry():
    packet,release,mapping=packet_and_release()
    packet['frames'][0]['objects'][0]['role']='referee'
    with pytest.raises(ValueError,match='reviewed ROI'):select_rows(packet,release,mapping)


def test_packet_coverage_and_match_split_cannot_be_rewritten():
    packet,release,mapping=packet_and_release()
    release['files'].pop()
    with pytest.raises(ValueError,match='coverage'):select_rows(packet,release,mapping)
    packet,release,mapping=packet_and_release()
    release['locked_match_splits']={**mapping,'20':'train_candidate'}
    with pytest.raises(ValueError,match='split'):select_rows(packet,release,mapping)
