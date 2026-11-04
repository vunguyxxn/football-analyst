from backend.cv.compare_role_models import operating_metrics
from backend.cv.compare_role_sources import comparison_specs, sum_diagnostics
from collections import Counter
import pytest


def test_diagnostic_aggregation_sums_counts_before_computing_rates():
    first=operating_metrics(Counter({('referee','referee'):1,('player','referee'):2}),Counter({'goalkeeper':1}))
    second=operating_metrics(Counter({('referee','missed'):2,('player','player'):3}),Counter({'referee':1}))
    result=sum_diagnostics([{**first,'frames':2},{**second,'frames':2}])
    assert result['frames']==4
    assert result['classes']['referee']=={'tp':1,'fp':3,'fn':2,'precision':.25,'recall':1/3}
    assert result['classes']['goalkeeper']['fp']==1
    assert result['player_called_referee']==2


def test_comparison_keeps_v6_gate_reference_and_adds_v10_without_relabelling_candidate():
    v6={'path':'v6.pt','sha256':'six'}
    v10={'path':'v10.pt','sha256':'ten'}
    status={'best_weights':'v11.pt','best_weights_sha256':'eleven'}
    assert set(comparison_specs({'comparison_baseline':v6},status,'v10'))=={'v6','v10'}
    p={'comparison_baseline':v6,'comparison_references':{'v6':v6,'v10':v10}}
    result=comparison_specs(p,status,'v11')
    assert result=={'v6':v6,'v10':v10,'v11':{'path':'v11.pt','sha256':'eleven'}}
    with pytest.raises(ValueError,match='references'):
        comparison_specs(p,status,'v10')
    p['comparison_references']['v6']=v10
    with pytest.raises(ValueError,match='references'):
        comparison_specs(p,status,'v11')
