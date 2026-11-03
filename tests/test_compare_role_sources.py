from backend.cv.compare_role_models import operating_metrics
from backend.cv.compare_role_sources import sum_diagnostics
from collections import Counter


def test_diagnostic_aggregation_sums_counts_before_computing_rates():
    first=operating_metrics(Counter({('referee','referee'):1,('player','referee'):2}),Counter({'goalkeeper':1}))
    second=operating_metrics(Counter({('referee','missed'):2,('player','player'):3}),Counter({'referee':1}))
    result=sum_diagnostics([{**first,'frames':2},{**second,'frames':2}])
    assert result['frames']==4
    assert result['classes']['referee']=={'tp':1,'fp':3,'fn':2,'precision':.25,'recall':1/3}
    assert result['classes']['goalkeeper']['fp']==1
    assert result['player_called_referee']==2
