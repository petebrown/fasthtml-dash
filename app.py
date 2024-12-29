import pandas as pd
from trfc_data import *
from fasthtml.common import *
import json

def df_to_json(df):
    return json.dumps({
        'columns': [{'header': col, 'accessorKey': col} for col in df.columns],
        'data': df.to_dict(orient='records')
    })

def table_to_datatable(table, table_id, page_length=25):
    return table, Script(f"""
        $(document).ready(function() {{
            $('#{table_id}').DataTable({{
                "order": [],
                "pageLength": {page_length}
            }});
        }});
    """)

def df_to_html(df, table_id=None, extra_classes=None):
    """
    Convert a pandas DataFrame to an HTML table.
    """
    classes = ['table', 'display']  # 'display' class is used by DataTables
    if extra_classes:
        classes.extend(extra_classes)
    class_list = ' '.join(classes)
    
    table_id = table_id or 'dataTable'  # Default ID if none provided
    
    return Table(
        Thead(Tr(*[Th(col) for col in df.columns])),
        Tbody(*[Tr(*[Td(row[col]) for col in df.columns]) for idx, row in df.iterrows()]),
        id=table_id,
        cls=f'{class_list}'
    )

def df_to_html_expanded(df, table_id=None, extra_classes=None):
    """
    Convert a pandas DataFrame to an HTML table with expandable row details using DataTables.
    """
    classes = ['table', 'display']
    if extra_classes:
        classes.extend(extra_classes)
    class_list = ' '.join(classes)
    
    table_id = table_id or 'dataTable'
    
    df['game_date_str'] = df['game_date'].astype(str)
    df['game_date_formatted'] = df['game_date'].dt.strftime('%d/%m/%Y')
    
    columns = [col for col in df.columns if col not in ['game_date_str']]
    
    table = Table(
        Thead(Tr(*[Th(col) for col in columns])),
        Tbody(
            *[Tr(*[Td(row[col]) for col in columns],
                  **{'data-game-date': row['game_date_str']}) 
              for idx, row in df.iterrows()]
        ),
        id=table_id,
        cls=class_list
    )
    
    script = Script(f"""
        (function() {{
            var tableInstance = $('#{table_id}').DataTable({{
                "order": [],
                "pageLength": 25,
                "columnDefs": [
                    {{
                        "targets": 0,
                        "data": null,
                        "defaultContent": '<button class="btn btn-primary btn-sm">+</button>',
                        "orderable": false
                    }}
                ]
            }});
            
            $('#{table_id} tbody').on('click', 'button', function () {{
                var tr = $(this).closest('tr');
                var row = tableInstance.row(tr);
                var gameDate = tr.data('game-date');
         
                if (row.child.isShown()) {{
                    row.child.hide();
                    tr.removeClass('shown');
                    $(this).text('+');
                }} else {{
                    $.ajax({{
                        url: '/match_details/' + gameDate,
                        type: 'POST',
                        success: function(data) {{
                            row.child(data).show();
                            tr.addClass('shown');
                            $(tr).find('button').text('-');
                        }}
                    }});
                }}
            }});
        }})();
    """)
    
    return table, script

def page_length_options(df, page_length=20):
    """ 
    * Currently unused *
    Create HTML options for the page length select element.
    """
    n_records = len(df)
    page_length_options = list(range(page_length, n_records, page_length))
    if n_records % page_length != 0:
        page_length_options.append(n_records)
    return [Option(str(o), value=str(o)) for o in page_length_options]

cdn = 'https://cdn.jsdelivr.net/npm/bootstrap'

