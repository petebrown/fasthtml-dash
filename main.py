from re import search
from fasthtml.common import *
from dataclasses import dataclass, field
from typing import Optional, List
import math

db = database('trfc.db')

@dataclass
class Head2HeadAll:
    min_season: int
    max_season: int
    league_tiers: list[str] = field(default_factory=list)
    include_playoffs: bool = field(default=False)
    cup_competitions: list[str] = field(default_factory=list)
    pens_as_draw: bool = field(default=False)
    venues: list[str] = field(default_factory=list)
    min_meetings: int = field(default=10)
    search_terms: str = field(default='')
    tab_recs_per_page: int = field(default=10)
    tab_page_no: int = field(default=1)
    tab_sort_col: str = field(default='P')
    tab_sort_desc: bool = field(default=True)

    def __post_init__(self):
        if self.min_season is None:
            self.min_season = db.q("SELECT MIN(season) as season FROM seasons")
        if self.max_season is None:
            self.max_season = db.q("SELECT MAX(season) as season FROM seasons")
        if self.league_tiers is None:
            self.league_tiers = []
        if self.cup_competitions is None:
            self.cup_competitions = []
        if self.include_playoffs is None:
            self.include_playoffs = True
        if self.pens_as_draw is None:
            self.pens_as_draw = True

