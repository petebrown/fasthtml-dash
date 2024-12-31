from fasthtml.common import *
from dataclasses import dataclass
from typing import List, Optional, Tuple, Literal
from enum import Enum

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
        Legend("Include play-off games?"),
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

def pens_as_draw_selector():
    return Fieldset(
        Legend("Treat one-off cup games decided by penalty shoot-out as draws?"),
        Label(
            Input(
                type="checkbox",
                id="pens_as_draw",
                name="pens_as_draw",
                role="switch",
                checked=True
            ),
            For="pens_as_draw"
        )
    )

def venue_selector():
    venues = ['Home', 'Away', 'Neutral']
    return Fieldset(
        Legend(Strong('Venues')),
        *[Label(Input(type='checkbox', name='venues', value=venue[0], checked='checked'), venue) for venue in venues]
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

class StatType(Enum):
    OPPOSITION = 'opposition'
    MANAGER = 'manager'
    PLAYER = 'player'

@dataclass
class StatsQueryParams:
    min_season: int
    max_season: int
    league_tiers: Optional[List[int]]
    inc_play_offs: bool
    generic_comps: Optional[List[str]]
    pens_as_draw: bool
    venues: List[str]
    min_games: int
    inc_caretakers: Optional[bool] = None  # Only used for manager stats
    inc_sub_apps: Optional[bool] = None  # Only used for player stats
    stat_type: StatType = StatType.OPPOSITION

class StatsQueryBuilder:
    """Builder for generating reusable statistics queries."""
    
    # Common SQL fragments
    # CASE conditions for win/loss based on whether penalties are treated as draws
    # When user opts NOT to treat one-off cup games decided by penalties as draws, a win/loss is recorded if (1) a penalty shoot-out was used to decide a non-multi-leg game that was drawn, or (2) the game was recorded as a W/L (outcome) and therefore penalties were not involved
    BASE_CASE_CONDITIONS = """
        CASE WHEN
            ({pens_draw} = 0 AND ((COALESCE(c.is_multi_leg, 0) = 0 AND r.outcome = 'D' AND c.pens_outcome = '{outcome}') OR r.outcome = '{match_outcome}'))
        OR 
            ({pens_draw} = 1 AND r.outcome = '{match_outcome}')
        THEN 1 END
    """

    # When user opts NOT to treat one-off cup games decided by penalties as draws, a draw is only recorded if (1) the game finished in a draw and a penalty shoot-out was not used to decide a game, OR (2) the game finished in a draw and a penalty shoot-out was used to decide a multi-leg game
    DRAW_CONDITION = """
        CASE WHEN
            ({pens_draw} = 0 AND r.outcome = 'D' AND (COALESCE(c.is_pen_shootout, 0) = 0 OR (COALESCE(c.is_pen_shootout, 0) = 1) AND COALESCE(c.is_multi_leg, 0) = 1))
        OR 
            ({pens_draw} = 1 AND r.outcome = 'D')
        THEN 1 END
    """

    def __init__(self, params: StatsQueryParams):
        self.params = params
        self.query_params: List = []

    def build_select(self) -> str:
        """Build the SELECT clause based on stat type."""
        group_field = 'm.manager_name' if self.params.stat_type == StatType.MANAGER else 'r.opposition'
        
        return f"""
            SELECT
                {group_field},
                COUNT(*) as P,
                COUNT({self.build_win_condition()}) as W,
                COUNT({self.build_draw_condition()}) as D,
                COUNT({self.build_loss_condition()}) as L,
                SUM(r.goals_for) as GF,
                SUM(r.goals_against) as GA,
                SUM(r.goals_for) - SUM(r.goals_against) as GD,
                ROUND(CAST(COUNT({self.build_win_condition()}) AS FLOAT) / COUNT(*) * 100, 1) as win_pc
        """

    def build_joins(self) -> str:
        """Build the common JOIN clauses."""
        return """
            FROM results r
            LEFT JOIN cup_game_details c ON r.game_date = c.game_date
            LEFT JOIN manager_reigns mr ON r.game_date >= mr.mgr_date_from
                AND (r.game_date <= mr.mgr_date_to OR mr.mgr_date_to IS NULL)
            LEFT JOIN managers m ON mr.manager_id = m.manager_id
            LEFT JOIN seasons s ON r.season = s.season
        """

    def build_win_condition(self) -> str:
        return self.BASE_CASE_CONDITIONS.format(
            pens_draw='?',
            outcome='W',
            match_outcome='W'
        )

    def build_draw_condition(self) -> str:
        return self.DRAW_CONDITION.format(pens_draw='?')

    def build_loss_condition(self) -> str:
        return self.BASE_CASE_CONDITIONS.format(
            pens_draw='?',
            outcome='L',
            match_outcome='L'
        )

    def build_where_clause(self) -> str:
        """Build the WHERE clause with all conditions."""
        conditions = []
        
        # Basic date range
        conditions.append("s.ssn_start >= ? AND s.ssn_start <= ?")
        self.query_params.extend([self.params.min_season, self.params.max_season])

        # Venues
        venue_placeholders = ','.join(['?' for _ in self.params.venues])
        conditions.append(f"r.venue IN ({venue_placeholders})")
        self.query_params.extend(self.params.venues)

        # Play-offs filter
        if not self.params.inc_play_offs:
            conditions.append("COALESCE(c.is_playoff, 0) != 1")

        # League tiers and competition types
        if self.params.league_tiers or self.params.generic_comps:
            tier_comp_conditions = []
            if self.params.league_tiers:
                placeholders = ','.join(['?' for _ in self.params.league_tiers])
                tier_comp_conditions.append(f'r.league_tier IN ({placeholders})')
                self.query_params.extend(self.params.league_tiers)
            if self.params.generic_comps:
                placeholders = ','.join(['?' for _ in self.params.generic_comps])
                tier_comp_conditions.append(f'r.generic_comp IN ({placeholders})')
                self.query_params.extend(self.params.generic_comps)
            conditions.append('(' + ' OR '.join(tier_comp_conditions) + ')')

        # Caretaker filter for manager stats
        if self.params.stat_type == StatType.MANAGER and not self.params.inc_caretakers:
            conditions.append('mr.mgr_role != "Caretaker"')

        return 'WHERE ' + ' AND '.join(conditions)

    def build_group_by(self) -> str:
        """Build the GROUP BY clause based on stat type."""
        group_field = 'm.manager_name' if self.params.stat_type == StatType.MANAGER else 'r.opposition'
        return f"""
            GROUP BY {group_field}
            HAVING COUNT(*) >= ?
            ORDER BY P DESC
        """

    def build_query(self) -> Tuple[str, List]:
        """Build the complete query and parameter list."""
        # Add parameters for the CASE statements
        case_params = [self.params.pens_as_draw] * 8  # 8 occurrences in the case conditions
        self.query_params = case_params.copy()
        
        query = f"""
            {self.build_select()}
            {self.build_joins()}
            {self.build_where_clause()}
            {self.build_group_by()}
        """
        
        # Add min_games parameter for HAVING clause
        self.query_params.append(self.params.min_games)
        
        return query, self.query_params

def get_stats_table(params: StatsQueryParams) -> Table:
    """Generate statistics table based on provided parameters."""
    builder = StatsQueryBuilder(params)
    query, query_params = builder.build_query()
    
    results = db.execute(query, tuple(query_params)).fetchall()
    
    # Column header is either "Opposition" or "Manager" based on stat type
    header = "Manager" if params.stat_type == StatType.MANAGER else "Opposition"
    
    return Table(
        Thead(
            Tr(
                Th(header),
                Th("P"),
                Th("W"),
                Th("D"),
                Th("L"),
                Th("GF"),
                Th("GA"),
                Th("GD"),
                Th("Win %")
            )
        ),
        Tbody(
            *[Tr(*[Td(c) for c in columns]) for columns in results]
        )
    )

# Example usage:
def query_h2h(min_season, max_season, league_tiers, inc_play_offs, 
              generic_comps, pens_as_draw, venues, min_games):
    """Generate head-to-head opposition statistics."""
    params = StatsQueryParams(
        min_season=min_season,
        max_season=max_season,
        league_tiers=league_tiers,
        inc_play_offs=inc_play_offs,
        generic_comps=generic_comps,
        pens_as_draw=pens_as_draw,
        venues=venues,
        min_games=min_games,
        stat_type=StatType.OPPOSITION
    )
    return get_stats_table(params)

def query_manager_stats(min_season, max_season, league_tiers, inc_play_offs,
                       generic_comps, pens_as_draw, venues, min_games, inc_caretakers):
    """Generate manager statistics."""
    params = StatsQueryParams(
        min_season=min_season,
        max_season=max_season,
        league_tiers=league_tiers,
        inc_play_offs=inc_play_offs,
        generic_comps=generic_comps,
        pens_as_draw=pens_as_draw,
        venues=venues,
        min_games=min_games,
        inc_caretakers=inc_caretakers,
        stat_type=StatType.MANAGER
    )
    return get_stats_table(params)

@app.post("/h2h-update")
def process_h2h_inputs(data: dict):
    min_season = data['min_season']
    max_season = data['max_season']
    
    if 'league_tiers' in data:
        league_tiers = data['league_tiers']
    else:
        league_tiers = False
        
    if 'inc_play_offs' in data:
        inc_play_offs = 1
    else:
        inc_play_offs = 0

    if 'generic_comps' in data:
        generic_comps = data['generic_comps']
    else:
        generic_comps = False

    if 'pens_as_draw' in data:
        pens_as_draws = 1
    else:
        pens_as_draws = 0

    min_games = int(data['min_games'])
    
    return Div(
        *[Div(f"{k}: {v}") for k, v in data.items()],
        Div(f"League tiers: {filter_league_tiers(min_season, max_season)}"),
        Div(f"Play-offs: {filter_play_offs(min_season, max_season)}"),
        Div(f"Competitions: {filter_generic_comps(min_season, max_season)}"),
        
        Div(f"Venues: {filter_venues(min_season, max_season)}"),
        Div(query_h2h(min_season, max_season, league_tiers, inc_play_offs, generic_comps, pens_as_draws, data['venues'], min_games))
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
            pens_as_draw_selector(),
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