import pandas as pd
from fasthtml.common import *

results = pd.read_csv('./data/results.csv', parse_dates=['game_date'])

def df_to_html(df, table_id='results', sort_column='game_date', sort_order='asc'):

    return Table(
        Thead(Tr(*[Th(
            col,
            id=col,
            hx_get=f'/sort_table?column={col}&order={"desc" if col == sort_column and sort_order == "asc" else "asc"}',
            hx_target=f'#{table_id}',
            hx_swap='innerHTML'
        ) for col in df.columns])),
        Tbody(*[Tr(*[Td(row[col]) for col in df.columns]) for idx, row in df.iterrows()]),
        id=table_id,
        cls='table'
    )

def filter_season(df, season='2024/25'):
    if isinstance(season, str):
        season = [season]
    return df[df['season'].isin(season)]

app, rt = fast_app()

@app.get("/")
def home():
    global results
    df = results
    return Div(
        df_to_html(
            filter_season(
                df=df,
                season=['2024/25', '2023/24'],
            )), table_id='results')

@app.get('/sort_table')
def get(column: str, order: str):
    global results
    df = filter_season(results)
    df_sorted = df.sort_values(by=column, ascending=(order == 'asc'))
    return df_to_html(df_sorted, table_id='results', sort_column=column, sort_order=order)

serve()