app, rt = fast_app(
    hdrs=(Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/flexboxgrid/6.3.1/flexboxgrid.min.css", type="text/css"),)
)

def get_unique(table, col, where='1=1'):
    return [x[f'{col}'] for x in db.q(f"SELECT DISTINCT {table}.{col} FROM {table} WHERE {where} ORDER BY {col}")]

def input_number(title: str, id:str, min:int, max:int, value:int): return Label(
    f'{title}',
    Input(
        type='number',
        id=id,
        min=min,
        max=max,
        value=value
    )
)

def input_checkboxes(items: list, name: str, val_length: int|None = None):
    return Fieldset(
        *[Label(
            Input(
                type='checkbox',
                name=name,
                value=i[:val_length],
                checked=True
            ), i) for i in items
        ]
    )

def input_switch(label: str, id:str, checked:bool): return Fieldset(
    Label(
        Input(
            type='checkbox',
            role='switch',
            id=id,
            checked=checked
        ),
        f'{label}',
    )
)

def input_dropdown(name: str, items: list, id: str, selected: str, **hx_args): return Select(
    *[Option(i, value=i, selected=True if selected==i else False) for i in items],
    name=name, id=id, **hx_args)

league_tiers = [
    '2: Championship',
    '3: League One',
    '4: League Two',
    '5: National League',
]

cup_competitions = get_unique('results', 'generic_comp', 'game_type="Cup"')

venues = ['Home', 'Away', 'Neutral']

@rt('/')
def get():
    return Div(
        Div(
            Div(Form(
                H2('Select Seasons'),
                Grid(
                    input_number('Minimum', 'min_season', 1921, 2024, 1921),
                    input_number('Maximum', 'max_season', 1921, 2024, 2024)
                ),
                Hr(),
                H2('Leagues'),
                input_checkboxes(league_tiers, 'league_tiers', 1),
                input_switch('Include Playoffs', 'include_playoffs', True),
                Hr(),
                H2('Cup Competitions'),
                input_checkboxes(cup_competitions, 'cup_competitions'),
                input_switch('Treat one-off cup games decided by penalty shoot-out as draws', 'pens_as_draw', True),
                Hr(),
                H2('Venues'),
                input_checkboxes(venues, 'venues', 1),
                Hr(),
                input_number('Minimum Meetings', 'min_meetings', 1, 65, 10),
                id='inputs_h2h_all',
                hx_post='/head2head_all',
                hx_include='#tab_recs_per_page, #tab_page_no',
                hx_target='#head2head_all',
                hx_trigger='change'
            ), cls='col-xs-12 col-sm-4 col-md-3 col-lg-2'),
            Div(
                Div(
                    Input(
                        type='text',
                        name='search_terms',
                        placeholder='Search',
                        hx_post='/head2head_all',
                        hx_target='#head2head_all',
                        hx_include='#inputs_h2h_all, #tab_recs_per_page, #tab_page_no, #table_header',
                        hx_trigger='keyup changed delay:500ms'
                ),
                html_h2h_all(
                    sql_h2h_all(Head2HeadAll(min_season=1921, max_season=2024, league_tiers=['2','3','4','5'], cup_competitions=cup_competitions, pens_as_draw=True, venues=['H','A','N'], min_meetings=10)
                )[0]),
                input_dropdown(
                    name='tab_recs_per_page', 
                    items=[10, 25, 50, 100], 
                    id='tab_recs_per_page', 
                    selected=10, 
                    hx_post='/head2head_all', 
                    hx_target='#head2head_all',
                    hx_include='#inputs_h2h_all, #tab_page_no, #table_header',  
                    hx_trigger='change'
                ), 
                input_dropdown(
                    name='tab_page_no', 
                    items=[i for i in range(1, 11)],
                    id='tab_page_no', 
                    selected=1, 
                    hx_post='/head2head_all', 
                    hx_target='#head2head_all',
                    hx_include='#inputs_h2h_all, #tab_recs_per_page, #table_header',  
                    hx_trigger='change'
                ),
                id='head2head_all',
            ), cls='col-xs-12 col-sm-8 col-md-9 col-lg-10'),
        cls='row'),
    cls='container-fluid')

def sql_h2h_all(inputs: Head2HeadAll):
    limit = f'{inputs.tab_recs_per_page}'
    offset = f', {(inputs.tab_page_no-1) * inputs.tab_recs_per_page}' if inputs.tab_page_no > 1 else ''
    search_terms = f'AND LOWER(r.opposition) LIKE "%{inputs.search_terms.lower()}%"' if inputs.search_terms else ''
    base_query = f"""
        SELECT
            r.opposition,
            COUNT(*) AS P,
            COUNT(
                CASE
                    WHEN (
                        {int(inputs.pens_as_draw)} = 0
                        AND (
                            (
                                r.pens_outcome IS NULL
                                AND r.outcome = 'W'
                            )
                            OR (
                                r.pens_outcome IS NOT NULL
                                AND r.pens_outcome = 'W'
                            )
                        )
                    )
                    OR (
                        {int(inputs.pens_as_draw)} = 1
                        AND r.outcome = 'W'
                    ) THEN 1
                END
            ) AS W,
            COUNT(
                CASE
                    WHEN (
                        {int(inputs.pens_as_draw)} = 0
                        AND (
                            r.pens_outcome IS NULL
                            AND r.outcome = 'D'
                        )
                    )
                    OR (
                        {int(inputs.pens_as_draw)} = 1
                        AND r.outcome = 'D'
                    ) THEN 1
                END
            ) AS D,
            COUNT(
                CASE
                    WHEN (
                        {int(inputs.pens_as_draw)} = 0
                        AND (
                            (
                                r.pens_outcome IS NULL
                                AND r.outcome = 'L'
                            )
                            OR (
                                r.pens_outcome IS NOT NULL
                                AND r.pens_outcome = 'L'
                            )
                        )
                    )
                    OR (
                        {int(inputs.pens_as_draw)} = 1
                        AND r.outcome = 'L'
                    ) THEN 1
                END
            ) AS L,
            SUM(r.goals_for) AS GF,
            SUM(r.goals_against) AS GA,
            SUM(r.goals_for) - SUM(r.goals_against) AS GD,
            ROUND(
                CAST(
                    COUNT(
                        CASE
                            WHEN (
                                {int(inputs.pens_as_draw)} = 0
                                AND (
                                    r.pens_outcome IS NOT NULL
                                    AND r.pens_outcome = 'W'
                                )
                                OR (
                                    r.pens_outcome IS NULL
                                    AND r.outcome = 'W'
                                )
                            )
                            OR (
                                {int(inputs.pens_as_draw)} = 1
                                AND r.outcome = 'W'
                            ) THEN 1
                        END
                    ) AS FLOAT
                ) / COUNT(*) * 100,
                1
            ) AS win_pc
        FROM
            full_results r
        WHERE
            r.ssn_start >= {inputs.min_season} AND r.ssn_start <= {inputs.max_season} 
            AND (r.generic_comp IN ({','.join([f'"{x}"' for x in inputs.cup_competitions])}) OR (r.league_tier IN ({','.join([x for x in inputs.league_tiers])})))
            AND r.is_playoff IN ({int(inputs.include_playoffs)}, 0) OR r.is_playoff IS NULL
            AND r.venue IN ({','.join([f"'{x}'" for x in inputs.venues])}) 
            {search_terms}
        GROUP BY
            r.opposition
        HAVING
            COUNT(*) >= {inputs.min_meetings}
        ORDER BY
            {inputs.tab_sort_col} {'ASC' if inputs.tab_sort_desc else 'DESC'},
            r.opposition
        LIMIT {limit}{offset}
    """
    n_records = len(db.q(base_query.replace(f'LIMIT {limit}{offset}', '')))
    records = db.q(base_query)

    return records, n_records

def html_h2h_all(data):
    return Table(
        Thead(
            Tr(
                Th('Opposition'),
                Th('P', hx_post='/head2head_all', hx_vals={'tab_sort_col': 'P'}, hx_target='#head2head_all', hx_trigger='click', hx_include='#inputs_h2h_all, #tab_recs_per_page, #tab_page_no'),
                Th('W'),
                Th('D'),
                Th('L'),
                Th('GF'),
                Th('GA'),
                Th('GD'),
                Th('%'), 
            style='cursor: pointer;')
            ),
        Tbody(
            *[Tr(
                Td(d['opposition']),
                Td(d['P']),
                Td(d['W']),
                Td(d['D']),
                Td(d['L']),
                Td(d['GF']),
                Td(d['GA']),
                Td(d['GD']),
                Td(d['win_pc'])
            ) for d in data]
        )
    )

sort_col = {}
print(f'global sort_col is {sort_col}')

@rt('/head2head_all')
def post(inputs: Head2HeadAll):
    global sort_cols
    sort_col = inputs.tab_sort_col
    print(f'sort_col is {sort_col}')

    sql_resp = sql_h2h_all(inputs)
    
    records = sql_resp[0]
    n_recs = sql_resp[1]

    page = inputs.tab_page_no
    recs_per_page = inputs.tab_recs_per_page
    return (
        Div(
            Input(
                type='text',
                name='search_terms',
                placeholder='Search',
                value=inputs.search_terms,
                hx_post='/head2head_all',
                hx_target='#head2head_all',
                hx_include='#inputs_h2h_all, #tab_recs_per_page, #tab_page_no, #table_header',
                hx_trigger='keyup changed delay:500ms'
            )
        ),
        html_h2h_all(records),
        Grid(
            Div(
                input_dropdown(
                    name='tab_recs_per_page', 
                    items=[10, 25, 50, 100], 
                    id='tab_recs_per_page', 
                    selected=inputs.tab_recs_per_page, 
                    hx_post='/head2head_all', 
                    hx_target='#head2head_all',
                    hx_include='#inputs_h2h_all, #tab_page_no, #table_header',  
                    hx_trigger='change',
                    style='width: auto;'
                ),
                Span("records per page", style='padding-left: 5px; margin: auto;')
            ),
            Div(
                Span(f'Displaying records {(page-1) * recs_per_page + 1}-{min(page * recs_per_page, n_recs)} of {n_recs}', 
                style='text-align: center; display:contents;')
            ),
            Div(
                Span("Page "),
                input_dropdown(
                    name='tab_page_no', 
                    items=[i for i in range(1, math.ceil(n_recs/inputs.tab_recs_per_page +1))],
                    id='tab_page_no', 
                    selected=inputs.tab_page_no, 
                    hx_post='/head2head_all', 
                    hx_target='#head2head_all',
                    hx_include='#inputs_h2h_all, #tab_recs_per_page, #table_header',  
                    hx_trigger='change',
                    style='width: auto'
                ),
                Span(f" of {math.ceil(n_recs/inputs.tab_recs_per_page +1)}"),
            style='text-align: right')
        )        
    )

serve()