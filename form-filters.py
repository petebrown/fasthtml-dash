from fasthtml.common import *
from dataclasses import dataclass
from typing import List, Optional, Tuple, Literal
from enum import Enum
import pandas as pd

db = database("trfc.db")

app, rt = fast_app(
    pico = True,    
    hdrs = ()
)

def season_list():
    return [s['season'] for s in db.query("SELECT season FROM seasons ORDER BY season DESC")]

def season_selector(type):
    min_ssn = min(season_list())[:4]
    max_ssn = max(season_list())[:4]
    if type == 'min':
        name = 'min_season'
        default_ssn = min_ssn
    else:
        name = 'max_season'
        default_ssn = max_ssn
    return Input(type="range", name=f"{name}", min=min_ssn, max=max_ssn, value=f"{default_ssn}")

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
        Legend(Strong('League Tiers')),
        *labels
    )

def play_off_selector():
    return Fieldset(
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
        Label(
            Input(
                "Treat one-off cup games decided by penalty shoot-out as draws?",
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

class BaseQueryBuilder:
    """Base class for building football statistics queries"""
    
    def __init__(self, params: StatsQueryParams):
        self.params = params
        self.query_params: List = []

    def build_base_joins(self) -> str:
        """Common JOIN clauses used across query types"""
        base_joins = """
            FROM results r
            LEFT JOIN cup_game_details c ON r.game_date = c.game_date
            LEFT JOIN manager_reigns mr ON r.game_date >= mr.mgr_date_from
                AND (r.game_date <= mr.mgr_date_to OR mr.mgr_date_to IS NULL)
            LEFT JOIN managers m ON mr.manager_id = m.manager_id
            LEFT JOIN seasons s ON r.season = s.season
        """

        if self.params.stat_type == StatType.PLAYER:
            base_joins += """
                LEFT JOIN player_apps pa ON r.game_date = pa.game_date
                LEFT JOIN players p ON pa.player_id = p.player_id
            """

        return base_joins

    def build_where_clause(self) -> str:
        """Common WHERE conditions across query types"""
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

        # Type-specific conditions
        if self.params.stat_type == StatType.MANAGER and not self.params.inc_caretakers:
            conditions.append('mr.mgr_role != "Caretaker"')
        elif self.params.stat_type == StatType.PLAYER:
            if not self.params.inc_sub_apps:
                conditions.append("pa.role = 'starter'")

        return 'WHERE ' + ' AND '.join(conditions)

    def get_group_field(self) -> str:
        """Get the appropriate grouping field based on stat type"""
        return {
            StatType.OPPOSITION: 'r.opposition',
            StatType.MANAGER: 'm.manager_name',
            StatType.PLAYER: 'p.player_name'
        }[self.params.stat_type]

class StatsQueryBuilder(BaseQueryBuilder):
    """Builder for aggregated statistics queries"""
    
    BASE_CASE_CONDITIONS = """
        CASE WHEN
            ({pens_draw} = 0 AND ((COALESCE(c.is_multi_leg, 0) = 0 AND r.outcome = 'D' AND c.pens_outcome = '{outcome}') OR r.outcome = '{match_outcome}'))
        OR 
            ({pens_draw} = 1 AND r.outcome = '{match_outcome}')
        THEN 1 END
    """

    DRAW_CONDITION = """
        CASE WHEN
            ({pens_draw} = 0 AND r.outcome = 'D' AND (COALESCE(c.is_pen_shootout, 0) = 0 OR (COALESCE(c.is_pen_shootout, 0) = 1) AND COALESCE(c.is_multi_leg, 0) = 1))
        OR 
            ({pens_draw} = 1 AND r.outcome = 'D')
        THEN 1 END
    """

    def build_select(self) -> str:
        """Build aggregated statistics SELECT clause"""
        group_field = self.get_group_field()
        
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

    def build_group_by(self) -> str:
        """Build GROUP BY clause for aggregated statistics"""
        group_field = self.get_group_field()
        return f"""
            GROUP BY {group_field}
            HAVING COUNT(*) >= ?
            ORDER BY P DESC
        """

    def build_query(self) -> Tuple[str, List]:
        """Build complete aggregated statistics query"""
        # Add parameters for the CASE statements
        case_params = [self.params.pens_as_draw] * 8
        self.query_params = case_params.copy()
        
        query = f"""
            {self.build_select()}
            {self.build_base_joins()}
            {self.build_where_clause()}
            {self.build_group_by()}
        """
        
        self.query_params.append(self.params.min_games)
        return query, self.query_params

class StreakQueryBuilder(BaseQueryBuilder):
    """Builder for streak analysis queries"""

    def build_select(self) -> str:
        """Build raw game data SELECT clause for streak analysis"""
        select_field = self.get_group_field()
        
        return f"""
            SELECT 
                {select_field},
                r.game_date,
                r.outcome,
                r.goals_for,
                r.goals_against,
                c.is_pen_shootout,
                c.pens_outcome,
                c.is_multi_leg
        """

    def build_joins(self) -> str:
        """Build JOINs including player-specific joins if needed"""
        joins = self.build_base_joins()
        
        if self.params.stat_type == StatType.PLAYER:
            joins += """
                LEFT JOIN player_apps pa ON r.game_date = pa.game_date
                LEFT JOIN players p ON pa.player_id = p.player_id
            """
            
        return joins

    def build_order_by(self) -> str:
        """Build ORDER BY clause for streak analysis"""
        group_field = self.get_group_field()
        return f"ORDER BY {group_field}, r.game_date"

    def build_query(self) -> Tuple[str, List]:
        """Build complete streak analysis query"""
        query = f"""
            {self.build_select()}
            {self.build_joins()}
            {self.build_where_clause()}
            {self.build_order_by()}
        """
        
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
        # *[Div(f"{k}: {v}") for k, v in data.items()],
        # Div(f"League tiers: {filter_league_tiers(min_season, max_season)}"),
        # Div(f"Play-offs: {filter_play_offs(min_season, max_season)}"),
        # Div(f"Competitions: {filter_generic_comps(min_season, max_season)}"),
        # Div(f"Venues: {filter_venues(min_season, max_season)}"),
        Div(query_h2h(min_season, max_season, league_tiers, inc_play_offs, generic_comps, pens_as_draws, data['venues'], min_games))
    )


def prepare_streaks_df(df: pd.DataFrame, pens_as_draw: bool = True) -> pd.DataFrame:
    """Prepare DataFrame with streak indicators"""
    
    def get_outcome(row):
        if pens_as_draw:
            return row['outcome']
        else:
            if (row['outcome'] == 'D' and 
                row['is_pen_shootout'] == 1 and 
                row['is_multi_leg'] == 0):
                return row['pens_outcome']
            return row['outcome']
    
    df['adjusted_outcome'] = df.apply(get_outcome, axis=1)
    
    df['is_win'] = df['adjusted_outcome'] == 'W'
    df['is_unbeaten'] = df['adjusted_outcome'] != 'L'
    df['is_clean_sheet'] = df['goals_against'] == 0
    df['is_draw'] = df['adjusted_outcome'] == 'D'
    df['is_winless'] = df['adjusted_outcome'] != 'W'
    df['is_loss'] = df['adjusted_outcome'] == 'L'
    df['is_win_to_nil'] = (df['adjusted_outcome'] == 'W') & (df['goals_against'] == 0)
    df['is_loss_to_nil'] = (df['adjusted_outcome'] == 'L') & (df['goals_for'] == 0)
    
    return df

def get_streak_lengths(group: pd.Series) -> pd.Series:
    """Calculate streak lengths for a group"""
    streak_groups = (group != group.shift()).cumsum()
    return group.groupby(streak_groups).sum()

def calc_streaks(df: pd.DataFrame, focus: str, condition: str) -> pd.Series:
    """Calculate maximum streak length for a condition"""
    return df.groupby(focus)[condition].apply(
        lambda x: get_streak_lengths(x).max()
    )

def get_streaks_df(df: pd.DataFrame, focus: str, params: StatsQueryParams) -> pd.DataFrame:
    """Generate DataFrame with streak statistics"""
    df = prepare_streaks_df(df, params.pens_as_draw)
    
    index_name = {
        'manager_name': 'Manager',
        'player_name': 'Player',
        'opposition': 'Opposition',
        'season': 'Season'
    }[focus]
    
    return pd.DataFrame({
        'Wins': calc_streaks(df, focus, 'is_win'),
        'Unbeaten': calc_streaks(df, focus, 'is_unbeaten'),
        'Clean Sheets': calc_streaks(df, focus, 'is_clean_sheet'),
        'Wins to nil': calc_streaks(df, focus, 'is_win_to_nil'),
        'Draws': calc_streaks(df, focus, 'is_draw'),
        'Winless': calc_streaks(df, focus, 'is_winless'),
        'Defeats': calc_streaks(df, focus, 'is_loss'),
        'Losses to nil': calc_streaks(df, focus, 'is_loss_to_nil')
    }).reset_index().rename(columns={focus: index_name})

def get_streaks_table(params: StatsQueryParams) -> Table:
    """Generate streak statistics table based on provided parameters"""
    # Build and execute query
    builder = StreakQueryBuilder(params)
    query, query_params = builder.build_query()
    
    # Convert to DataFrame
    df = pd.read_sql(query, db.conn, params=query_params)
    
    # Get focus field based on stat type
    focus = {
        StatType.OPPOSITION: 'opposition',
        StatType.MANAGER: 'manager_name',
        StatType.PLAYER: 'player_name'
    }[params.stat_type]
    
    # Calculate streaks
    streaks_df = get_streaks_df(df, focus, params)
    
    # Filter by minimum games if specified
    if params.min_games > 0:
        games_per_entity = df.groupby(focus).size()
        valid_entities = games_per_entity[games_per_entity >= params.min_games].index
        streaks_df = streaks_df[streaks_df[streaks_df.columns[0]].isin(valid_entities)]
    
    # Convert to FastHTML Table
    return Table(
        Thead(
            Tr(*[Th(col) for col in streaks_df.columns])
        ),
        Tbody(
            *[Tr(*[Td(val) for val in row]) for row in streaks_df.values]
        )
    )

@app.post("/streaks-update")
def process_streaks_inputs(data: dict):
    """Process form inputs and return streak analysis"""
    min_season = int(data['min_season'])
    max_season = int(data['max_season'])
    
    league_tiers = data.get('league_tiers', [])
    inc_play_offs = 'inc_play_offs' in data
    generic_comps = data.get('generic_comps', [])
    pens_as_draw = 'pens_as_draw' in data
    venues = data.get('venues', [])
    min_games = int(data.get('min_games', 0))
    
    # Create stats parameters
    params = StatsQueryParams(
        min_season=min_season,
        max_season=max_season,
        league_tiers=league_tiers,
        inc_play_offs=inc_play_offs,
        generic_comps=generic_comps,
        pens_as_draw=pens_as_draw,
        venues=venues,
        min_games=min_games,
        stat_type=StatType.OPPOSITION  # Can be parameterized based on UI selection
    )
    
    return Div(
        get_streaks_table(params)
    )

@app.post("/h2h-records")
def return_h2h_records(data: dict):
    h2h_tab = process_h2h_inputs(data)
    streaks_tab = process_streaks_inputs(data)

    return Div(
        Card(
            H1('Head-to-Head Records'),
            h2h_tab
        ),
        Card(
            H1('Streak Analysis'),
            streaks_tab
        )
    )


@app.get("/")
def index():
    return Grid(
        Form(
            Strong('Season range'),
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
            id="streak-options",
            hx_trigger="input",
            hx_post="/h2h-records",
            hx_target="#h2h-output",
            hx_swap="innerHTML"
        ),
        Div(id="h2h-output")
    )

serve()