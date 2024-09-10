from fasthtml.common import *
import pandas as pd

img_dir = 'https://raw.githubusercontent.com/petebrown/trfcdash/main/inst/app/www'
data_dir = './data'

def all_results():
    return pd.read_csv(f'{data_dir}/results.csv', parse_dates=['game_date'])

def filter_season(df, season):
    return df[df.season == season]

def get_game_dates(df=all_results(), reverse=True):
    return sorted(df.game_date.unique(), reverse=reverse)

def get_game_date_options(game_dates=get_game_dates()):
    return [Option(str(game_date), value=str(game_date)) for game_date in game_dates]

def get_season_list(reverse=True):
    return sorted(all_results().season.unique(), reverse=reverse)

def get_season_options(reverse=True):
    seasons = get_season_list(reverse)
    return [Option(str(season), value=str(season)) for season in seasons]