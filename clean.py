from fasthtml.common import *
from dataclasses import dataclass, field
from typing import List
from enum import Enum

db = database('trfc.db')

MIN_GAMES = 10

class AppsType(Enum):
    APPS = 'apps'
    STARTS = 'starts'

@dataclass
class Season:
    season: int

    def __post_init__(self):
        if isinstance(self.season, str):
            try:
                self.season = int(self.season)
            except ValueError:
                raise ValueError(f"Invalid season value: {self.season}")
        
        if not min(get_unique('seasons', 'ssn_start')) <= self.season <= max(get_unique('seasons', 'ssn_start')):
            raise ValueError(f"Invalid season year: {self.season}")

@dataclass
class LeagueTiers:
    league_tiers: List[int] = field(default_factory=list)

    def __post_init__(self):
        if self.league_tiers and all(isinstance(x, str) for x in self.league_tiers):
            self.league_tiers = [int(x) for x in self.league_tiers]

@dataclass
class CupCompetitions:
    cup_competitions: List[str] = field(default_factory=list)

@dataclass
class Venues:
    venues: List[str] = field(default_factory=list)

@dataclass 
class SeasonRecordsAll:
    min_season: Season
    max_season: Season
    league_tiers: List[str] = field(default_factory=list)
    cup_competitions: List[str] = field(default_factory=list)
    venues: List[str] = field(default_factory=list)
    inc_playoffs: bool = True
    pens_as_draw: bool = True
    min_game_no: int = 1
    max_game_no: int = 65

    def __post_init__(self):
        if isinstance(self.min_season, str):
            self.min_season = Season(self.min_season)
        if isinstance(self.max_season, str):
            self.max_season = Season(self.max_season)
        if self.league_tiers:
            self.league_tiers = LeagueTiers(self.league_tiers)
        if self.cup_competitions:
            self.cup_competitions = CupCompetitions(self.cup_competitions)
        if self.venues:
            self.venues = Venues(self.venues)

@dataclass 
class OpponentRecordsAll:
    min_season: Season
    max_season: Season
    league_tiers: List[str] = field(default_factory=list)
    inc_playoffs: bool = True
    cup_competitions: List[str] = field(default_factory=list)
    pens_as_draw: bool = True
    venues: List[str] = field(default_factory=list)
    min_meetings: int = MIN_GAMES

    def __post_init__(self):
        if isinstance(self.min_season, str):
            self.min_season = Season(db.q("SELECT MIN(season) as season FROM seasons"))
        if isinstance(self.max_season, str):
            self.max_season = Season(db.q("SELECT MAX(season) as season FROM seasons"))
        if self.league_tiers:
            self.league_tiers = LeagueTiers(self.league_tiers)
        if self.cup_competitions:
            self.cup_competitions = CupCompetitions(self.cup_competitions)
        if self.venues:
            self.venues = Venues(self.venues)

db = database('trfc.db')

app, rt = fast_app()

league_tiers = {
    2: '2: Championship',
    3: '3: League One',
    4: '4: League Two',
    5: '5: National League',
}

comps = {
    'Anglo-Italian Cup': 'Anglo-Italian Cup',
    'Associate Members\' Cup': 'Associate Members\' Cup',
    'FA Cup': 'FA Cup',
    'FA Trophy': 'FA Trophy',
    'Full Members\' Cup': 'Full Members\' Cup',
    'League Cup': 'League Cup',
    'War League': 'War League'
}

def get_unique(table, col, where='1=1'):
    return [x[f'{col}'] for x in db.q(f"SELECT DISTINCT {table}.{col} FROM {table} WHERE {where} ORDER BY {col}")]

comps_list = get_unique('results', 'generic_comp')

venues = {
    'H': 'Home',
    'A': 'Away',
    'N': 'Neutral'
}

