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

def get_unique(table, col):
    return [x[f'{col}'] for x in db.q(f"SELECT DISTINCT {table}.{col} from {table} order by {col}")]

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

input_range = (Div(
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
    return (
        Form(
            input_range,
            Hr(),
            checkboxes(field='league_tiers', items=league_tiers),
            *[CheckboxX(c, label=c) for c in get_unique('results', 'generic_comp')],
            hx_post='/form',
            hx_target='#result',
            hx_trigger='change'
        ),
        Div(id='result')
    )

@rt('/form')
def post(form_data: SeasonRecordsAll):
    return Table(
        Tr(
            Td(ssn['season']),
            Td(ssn['game_no']),
            Td(ssn['league_pts'])
        ) for ssn in get_league_pos(['2024/25', '2023/24'])
    )

serve()