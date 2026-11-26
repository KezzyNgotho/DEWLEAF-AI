import pandas as pd
from sklearn.model_selection import GroupKFold
from pathlib import Path

def test_groupkfold_no_night_leakage():
    path = 'ml/data/dewleaf_kenya_2024_v2.csv'
    if not Path(path).exists():
        path = 'ml/data/dewleaf_global_2023_2024_v2.csv'
    df = pd.read_csv(path, nrows=50000)
    gkf = GroupKFold(n_splits=5)
    for tr, te in gkf.split(df, groups=df['night_id']):
        overlap = set(df.iloc[tr]['night_id']).intersection(set(df.iloc[te]['night_id']))
        assert not overlap