def checkboxes(field: str, items: dict):
    checkboxes = [Div(Input(
        type='checkbox',
        name=field,
        label=v,
        value=k,
        checked=True
    ), Label(v)) for k, v in items.items()]

    return Div(*checkboxes)

ssns = [1921, 2024]

def input_range(name: str, initial_value: int, min_value: int=1, max_value: int=100, step: int=1):
    return Div(
        f'{min_value}',
        Input(
            type="range",
            name=f"{name}",
            value=f'{initial_value}',
            min=f'{min_value}',
            max=f'{max_value}',
            step=f'{step}',
            id=f"{name}_input",
            hx_on_input=f"document.getElementById('{name}_display').innerText = this.value;"
        ),
        Span(initial_value, id=f"{name}_display")
    )

ssn_input_range = (Div(
    '1921', 
    Input(
        type="range",
        name=f"min_season",
        value=1921,
        placeholder=f"Min.",
        min=1921,
        max=2024,
        step=1,
        id=f"min_season",
        hx_on_input=f"document.getElementById('min_season_display').innerText = this.value;"
    ),
    Span(min(ssns), id="min_season_display")
),
Div(
    Input(
        type="range",
        name=f"max_season",
        value=2024,
        placeholder=f"Max.",
        min=1921,
        max=2024,
        step=1,
        id=f"id",
        hx_on_input=f"document.getElementById('max_season_display').innerText = this.value;"
    ),
    Span(max(ssns), id="max_season_display")
))

def get_league_pos(seasons: List[Season]):
    base_query = """
        SELECT
            r.season,
            CAST(r.comp_game_no AS INT) as game_no,
            CAST(r.league_pts  AS INT) as league_pts
        FROM results r
        WHERE r.game_type = 'League'
        AND r.season IN ({})
    """.format(','.join(['?' for _ in seasons]))
    
    return db.q(base_query, seasons)


@rt('/')
def get():
    return Div(
        Form(
            ssn_input_range,
            Hr(),
            checkboxes(field='league_tiers', items=league_tiers),
            Hr(),
            *[CheckboxX(c, label=c, name='cup_competitions', value=c) for c in get_unique('results', 'generic_comp', 'game_type = "Cup"')],
            Hr(),
            checkboxes(field='venues', items=venues),
            Hr(),
            input_range(name='min_meetings', initial_value=MIN_GAMES, min_value=1, max_value=65, step=1),
            hx_post='/form',
            hx_target='#result',
            hx_trigger='change'
        ),
        Div(
            id='result'
        ),
    style="margin: 20px;"
    )

@rt('/form')
def post(form_data: OpponentRecordsAll):
    return form_data, form_data.min_season.season, [f'{c}, ' for c in form_data.cup_competitions.cup_competitions]

@rt('/results')
def get():
    res = db.q("SELECT * FROM full_results WHERE ssn_start = 2024")
    return Div(
        *[Grid(
            Div(r['season']),
            Div(r['game_date'],
                hx_get=f'/game/{r["game_date"]}',
                hx_target=f"#d_{r['game_date'].replace('-', '')}",
                hx_trigger='click'
            ),
            Div(r['game_no']),
            Div(r['opposition']),
            Div(r['venue']),
            Div(r['goalscorers']), id=f"d_{r['game_date'].replace('-', '')}") for r in res],

    cls='container')

@rt('/game/{game_date}')
def get(game_date: str):
    r = db.q(f"SELECT * FROM full_results WHERE game_date = '{game_date}'")[0]
    print(r)
    return Div(
            Div(r['season']),
            Div(r['game_date'],
                hx_get=f'/game/{r["game_date"]}',
                hx_target=f"#d_{r['game_date'].replace('-', '')}",
                hx_trigger='click'
            ),
            Div(r['game_no']),
            Div(r['opposition']),
            Div(r['venue']),
            Div(r['goalscorers']), id=f"d_{r['game_date'].replace('-', '')}"), Grid(Div('hahahahahahahah'))

serve()