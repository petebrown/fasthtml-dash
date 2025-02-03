from fasthtml.common import *
from dataclasses import dataclass, field
from typing import List, Literal

@dataclass
class AllRecords:
    min_season: int
    max_season: int
    league_tiers: List[int] = field(default_factory=list)
    inc_playoffs: bool = field(default=True)
    cup_competitions: List[str] = field(default_factory=list)
    pens_as_draw: bool = field(default=True)
    venues: List[str] = field(default_factory=list)



db = database('trfc.db')

app, rt = fast_app()

league_tiers = {
    2: '2: Championship',
    3: '3: League One',
    4: '4: League Two',
    5: '5: National League',
}

venues = {
    'H': 'Home',
    'A': 'Away',
    'N': 'Neutral'
}

def checkboxes(field: str, items: dict):
    checkboxes = [(CheckboxX(
        name=field,
        label=v,
        value=k,
        checked=True
    )) for k, v in items.items()]

    return Div(*checkboxes)

ssns = [1921, 2024]

input_range = (Div(
    '1921', 
    Input(
        type="range",
        name=f"min_season",
        value=f"1921",
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
        value=f"2024",
        placeholder=f"Max.",
        min=1921,
        max=2024,
        step=1,
        id=f"id",
        hx_on_input=f"document.getElementById('max_season_display').innerText = this.value;"
    ),
    Span(max(ssns), id="max_season_display")
))

@rt('/')
def get():
    return (
        Form(
            input_range,
            checkboxes(field='league_tiers', items=league_tiers),
            checkboxes(field='venues', items=venues),
            hx_post='/form',
            hx_target='#result',
            hx_trigger='change'
        ),
        Div(id='result')
    )

@rt('/form')
def post(form_data: AllRecords):
    print(form_data)
    return form_data

serve()