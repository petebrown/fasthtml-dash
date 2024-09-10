from fasthtml.common import *
import pandas as pd
from trfc_data.utils import *
from trfc_data.h2h_all import *
from trfc_data.player_apps import *
from trfc_data.league_tables import *
from trfc_data.managers import *

def df_to_html(df, table_id=None, extra_classes=None):
    """
    Convert a pandas DataFrame to an HTML table.
    Column names are used for the table headers.
    """
    classes = ['table']
    if extra_classes:
        classes.extend(extra_classes)
    class_list = ' '.join(classes)
    return Div(
        Table(
            Thead(Tr(*[Th(col) for col in df.columns])),
            Tbody(*[Tr(*[Td(row[col]) for col in df.columns]) for idx, row in df.iterrows()]),
        cls=f'{class_list}'),
        id=table_id
    )

def df_to_html_expanded(df, table_id=None, extra_classes=None):
    """
    Convert a pandas DataFrame to an HTML table where the game_data
    column is converted to a button that triggers a collapse element.
    Column names are used for the table headers.
    """
    classes = ['table']
    if extra_classes:
        classes.extend(extra_classes)
    class_list = ' '.join(classes)
    df['game_date_str'] = df['game_date'].astype(str)
    df['game_date'] = df['game_date'].dt.strftime('%d/%m/%Y')
    df['game_date'] = df.apply(lambda row: A(
        f"{row['game_date']}", cls = "btn btn-primary", href = f"#{row.game_date_str}", data_bs_toggle = "collapse", role = "button", aria_expanded = "false", aria_controls = row.game_date_str,
        hx_post = f'/match_details/{row.game_date_str}',
        target_id = f'content_{row.game_date_str}',
        hx_swap = 'innerHTML'),
    axis=1)
    return Div(
        Table(
            Thead(Tr(*[Th(col) for col in df.columns[:-1]])), # Excludes temporary 'game_date_str' column
            Tbody(
                *[(Tr(*[Td(row[col]) for col in df.columns[:-1]]),
                   Tr(Td(Div("", id=f"content_{row.game_date_str}"), colspan=len(df.columns)-1), cls="collapse", id=row.game_date_str)) for idx, row in df.iterrows()
                ]
            ),
        cls = class_list),
        id = table_id
    )

def page_length_options(df, page_length=20):
    """ 
    * Currently unused *
    Create HTML options for the page length select element.
    """
    n_records = len(df)
    page_length_options = list(range(page_length, n_records, page_length))
    if n_records % page_length != 0:
        page_length_options.append(n_records)
    return [Option(str(o), value=str(o)) for o in page_length_options]

cdn = 'https://cdn.jsdelivr.net/npm/bootstrap'
bootstrap_links = [
    Link(href=cdn+"@5.3.3/dist/css/bootstrap.min.css", rel="stylesheet"),
    Link(href=cdn+"-icons@1.11.3/font/bootstrap-icons.min.css", rel="stylesheet"),
    Script(src=cdn+"@5.3.3/dist/js/bootstrap.bundle.min.js")
]

app = FastHTML(hdrs=bootstrap_links, live=True)

@app.get("/")
def home():
    return Title("Links"), Div(
        H1('Links'),
        A("Link to Seasons page", href="/seasons"),
        Br(),
        A("Link to Results page", href="/results"),
        Br(),
        A("Link to Line Up page", href="/line_ups"),
        Br(),
        A("Link to Head to Head page", href="/h2h"),
        cls='container')

# Function to create season list items
def create_season_list_items(selected_seasons):
    return Ul(
        *[Li(A(f"{season}",
                cls="nav-link",
                href=f"#",
                role="tab",
                id=f"{season}",
                hx_post=f"/season/{season.replace('/', '-')}",
                hx_target="#season_tab",
                hx_swap="innerHTML"),
            cls="nav-item") for season in selected_seasons],
        cls="nav nav-tabs"
    )

@app.get("/seasons")
def seasons():
    return Title("Seasons"), Div(
        H1('Seasons'),
        Form(Div(
            *[Div(
                Input(
                    cls="form-check-input",
                    type="checkbox",
                    value=f"{season}",
                    id="flexCheckDefault",
                    name="selected_seasons",
                    checked="checked" if i == 0 else None
                ),
                Label(
                    f"{season}",
                    cls="form-check-label",
                    _for="flexCheckDefault"
                ),
                cls="form-check") for i, season in enumerate(get_season_list())],
            cls='overflow-auto',
            style='max-height: 290px; width: 150px;'),
            Button('Submit', cls='btn btn-primary'),
            hx_post='/season',
            hx_target='#season_tabs'),
        Div(id='season_tabs', cls='container'),
        cls='container')

