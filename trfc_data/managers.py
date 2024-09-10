from fasthtml.common import *
import pandas as pd

data_dir = './data'

def managers():
    return pd.read_csv(f'{data_dir}/managers.csv', parse_dates=['manager_dob'])

def manager_reigns():
    return pd.read_csv(f'{data_dir}/manager_reigns.csv', parse_dates=['date_from', 'date_to'])

def results_with_managers():
    results = all_results()
    managers = managers()
    manager_reigns = manager_reigns()

    results_with_managers = pd.merge_asof(
        results.sort_values('game_date'), 
        manager_reigns.sort_values('date_from'), 
        left_on='game_date', 
        right_on='date_from', 
        direction='backward',
        allow_exact_matches=True
    )

    # Filter out rows where game_date is not within the correct manager reign period
    results_with_managers = results_with_managers[
        (results_with_managers['game_date'] >= results_with_managers['date_from']) &
        (results_with_managers['game_date'] <= results_with_managers['date_to'])
    ]

    return pd.merge(
        results_with_managers,
        managers,
        left_on='manager_id',
        right_on='manager_id',
        how='left'
    )



results_with_managers()