app, rt = fast_app(live=True, hdrs=[
    Link(href=cdn+"@5.3.3/dist/css/bootstrap.min.css", rel="stylesheet"),
    Link(href=cdn+"-icons@1.11.3/font/bootstrap-icons.min.css", rel="stylesheet"),
    Link(rel="stylesheet", type="text/css", href="https://cdn.datatables.net/1.10.24/css/jquery.dataTables.css"),
    Script(src=cdn+"@5.3.3/dist/js/bootstrap.bundle.min.js"),
    Script(src="https://code.jquery.com/jquery-3.5.1.js"),
    Script(src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.js")
])

@app.get("/")
def home():
    return Title("Links"), Div(
        H1('Links'),
        A("Link to Seasons page", href="/seasons"),
        Br(),
        A("Link to Results page", href="/results"),
        Br(),
        A("Link to Line Up page", href="/line_ups"),
        Br(),
        A("Link to Head to Head page", href="/h2h"),
        cls='container')

# Function to create season list items
def create_season_list_items(selected_seasons):
    return Ul(
        *[Li(A(f"{season}",
                cls="nav-link",
                href=f"#",
                role="tab",
                id=f"{season}",
                hx_post=f"/season/{season.replace('/', '-')}",
                hx_target="#season_tab",
                hx_swap="innerHTML"),
            cls="nav-item") for season in selected_seasons],
        cls="nav nav-tabs"
    )

@app.get("/seasons")
def seasons():
    initial_season = max(get_season_list())
    initial_df = all_results()[all_results().season == initial_season].fillna('-')
    initial_table, initial_script = df_to_html_expanded(initial_df, 'results_table')

    return Title("Seasons"), Div(
        H1('Seasons'),
        Form(Div(
            *[Div(
                Input(
                    cls="form-check-input",
                    type="checkbox",
                    value=f"{season}",
                    id=f"season_{season.replace('/', '_')}",
                    name="selected_seasons",
                    checked="checked" if season == initial_season else None
                ),
                Label(
                    f"{season}",
                    cls="form-check-label",
                    _for=f"season_{season.replace('/', '_')}"
                ),
                cls="form-check") for season in get_season_list()],
            cls='overflow-auto',
            style='max-height: 290px; width: 150px;'),
            Button('Submit', cls='btn btn-primary'),
            hx_post='/season',
            hx_target='#season_tabs'),
        Div(id='season_tabs', cls='container'),
        initial_table,
        initial_script,
        cls='container')
        
@app.post('/season')
async def season_handler(request):
    selected_seasons = await request.form()
    selected_seasons = [value for key, value in selected_seasons.multi_items() if key == 'selected_seasons']

    if not selected_seasons:
        selected_seasons = [max(get_season_list())]

    df = all_results()[all_results().season.isin(selected_seasons)].fillna('-')
    tab = df_to_html_expanded(df, 'results_table')

    return Div(
        Ul(
            *[Li(A(f"{season}",
                    cls="nav-link",
                    href=f"#",
                    role="tab",
                    id=f"{season}",
                    hx_post=f"/season/{season.replace('/', '-')}",
                    hx_target="#season_tab",
                    hx_swap="innerHTML"),
                cls="nav-item") for season in selected_seasons],
            cls="nav nav-tabs"),
        Div(
            tab,
            id="season_tab"),
        cls="container")

@app.get("/season/{ssn}", methods=["GET", "POST"])
def season_tab(ssn: str):
    ssn = ssn.replace('-', '/')
    df = all_results().query(f"season == '{ssn}'").fillna('-')
    tab = df_to_html_expanded(df, 'results_table')
    return Div(tab, id='results_table', cls='container')

@app.get("/results")
def results():
    df = all_results().fillna('-')
    df = filter_season(df, max(df.season))
    table, script = df_to_html_expanded(df, 'results_table')

    season_options = get_season_options()
    return Title("Results"), Div(
        Form(
            Select(
                *season_options,
                cls='form-select',
                id='season'
            ),
            Button('Submit'),
            hx_post='/season-results',
            hx_target='#results_container'
        ),
        H1('Results'),
        Div(table, id='results_container'),
        script,
        cls='container'
    )

@app.post('/match_details/{game_date}')
def match_details_handler(game_date: str):
    matchday_apps = filter_game(player_apps_df(), game_date)
    league_table = filter_lge_table(league_tabs_df(), game_date)

    matchday_apps = df_to_html(matchday_apps, table_id=f'{game_date}_apps', extra_classes=['table-sm'])
    matchday_apps = table_to_datatable(matchday_apps, f'{game_date}_apps')
    league_table = df_to_html(league_table, table_id=f'{game_date}_table', extra_classes=['table-sm'])
    league_table = table_to_datatable(league_table, f'{game_date}_table')

    return Div(
        Div(
            Div(matchday_apps, cls='col-sm-6'),
            Div(league_table, cls='col-sm-6'),
            cls='row'
        ),
        cls='container-fluid'
    )

@app.post('/season-results')
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

from fasthtml.common import *
import pandas as pd

def df_to_html(df, table_id=None, extra_classes=None):
    """
    Convert a pandas DataFrame to an HTML table with sortable columns using DataTables.
    """
    classes = ['table', 'display']  # 'display' class is used by DataTables
    if extra_classes:
        classes.extend(extra_classes)
    class_list = ' '.join(classes)
    
    table_id = table_id or 'dataTable'  # Default ID if none provided
    
    return Table(
        Thead(Tr(*[Th(col) for col in df.columns])),
        Tbody(*[Tr(*[Td(row[col]) for col in df.columns]) for idx, row in df.iterrows()]),
        id=table_id,
        cls=f'{class_list}'
    )

@app.get("/h2h")
def h2h():
    df = h2h_all(all_results()).fillna('-')
    tab = df_to_html(df, 'h2h_table', extra_classes=['table-striped', 'table-bordered'])
    page_lengths = page_length_options(h2h_all(all_results()))
    
    return Title("Head to Head Overview"), Container(
        H1('Head to Head Overview'),
        Form(
            Select(
                *page_lengths,
                cls='form-select',
                id='page_length'
            ),
            Button('Submit'),
            hx_post='/page_length',
            hx_target='#table-container'
        ),
        Div(
            tab,
            id='table-container'
        ),
        Script("""
            $(document).ready(function() {
                $('#h2h_table').DataTable({
                    "order": [],
                    "pageLength": 25,
                    "lengthChange": false,
                    "searching": false,
                    "info": false,
                    "paging": false
                });
            });
        """)
    )

@app.post('/page_length')
async def page_length_handler(request):
    page_length = await request.form()
    page_length = page_length.get('page_length')
    df = h2h_all(all_results())[:int(page_length)].fillna('-')

    tab = df_to_html(df, 'h2h_table', extra_classes=['table-striped', 'table-bordered'])
    
    return Div(
        tab,
        Script("""
            $(document).ready(function() {
                $('#h2h_table').DataTable({
                    "order": [],
                    "pageLength": 25,
                    "lengthChange": false,
                    "searching": false,
                    "info": false,
                    "paging": false,
                    "destroy": true  // This allows re-initialization
                });
            });
        """),
        id='table-container'
    )

@rt("/r-table")
def get():
    df = filter_season(all_results(), max(all_results().season))
    df['game_date'] = df['game_date'].dt.strftime('%d/%m/%Y')
    table_data = df_to_json(df)
    
    return Titled("TanStack Table Example",
        Div(id="table-container"),
        Script(f"""
            import {{ createTable }} from 'https://cdn.jsdelivr.net/npm/@tanstack/table-core@latest/+esm';

            document.addEventListener('DOMContentLoaded', function() {{
                const tableData = {table_data};
                
                const columns = tableData.columns.map(col => ({{
                    accessorKey: col.accessorKey,
                    header: col.header
                }}));

                const table = createTable({{
                    data: tableData.data,
                    columns: columns,
                }});

                function renderTable() {{
                    const container = document.getElementById('table-container');
                    container.innerHTML = '';

                    const tableElement = document.createElement('table');
                    tableElement.className = 'table table-striped';

                    // Render header
                    const thead = tableElement.createTHead();
                    const headerRow = thead.insertRow();
                    columns.forEach(column => {{
                        const th = document.createElement('th');
                        th.textContent = column.header;
                        headerRow.appendChild(th);
                    }});

                    // Render rows
                    const tbody = tableElement.createTBody();
                    tableData.data.forEach(rowData => {{
                        const tr = tbody.insertRow();
                        columns.forEach(column => {{
                            const td = tr.insertCell();
                            td.textContent = rowData[column.accessorKey];
                        }});
                    }});

                    container.appendChild(tableElement);
                }}

                renderTable();
            }});
        """, type="module")
    )

serve()