from fasthtml.common import *

db = database("trfc.db")

app, rt = fast_app(
    pico=True,
    hdrs = ()
)

def season_selector(type):
    if type == 'min':
        name = 'min_season'
        default_ssn = 1921
    else:
        name = 'max_season'
        default_ssn = 2024
    return Input(type="range", name=f"{name}", min=1921, max=2024, value=f"{default_ssn}")

def league_tier_selector(min_season=1921, max_season=2024):
    valid_tiers = filter_league_tiers(min_season, max_season)
    return Fieldset(
        Legend('League Tiers'),
        Label(
            Input(type='checkbox', name='league_tier', value=2, checked='checked'),
            "2: Championship",
            disabled=True if 2 not in valid_tiers else False
        ),
        Label(
            Input(type='checkbox', name='league_tier', value=3, checked='checked'),
            "3: League One",
            disabled=True if 3 not in valid_tiers else False
        ),
        Label(
            Input(type='checkbox', name='league_tier', value=4, checked='checked'),
            "4: League Two",
            disabled=True if 4 not in valid_tiers else False
        ),
        Label(
            Input(type='checkbox', name='league_tier', value=5, checked='checked'),
            "5: National League",
            disabled=True if 5 not in valid_tiers else False
        )
    )

def play_off_selector():
    return Fieldset(
        Legend(Strong("Include play-off games?")),
        Label(
            Input(
                "Include play-off games?",
                type="checkbox",
                id="inc_play_offs",
                name="inc_play_offs",
                role="switch",
                checked=True
            ),
            For="inc_play_offs"
        )
    )

def competition_selector(min_season=1921, max_season=2024):
    return Fieldset(
        Legend(Strong('Competitions')),
            *[Label(Input(comp, type='checkbox', value=comp)) for comp in filter_generic_comps(min_season, max_season)],
        name='generic_comps')
    # return Fieldset(
    #     Legend("Cup competitions:"),
    #     Label(
    #         Input(type="checkbox", name="competition", value="Anglo-Italian Cup", checked="checked"),
    #         "Anglo-Italian Cup"
    #     ),
    #     Label(
    #         Input(type="checkbox", name="competitions", value="Associate Members' Cup", checked="checked"),
    #         "Associate Members' Cup"
    #     ),
    #     Label(
    #         Input(type="checkbox", name="competitions", value="FA Cup", checked="checked"),
    #         "FA Cup"
    #     ),
    #     Label(
    #         Input(type="checkbox", name="competitions", value="FA Trophy", checked="checked"),
    #         "FA Trophy"
    #     ),
    #     Label(
    #         Input(type="checkbox", name="competitions", value="Full Members' Cup", checked="checked"),
    #         "Full Members' Cup"
    #     ),
    #     Label(
    #         Input(type="checkbox", name="competitions", value="League Cup", checked="checked"),
    #         "League Cup"
    #     ),
    #     Label(
    #         Input(type="checkbox", name="competitions", value="War League", checked="checked"),
    #         "War League"
    #     )
    # )

def venue_selector():
    return Fieldset(
        Legend('Venues'),
        Label(
            Input(type='checkbox', name='venues', value='H', checked='checked'),
            "Home"
        ),
        Label(
            Input(type='checkbox', name='venues', value='A', checked='checked'),
            "Away"
        ),
        Label(
            Input(type='checkbox', name='venues', value='N', checked='checked'),
            "Neutral"
        )
    )

def min_game_selector(page, min_no=1):
    if page == 'h2h':
        label_text = 'meetings'
    elif page == 'managers':
        label_text = 'games managed'
    elif page == 'players':
        label_text = 'starts'
        min_no = 0
    return Label(
        f'Minimum number of {label_text}:',
        Input(type="range", name="min_games", min={min_no}, max=100, value=10)
    )

def season_list():
    return [s['season'] for s in db.query("SELECT season FROM seasons ORDER BY season DESC")]

def filter_league_tiers(min_season, max_season):
    return [s['league_tier'] for s in db.query("SELECT DISTINCT(league_tier) FROM seasons s WHERE s.ssn_start BETWEEN ? AND ? ORDER BY league_tier", (min_season, max_season))]

def filter_play_offs(min_season, max_season):
    return len([s['season'] for s in db.query("SELECT DISTINCT(season) FROM seasons s WHERE (s.ssn_start BETWEEN ? AND ?) AND s.is_playoffs = 'True' ORDER BY is_playoffs", (min_season, max_season))]) > 0

def filter_generic_comps(min_season, max_season):
    return [s['generic_comp'] for s in db.query("SELECT DISTINCT(generic_comp) FROM results r JOIN seasons s ON r.season = s.season WHERE r.game_type = 'Cup' AND s.ssn_start BETWEEN ? AND ? ORDER BY generic_comp", (min_season, max_season))]

def filter_venues(min_season, max_season):
    return [r['venue'] for r in db.query("SELECT DISTINCT(venue) FROM results r JOIN seasons s ON r.season = s.season WHERE s.ssn_start BETWEEN ? AND ? ORDER BY venue", (min_season, max_season))]

@app.post("/h2h-update")
def process_h2h_inputs(data: dict):
    min_season = data['min_season']
    max_season = data['max_season']
    return Div(
        *[Div(f"{k}: {v}") for k, v in data.items()],
        Div(f"League tiers: {filter_league_tiers(min_season, max_season)}"),
        Div(f"Competitions: {filter_generic_comps(min_season, max_season)}"),
        Div(f"Play-offs: {filter_play_offs(min_season, max_season)}"),
        Div(f"Venues: {filter_venues(min_season, max_season)}"),
        league_tier_selector(min_season, max_season)
    )

@app.get("/")
def index():
    return Grid(
        Form(
            H6('Season range'),
            Div(
                season_selector('min'),
                season_selector('max')
            ),
            Hr(),
            league_tier_selector(),
            play_off_selector(),
            Hr(),
            competition_selector(),
            Hr(),
            venue_selector(),
            Hr(),
            min_game_selector('h2h'),
        # Routing for form submission
        id="h2h-options",
        hx_trigger="input",
        hx_post="/h2h-update",
        hx_target="#h2h_records",
        hx_swap="innerHTML"
        ), 
        Div(id="h2h_records")
    )

serve()