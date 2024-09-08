import pandas as pd
from fasthtml.common import *

img_dir = 'https://raw.githubusercontent.com/petebrown/trfcdash/main/inst/app/www'
data_dir = './data'

def league_tabs_df():
    return pd.read_csv(f'{data_dir}/league_tables.csv', parse_dates=['game_date'])