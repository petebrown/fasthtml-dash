from fasthtml.common import *
import pandas as pd

img_dir = 'https://raw.githubusercontent.com/petebrown/trfcdash/main/inst/app/www'
data_dir = './data'

def filter_lge(df):
    return df[df.game_type == 'League']

def summarise_results(df, focus):
    return df.groupby([focus]) \
    .agg(
        p=('game_date', 'nunique'),
        w=('outcome', lambda x: (x == 'W').sum()),
        d=('outcome', lambda x: (x == 'D').sum()),
        l=('outcome', lambda x: (x == 'L').sum()),
        gf=('goals_for', 'sum'),
        ga=('goals_against', 'sum'),
        gd=('goal_diff', 'sum'),
        win_pc=('outcome', lambda x: round((x == 'W').sum() / len(x), 2))
    ) \
    .reset_index()

def calc_lge_ppg(df):
    return filter_lge(df) \
    .groupby(['opposition']) \
    .agg(
        p=('game_date', 'nunique'),
        pts=('outcome', lambda x: (x == 'W').sum() * 3 + (x == 'D').sum())
    ) \
    .assign(
        lge_ppg=lambda x: round(x.pts / x.p, 2)
    ) \
    .drop(columns=['p', 'pts']) \
    .reset_index()

def club_crest_and_name(club_name: str):
    img_file = club_name.lower().replace(' ', '-') + '.svg'
    return Div(
        Div(Img(src=f'{img_dir}/images/clubs/{img_file}', width='32px')),
        club_name)

def h2h_all(df):
    res_summary = summarise_results(df, 'opposition')
    lge_ppg = calc_lge_ppg(df)
    df = res_summary.merge(lge_ppg, on='opposition', how='left')

    df['opposition'] = df.opposition.apply(club_crest_and_name)

    df = df.rename(columns={
        'opposition': 'Opposition',
        'p': 'P',
        'w': 'W',
        'd': 'D',
        'l': 'L',
        'gf': 'GF',
        'ga': 'GA',
        'gd': 'GD',
        'lge_ppg': 'PPG',
        'win_pc': 'Win %'
    })

    return df