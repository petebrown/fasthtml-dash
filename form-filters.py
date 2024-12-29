from fasthtml.common import *

db = database("trfc.db")

app, rt = fast_app(
    pico = True,    
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
    
    tier_labels = {
        2: "Championship",
        3: "League One", 
        4: "League Two",
        5: "National League"
    }
    
    labels = [
        Label(
            Input(
                type='checkbox',
                name='league_tiers',
                value=tier,
                checked='checked',
                disabled=tier not in valid_tiers
            ),
            f"{tier}: {label}"
        )
        for tier, label in tier_labels.items()
    ]
    
    return Fieldset(
        Legend('League Tiers'),
        *labels
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
            *[Label(Input(comp, type='checkbox', value=comp, name='generic_comps', checked=True)) for comp in filter_generic_comps(min_season, max_season)])

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
    return [s['ssn_league_tier'] for s in db.query("SELECT DISTINCT(ssn_league_tier) FROM seasons s WHERE s.ssn_start BETWEEN ? AND ? ORDER BY ssn_league_tier", (min_season, max_season))]

def filter_play_offs(min_season, max_season):
    return len([s['season'] for s in db.query("SELECT DISTINCT(season) FROM seasons s WHERE (s.ssn_start BETWEEN ? AND ?) AND s.is_playoffs = 'True' ORDER BY is_playoffs", (min_season, max_season))]) > 0

def filter_generic_comps(min_season, max_season):
    return [s['generic_comp'] for s in db.query("SELECT DISTINCT(generic_comp) FROM results r JOIN seasons s ON r.season = s.season WHERE r.game_type = 'Cup' AND s.ssn_start BETWEEN ? AND ? ORDER BY generic_comp", (min_season, max_season))]

def filter_venues(min_season, max_season):
    return [r['venue'] for r in db.query("SELECT DISTINCT(venue) FROM results r JOIN seasons s ON r.season = s.season WHERE s.ssn_start BETWEEN ? AND ? ORDER BY venue", (min_season, max_season))]

def query_h2h(min_season, max_season, league_tiers, inc_play_offs, generic_comps, venues, min_games):
    league_tier_filter = f"AND r.league_tier IN ({', '.join([str(tier) for tier in league_tiers])})" if league_tiers else ""
    
    po_filter = "AND c.is_playoff != 1" if not inc_play_offs else ""

    generic_comp_filter = f"AND r.generic_comp IN ({', '.join([str(comp) for comp in generic_comps])})" if generic_comps else ""

    print(f"""
        SELECT 
            r.opposition,
            COUNT(*) AS P,
            SUM(CASE WHEN r.outcome = 'W' THEN 1 ELSE 0 END) AS W,
            SUM(CASE WHEN r.outcome = 'D' THEN 1 ELSE 0 END) AS D,
            SUM(CASE WHEN r.outcome = 'L' THEN 1 ELSE 0 END) AS L,
            SUM(r.goals_for) AS GF,
            SUM(r.goals_against) AS GA,
            SUM(r.goals_for) - SUM(r.goals_against) AS GD,
            SUM(CASE WHEN r.outcome = 'W' THEN 1 ELSE 0 END) / COUNT(*) AS WIN_PC
        FROM results r
            JOIN seasons s ON r.season = s.season
            LEFT JOIN cup_game_details c ON r.game_date = c.game_date
        WHERE s.ssn_start BETWEEN {min_season} AND {max_season}
            {league_tier_filter}
            {po_filter}
            {generic_comp_filter}
        GROUP BY r.opposition
    """)

    return db.query(f"""
        SELECT 
            r.opposition,
            COUNT(*) AS P,
            SUM(CASE WHEN r.outcome = 'W' THEN 1 ELSE 0 END) AS W,
            SUM(CASE WHEN r.outcome = 'D' THEN 1 ELSE 0 END) AS D,
            SUM(CASE WHEN r.outcome = 'L' THEN 1 ELSE 0 END) AS L,
            SUM(r.goals_for) AS GF,
            SUM(r.goals_against) AS GA,
            SUM(r.goals_for) - SUM(r.goals_against) AS GD,
            SUM(CASE WHEN r.outcome = 'W' THEN 1 ELSE 0 END) / COUNT(*) AS WIN_PC
        FROM results r
            JOIN seasons s ON r.season = s.season
            LEFT JOIN cup_game_details c ON r.game_date = c.game_date
        WHERE s.ssn_start BETWEEN {min_season} AND {max_season}
            {league_tier_filter}
            {po_filter}
            {generic_comp_filter}
        GROUP BY r.opposition
    """)

@app.post("/h2h-update")
def process_h2h_inputs(data: dict):
    min_season = data['min_season']
    max_season = data['max_season']
    if 'league_tiers' in data:
        league_tiers = data['league_tiers']
    else:
        league_tiers = False
        
    if 'inc_play_offs' in data:
        inc_play_offs = True
    else:
        inc_play_offs = False

    if 'generic_comps' in data:
        generic_comps = data['generic_comps']
    else:
        generic_comps = False
    
    return Div(
        *[Div(f"{k}: {v}") for k, v in data.items()],
        Div(f"League tiers: {filter_league_tiers(min_season, max_season)}"),
        Div(f"Competitions: {filter_generic_comps(min_season, max_season)}"),
        Div(f"Play-offs: {filter_play_offs(min_season, max_season)}"),
        Div(f"Venues: {filter_venues(min_season, max_season)}"),
        Div(query_h2h(min_season, max_season, league_tiers, inc_play_offs, generic_comps, data['venues'], data['min_games']))
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