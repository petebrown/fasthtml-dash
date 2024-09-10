from .utils import all_results
import pandas as pd
from fasthtml.common import *

data_dir = './data'

def get_managers():
    return pd.read_csv(f'{data_dir}/managers.csv', parse_dates=['manager_dob'])

def get_manager_reigns():
    return pd.read_csv(f'{data_dir}/manager_reigns.csv', parse_dates=['mgr_date_from', 'mgr_date_to'])

def results_with_managers():
    results = all_results()
    managers_df = get_managers()
    manager_reigns_df = get_manager_reigns()

    results_with_managers = pd.merge_asof(
        results.sort_values('game_date'), 
        manager_reigns_df.sort_values('mgr_date_from'),
        left_on='game_date', 
        right_on='mgr_date_from', 
        direction='backward',
        allow_exact_matches=True
    )

    results_with_managers = results_with_managers[
        (results_with_managers['game_date'] >= results_with_managers['mgr_date_from']) &
        (results_with_managers['game_date'] <= results_with_managers['mgr_date_to'])
    ]

    return pd.merge(
        results_with_managers,
        managers_df,
        left_on='manager_id',
        right_on='manager_id',
        how='left'
    )