@app.post('/season')
async def season_handler(request):
    selected_seasons = await request.form()
    selected_seasons = [value for key, value in selected_seasons.multi_items() if key == 'selected_seasons']

    return Div(
            Ul(
                *[Li(A(f"{season}",
                        cls="nav-link",
                        href=f"#",
                        role="tab",
                        id=f"{season}",
                        hx_post=f"/season/{season.replace('/', '-')}",
                        hx_target="#season_tab",
                        hx_swap="innerHTML"),
                    cls="nav-item") for season in selected_seasons],
                cls="nav nav-tabs"),
            Div(
                df_to_html_expanded(all_results()[all_results().season==max(selected_seasons)], 'results_table'),
                id="season_tab"),
            cls="container")

@app.get("/season/{ssn}", methods=["GET", "POST"])
def season_tab(ssn: str):
    ssn = ssn.replace('-', '/')
    df = all_results().query(f"season == '{ssn}'").fillna('-')
    tab = df_to_html_expanded(df, 'results_table')
    return Div(tab, id='results_table', cls='container')

@app.get("/results")
def results():
    df = all_results().fillna('-')
    df = filter_season(df, max(df.season))
    tab = df_to_html_expanded(df, 'results_table')

    season_options = get_season_options()
    return Title("Results"), Div(
        Form(
            Select(
                *season_options, # Create a list of Option elements
                cls='form-select', # Add class 'form-select' to the select element
                id='season' # Add id 'season' to the select element
            ),
            Button('Submit'),
            hx_post='/season-results', # Send selected season to @app.post('/season')
            hx_target='#results_table' # Send response from @app.post('/season') to element with id='results_table'
        ),
        H1('Results'),
        Div(tab, id='results_table'), # Table that will be updated by @app.post('/season')
        cls='container')

@app.post('/match_details/{game_date}')
def match_details_handler(game_date: str):
    matchday_apps = filter_game(player_apps_df(), game_date)
    league_table = filter_lge_table(league_tabs_df(), game_date)

    matchday_apps = df_to_html(matchday_apps, extra_classes=['table-sm'])
    league_table = df_to_html(league_table, extra_classes=['table-sm'])

    return Div(
        Div(
            Div(matchday_apps, cls='col-sm'),
            Div(league_table, cls='col-sm'),
        cls='row'),
        cls='container-fluid')

@app.post('/season-results')
async def season_handler(request):
    season = await request.form()
    season = season.get('season')
    df = all_results()[all_results().season == season].fillna('-')

    return df_to_html_expanded(df)

@app.get("/line_ups")
def lineup():
    game_date_options = get_game_date_options()
    return Title('Line-up'), Div(
        H1('Line-up'),
        Form(
            Select(
                *game_date_options, # Create a list of Option elements
                cls='form-select', # Add class 'form-select' to the select element
                id='game_date' # Add id 'game_date' to the select element
            ),
            Button('Submit'),
            hx_post='/line_up', # Send selected game_date to @app.post('/line_up')
            hx_target='#line_up' # Send response from @app.post('/page_length') to element with id='line_up'
        ),
        Div(df_to_html(filter_game(player_apps_df(), max(get_game_dates()))), id='line_up'), # Table that will be updated by @app.post('/line_up')
        cls='container')


@app.post('/line_up')
async def line_up_handler(request):
    game_date = await request.form()
    game_date = game_date.get('game_date')
    df = filter_game(player_apps_df(), game_date)

    return df_to_html(df)

@app.get("/h2h")
def h2h():
    df = h2h_all(all_results()).fillna('-')
    tab = df_to_html(df, 'h2h_table')
    page_lengths = page_length_options(h2h_all(all_results()))
    return Title("Head to Head Overview"), Div(
        H1('Head to Head Overview'),
        Form(
            Select(
                *page_lengths, # Create a list of Option elements
                cls='form-select', # Add class 'form-select' to the select element
                id='page_length' # Add id 'page_length' to the select element
            ),
            Button('Submit'),
            hx_post='/page_length', # Send selected page length to @app.post('/page_length')
            hx_target='#h2h_table' # Send response from @app.post('/page_length') to element with id='h2h_table'
        ),
        Div(tab, id='h2h_table'), # Table that will be updated by @app.post('/page_length')
        cls='container')

@app.post('/page_length')
async def page_length_handler(request):
    page_length = await request.form()
    page_length = page_length.get('page_length')
    df = h2h_all(all_results())[:int(page_length)].fillna('-')

    return df_to_html(df)

print(results_with_managers())

serve()