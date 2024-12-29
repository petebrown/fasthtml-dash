from fasthtml.common import *

db = database("trfc.db")

app, rt = fast_app(
    pico=False,
    hdrs = (
        Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/tom-select@2.4.1/dist/css/tom-select.css"),
        Script(src="https://cdn.jsdelivr.net/npm/tom-select@2.4.1/dist/js/tom-select.complete.min.js")
    )
)

def tom_select():
    return Script('''
        new TomSelect("#select-season", 
            {
        });
    ''')

def season_list():
    return [s['season'] for s in db.query("SELECT season FROM seasons ORDER BY season DESC")]

def all_comps():
    return [c['generic_comp'] for c in db.query("SELECT DISTINCT(generic_comp) FROM results ORDER BY competition")]

def filter_generic_comps(seasons):
    placeholders = ','.join(['?' for _ in seasons])
    return [r['generic_comp'] for r in db.query(f"SELECT DISTINCT(generic_comp) FROM results r WHERE r.game_type = 'Cup' AND r.season IN ({placeholders}) ORDER BY generic_comp", seasons)]

@app.post("/filter-comps")
async def comp_selector(request):
    selected_seasons = await request.form()
    selected_seasons = [value for key, value in selected_seasons.multi_items()]
    return Fieldset(
        Legend('Competitions'),
            Div(
                *[Input(comp, type='checkbox', value=comp) for comp in filter_generic_comps(selected_seasons)]
            ),
        name='generic_comps')

@app.get("/")
def index():
    return Grid(
        Form(
            Select(
                *[Option(str(season), value=str(season), selected=True if season in season_list()[:2] else False) for season in season_list()],
                name='season',
                multiple=True,
                placeholder="Select season...",
                autocomplete="off",
                hx_post='/filter-comps',
                hx_target='#comp_options',
                hx_trigger='change',
                id='select-season'
            ),
            Div(id='comp_options'),
            hx_include='form',
            hx_post='/seasons',
            hx_target='#chosen_seasons',
            hx_trigger='change'
        ),
      Div(id='chosen_seasons')  
    ), tom_select()

@app.post("/seasons")
async def season_results(request):
    selected_seasons = await request.form()
    print(selected_seasons)
    selected_seasons = [value for key, value in selected_seasons.multi_items()]
    selected_seasons = [Div(str(season)) for season in selected_seasons]
    return Div(
        *selected_seasons
    )

serve()