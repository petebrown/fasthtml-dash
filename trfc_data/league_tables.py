from fasthtml.common import *
import pandas as pd

data_dir = './data'

def league_tabs_df():
    return pd.read_csv(f'{data_dir}/league_tables.csv', parse_dates=['game_date'])

def league_tabs_eos_df():
    return pd.read_csv(f'{data_dir}/league_tables_eos.csv')

def filter_lge_table(df, date):
    return df[df.game_date == date]