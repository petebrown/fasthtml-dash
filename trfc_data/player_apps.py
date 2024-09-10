from fasthtml.common import *
import pandas as pd

img_dir = 'https://raw.githubusercontent.com/petebrown/trfcdash/main/inst/app/www'
data_dir = './data'

def player_apps_df():
    return pd.read_csv(f'{data_dir}/player_apps.csv', parse_dates=['game_date'])

def players_df():
    return pd.read_csv(f'{data_dir}/players.csv')

def goals_df():
    return pd.read_csv(f'{data_dir}/goals.csv', parse_dates=['game_date'])

def join_players(df):
    return df.merge(players_df(), on='player_id', how='left')

def join_goals(df):
    goals = pd.read_csv(f'{data_dir}/goals.csv')
    return df.merge(goals, on='game_id', how='left')

def match_goals_df():
    return goals_df().groupby(['game_date', 'player_id']).size().reset_index().rename(columns={0: 'goals'})

def filter_game(df, game_date):
    return df[df.game_date == game_date]