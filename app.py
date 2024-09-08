from fasthtml.common import *
from trfc_data.h2h_all import *
from trfc_data.player_apps import *

def df_to_html(df, table_id=None, extra_classes=None):
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
    classes = ['table']
    if extra_classes:
        classes.extend(extra_classes)
    class_list = ' '.join(classes)

    df['game_date_str'] = df['game_date'].astype(str)
    df['game_date'] = df['game_date'].dt.strftime('%d/%m/%Y')
    df['game_date'] = df.apply(lambda row: A(
        f"{row['game_date']}",
        cls = "btn btn-primary",
        href = f"#{row.game_date_str}",
        data_bs_toggle = "collapse",
        role = "button",
        aria_expanded = "false",
        aria_controls = row.game_date_str,
        hx_post = f'/match_details/{row.game_date_str}',
        target_id = f'content_{row.game_date_str}',
        hx_swap = 'innerHTML'),
    axis=1)
    return Div(
        Table(
            Thead(Tr(*[Th(col) for col in df.columns[:-1]])),
            Tbody(
                *[(Tr(*[Td(row[col]) for col in df.columns[:-1]]),
                   Tr(Td(Div(f"Additional content for {row.game_date_str}", id=f"content_{row.game_date_str}"), colspan=len(df.columns)-1), cls="collapse", id=row.game_date_str))
                    for idx, row in df.iterrows()
                ]
            ),
        cls=f'{class_list}'),
        id=table_id
    )

def page_length_options(df, page_length=20):
    n_records = len(df)
    page_length_options = list(range(page_length, n_records, page_length))
    if n_records % page_length != 0:
        page_length_options.append(n_records)
    return [Option(str(o), value=str(o)) for o in page_length_options]

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

cdn = 'https://cdn.jsdelivr.net/npm/bootstrap'
bootstrap_links = [
    Link(href=cdn+"@5.3.3/dist/css/bootstrap.min.css", rel="stylesheet"),
    Link(href=cdn+"-icons@1.11.3/font/bootstrap-icons.min.css", rel="stylesheet"),
    Script(src=cdn+"@5.3.3/dist/js/bootstrap.bundle.min.js")
]

app = FastHTML(hdrs=bootstrap_links)

@app.get("/")
def home():
    return Title("Links"), Div(
        H1('Links'),
        A("Link to Results page", href="/results"),
        Br(),
        A("Link to Line Up page", href="/line_ups"),
        Br(),
        A("Link to Head to Head page", href="/h2h"),
        cls='container')

@app.get("/seasons")
def seasons():
    return Title("Seasons"), Div(
        H1('Seasons'),
        Form(
            *[Div(
                Input(
                    cls="form-check-input",
                    type="checkbox",
                    value=f"{season}",
                    id="flexCheckDefault",
                    name="selected_seasons"
                ),
                Label(
                    f"{season}",
                    cls="form-check-label",
                    _for="flexCheckDefault"
                ),
                cls="form-check") for season in get_season_list()],
            Button('Submit'),
            hx_post='/season', # Send selected season to @app.post('/season')
            hx_target='#season_tabs' # Send response from @app.post('/season') to element with id='results_table'
        ),
        Div(id='season_tabs'),
        cls='container')

@app.post('/season')
async def season_handler(request):
    form_data = await request.form()
    selected_seasons = [value for key, value in form_data.multi_items() if key == 'selected_seasons']

    print(form_data)
    print(selected_seasons)

    # seasons = await request.form()
    # seasons = [season for season in seasons.values()]
    
    # seasons.get('selected_seasons')
    # print(seasons)
    # df = all_results()[all_results().season.isin(seasons)].fillna('-')

    return Div() #df_to_html_expanded(df)

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
            hx_post='/season', # Send selected season to @app.post('/season')
            hx_target='#results_table' # Send response from @app.post('/season') to element with id='results_table'
        ),
        H1('Results'),
        Div(tab, id='results_table'),
        cls='container')

@app.post('/match_details/{game_date}')
def match_details_handler(game_date: str):
    df = filter_game(player_apps_df(), game_date)
    return df_to_html(df, extra_classes=['table-sm'])

@app.post('/season')
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

serve()