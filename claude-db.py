from fasthtml.common import *
from dataclasses import dataclass
from datetime import datetime
from math import ceil
import json
import pandas as pd


# Connect to your existing database
db = database('trfc.db')

# Create your FastHTML app and get route decorator
app, rt = fast_app(
    hdrs = (
        Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.15.2/css/selectize.default.min.css"),
        Script(src="https://code.jquery.com/jquery-3.6.0.min.js"),
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.15.2/js/selectize.min.js"),
        Script(src='assets/app.js')
    )
)

def get_players(search_term=None, sort_by='display_name', sort_dir='asc'):
    query = '''SELECT player_id, display_name, player_name, surname, forename,
               COALESCE(player_dob, dob_display) as display_dob,
               comp_rec_pos, soccerbase_pos, tm_pos_1, tm_pos_2, tm_pos_3, position 
               FROM players'''
    params = []
    
    if search_term:
        query += ''' 
            WHERE display_name LIKE ? 
            OR position LIKE ? 
            OR player_name LIKE ?
        '''
        search_param = f'%{search_term}%'
        params = [search_param, search_param, search_param]
    
    query += f' ORDER BY {sort_by} {sort_dir.upper()}'
    
    cursor = db.conn.execute(query, params)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, player)) for player in cursor.fetchall()]

def create_filter_form(player_id, filter_values, date_from, date_to, opponent, competition, role, per_page=20):
    return Form(
        Div(
            Group(
                Label("Date Range"),
                Input(
                    type="date",
                    name="date_from",
                    value=date_from or '',
                    min=filter_values['min_date'],
                    max=filter_values['max_date'],
                    hx_get=f"/player/{player_id}/appearances",
                    hx_trigger="change",
                    hx_target="#appearances-content",
                    hx_include="form"
                ),
                Input(
                    type="date",
                    name="date_to",
                    value=date_to or '',
                    min=filter_values['min_date'],
                    max=filter_values['max_date'],
                    hx_get=f"/player/{player_id}/appearances",
                    hx_trigger="change",
                    hx_target="#appearances-content",
                    hx_include="form"
                )
            ),
            Group(
                Label("Opponent"),
                Select(
                    Option("All", value=""),
                    *[Option(opp, selected=opponent==opp) for opp in filter_values['opponents'].split(',')],
                    name="opponent",
                    hx_get=f"/player/{player_id}/appearances",
                    hx_trigger="change",
                    hx_target="#appearances-content",
                    hx_include="form"
                )
            ),
            Group(
                Label("Competition"),
                Select(
                    Option("All", value=""),
                    *[Option(comp, selected=competition==comp) for comp in filter_values['competitions'].split(',')],
                    name="competition",
                    hx_get=f"/player/{player_id}/appearances",
                    hx_trigger="change",
                    hx_target="#appearances-content",
                    hx_include="form"
                )
            ),
            Group(
                Label("Role"),
                Select(
                    Option("All", value=""),
                    *[Option(r.capitalize(), value=r, selected=role==r) for r in filter_values['roles'].split(',')],
                    name="role",
                    hx_get=f"/player/{player_id}/appearances",
                    hx_trigger="change",
                    hx_target="#appearances-content",
                    hx_include="form"
                )
            ),
            Group(
                Label("Page Size"),
                Select(
                    Option("20 per page", value="20", selected=per_page==20),
                    Option("50 per page", value="50", selected=per_page==50),
                    Option("100 per page", value="100", selected=per_page==100),
                    name="per_page",
                    hx_get=f"/player/{player_id}/appearances",
                    hx_trigger="change",
                    hx_target="#appearances-content",
                    hx_include="form"
                )
            ),
            cols="1fr 1fr 1fr 1fr 1fr"
        ),
        id="filter-form",
        cls="filter-form"
    )

def player_grid_html(players):
    return [  # Return just the cards without an outer Grid
        A(
            Card(
                H3(p['display_name']),
                P(f"Position: {p['position']}"),
                P(f"Date of Birth: {p['display_dob']}"),
                cls="card"
            ),
            href=f"/player/{p['player_id']}",
            cls="card-link"
        ) for p in players
    ] if players else [P("No players found")]

@rt('/')
def get(request, q: str = '', sort: str = 'display_name', direction: str = 'asc'):
    players = get_players(search_term=q, sort_by=sort, sort_dir=direction)
    
    # Only return the grid if this is an HTMX request
    if 'HX-Request' in request.headers:
        return Grid(*player_grid_html(players), id="player-grid", cls="results-grid")
    
    # Otherwise return the full page
    controls = Card(
        Form(
            Group(
                Input(id="search", name="q", placeholder="Search players...", 
                      value=q, hx_get="/", hx_trigger="keyup changed delay:500ms", 
                      hx_target="#player-grid",
                      hx_swap="outerHTML"),
                Div(
                    Select(
                        Option("Name", value="display_name", selected=sort=="display_name"),
                        Option("Position", value="position", selected=sort=="position"),
                        Option("Date of Birth", value="player_dob", selected=sort=="player_dob"),
                        name="sort",
                        hx_get="/",
                        hx_target="#player-grid",
                        hx_swap="outerHTML",
                        hx_include="#search, #direction"
                    ),
                    Select(
                        Option("Ascending", value="asc", selected=direction=="asc"),
                        Option("Descending", value="desc", selected=direction=="desc"),
                        name="direction",
                        id="direction",
                        hx_get="/",
                        hx_target="#player-grid",
                        hx_swap="outerHTML",
                        hx_include="#search, #sort"
                    ),
                    cls="sort-controls"
                )
            ),
            cls="search-controls"
        )
    )
    
    return Titled("Tranmere Rovers Players",
        Container(
            controls,
            Grid(*player_grid_html(players), id="player-grid", cls="results-grid"),
            Style("""
                .sort-controls {
                    display: flex;
                    gap: 1rem;
                }
                .sort-controls select {
                    flex: 1;
                }
                .search-controls form {
                    display: grid;
                    grid-template-columns: 1fr auto;
                    gap: 1rem;
                    align-items: start;
                }
                .search-controls {
                    margin-bottom: 2rem;
                }
                .search-controls form {
                    display: grid;
                    grid-template-columns: 1fr auto;
                    gap: 1rem;
                }
                .results-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 1.5rem;
                    width: 100%;
                }
                .card {
                    border: 1px solid var(--card-border-color);
                    padding: 1.5rem;
                    margin: 0;
                    transition: transform 0.2s;
                    background: var(--card-background-color);
                    height: 100%;
                }
                .card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                :root {
                    --card-border-color: #ddd;
                    --card-background-color: #fff;
                }
                @media (prefers-color-scheme: dark) {
                    :root {
                        --card-border-color: #444;
                        --card-background-color: #222;
                    }
                }
                .button {
                    display: inline-block;
                    padding: 0.5rem 1rem;
                    background: var(--primary);
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin-top: 1rem;
                }
                .card-link {
                    text-decoration: none;
                    color: inherit;
                    display: block;
                }
                .card-link:hover {
                    text-decoration: none;
                }
                .card-link:hover .card {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
            """)
        )
    )

@rt('/player/{player_id}/summary')
def get(player_id: str, group_by: str = 'overall'):
    # Use your existing summary query here
    summary_cursor = db.conn.execute('''
        WITH grouped_data AS (
            SELECT 
                CASE 
                    WHEN ? = 'season' THEN strftime('%Y', r.game_date)
                    WHEN ? = 'opposition' THEN r.opposition 
                    WHEN ? = 'competition' THEN r.competition
                    WHEN ? = 'manager' THEN m.manager_name
                    ELSE 'All' 
                END as group_by,
                pa.role,
                r.outcome,
                r.goals_for,
                r.goals_against,
                r.generic_comp
            FROM player_apps pa      
            JOIN results r ON r.game_date = pa.game_date
            JOIN manager_reigns mr ON r.game_date BETWEEN mr.mgr_date_from AND COALESCE(mr.mgr_date_to, '9999-12-31')
            JOIN managers m ON m.manager_id = mr.manager_id
            WHERE pa.player_id = ?
        )
        SELECT 
            group_by,
            SUM(CASE WHEN role = 'starter' THEN 1 ELSE 0 END) as starts,
            SUM(CASE WHEN role = 'sub' THEN 1 ELSE 0 END) as subs,
            SUM(CASE WHEN outcome = 'W' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'D' THEN 1 ELSE 0 END) as draws,
            SUM(CASE WHEN outcome = 'L' THEN 1 ELSE 0 END) as losses,
            SUM(goals_for) as goals_for,
            SUM(goals_against) as goals_against,
            ROUND(CAST(
                SUM(CASE 
                    WHEN role = 'starter' 
                    AND generic_comp IN ('Football League', 'Non-League')
                    THEN (CASE 
                            WHEN outcome = 'W' THEN 3 
                            WHEN outcome = 'D' THEN 1 
                            ELSE 0 
                        END)
                    ELSE 0 
                END) AS FLOAT) / 
                NULLIF(SUM(CASE 
                    WHEN role = 'starter' 
                    AND generic_comp IN ('Football League', 'Non-League')
                    THEN 1 
                    ELSE 0 
                END), 0), 2) as points_per_league_start
        FROM grouped_data
        GROUP BY group_by
        ORDER BY group_by ASC
    ''', [group_by, group_by, group_by, group_by, player_id])
    
    summaries = [dict(zip([d[0] for d in summary_cursor.description], row)) 
                for row in summary_cursor.fetchall()]

    # Return just the table body content
    return Tbody(
        *[Tr(
            Td(s['group_by']),
            Td(f"{s['starts']} ({s['subs']})"),
            Td(s['wins']),
            Td(s['draws']),
            Td(s['losses']),
            Td(s['goals_for']),
            Td(s['goals_against']),
            Td(s['points_per_league_start'])
        ) for s in summaries]
    )


@rt('/player/{player_id}/appearances')
def get(request, player_id: str, 
        page: int = 1, 
        per_page: int = 20,
        date_from: str = None,
        date_to: str = None,
        opponent: str = None,
        competition: str = None,
        role: str = None):

    # Convert per_page to int since it comes as string from form
    try:
        per_page = int(per_page)
    except:
        per_page = 20

    # Get filter values for the form
    cursor = db.conn.execute('''
        SELECT 
            MIN(pa.game_date) as min_date,
            MAX(pa.game_date) as max_date,
            GROUP_CONCAT(DISTINCT r.opposition) as opponents,
            GROUP_CONCAT(DISTINCT r.competition) as competitions,
            GROUP_CONCAT(DISTINCT pa.role) as roles
        FROM player_apps pa
        JOIN results r ON r.game_date = pa.game_date
        WHERE pa.player_id = ?
    ''', [player_id])
    columns = [description[0] for description in cursor.description]
    filter_values = dict(zip(columns, cursor.fetchone()))
    
    # Build base query
    base_query = '''
        SELECT 
            pa.game_date,
            r.opposition,
            r.venue,
            r.competition,
            r.score,
            pa.role,
            CAST(pa.shirt_no AS INTEGER) as shirt_no,
            COUNT(*) OVER() as total_count
        FROM player_apps pa
        JOIN results r ON r.game_date = pa.game_date
        WHERE pa.player_id = ?'''
    
    params = [player_id]
    
    # Add filters if they exist
    if date_from and date_from.strip() != '':
        base_query += ' AND pa.game_date >= ?'
        params.append(date_from)
    if date_to and date_to.strip() != '':
        base_query += ' AND pa.game_date <= ?'
        params.append(date_to)
    if opponent and opponent.strip() != '' and opponent != 'All':
        base_query += ' AND r.opposition = ?'
        params.append(opponent)
    if competition and competition.strip() != '' and competition != 'All':
        base_query += ' AND r.competition = ?'
        params.append(competition)
    if role and role.strip() != '' and role != 'All':
        base_query += ' AND pa.role = ?'
        params.append(role)
    
    # Add ordering and pagination
    final_query = base_query + ' ORDER BY pa.game_date DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    # print("Final Query:", final_query)
    # print("Params:", params)
    
    appearances_cursor = db.conn.execute(final_query, params)
    appearances = [dict(zip([d[0] for d in appearances_cursor.description], row)) 
                  for row in appearances_cursor.fetchall()]
    
    total_records = appearances[0]['total_count'] if appearances else 0
    total_pages = ceil(total_records / per_page)

    # Update the return Div to include better pagination controls
    return Div(
        create_filter_form(player_id, filter_values, date_from, date_to, opponent, 
                          competition, role, per_page),
        Table(
            Thead(
                Tr(
                    Th("Date"),
                    Th("Opponent"),
                    Th("Venue"),
                    Th("Competition"),
                    Th("Score"),
                    Th("Role"),
                    Th("Shirt")
                )
            ),
            Tbody(
                *[Tr(
                    Td(A(
                        datetime.strptime(app['game_date'], '%Y-%m-%d').strftime('%d/%m/%Y'),
                        href=f"/game/{app['game_date']}",
                        cls="date-link"
                    )),
                    Td(app['opposition']),
                    Td(app['venue']),
                    Td(app['competition']),
                    Td(app['score']),
                    Td(app['role'].capitalize()),
                    Td(str(app['shirt_no']))
                ) for app in appearances]
            ) if appearances else [Tr(Td("No results found", colspan="7", style="text-align: center"))],
            cls="appearances-table"
        ),
        Div(
            Div(
                Span(f"Showing {(page-1)*per_page + 1}-{min(page*per_page, total_records)} of {total_records} results"),
                cls="pagination-info"
            ),
            Div(
                *([] if page == 1 else [
                    A("← First", 
                      hx_get=f"/player/{player_id}/appearances?page=1&date_from={date_from or ''}&date_to={date_to or ''}&opponent={opponent or ''}&competition={competition or ''}&role={role or ''}&per_page={per_page}",
                      hx_target="#appearances-content",
                      cls="button"
                    ),
                    A("← Previous", 
                      hx_get=f"/player/{player_id}/appearances?page={page-1}&date_from={date_from or ''}&date_to={date_to or ''}&opponent={opponent or ''}&competition={competition or ''}&role={role or ''}&per_page={per_page}",
                      hx_target="#appearances-content",
                      cls="button"
                    )
                ]),
                Span(f"Page {page} of {total_pages}", cls="page-info"),
                *([] if page >= total_pages else [
                    A("Next →", 
                      hx_get=f"/player/{player_id}/appearances?page={page+1}&date_from={date_from or ''}&date_to={date_to or ''}&opponent={opponent or ''}&competition={competition or ''}&role={role or ''}&per_page={per_page}",
                      hx_target="#appearances-content",
                      cls="button"
                    ),
                    A("Last →", 
                      hx_get=f"/player/{player_id}/appearances?page={total_pages}&date_from={date_from or ''}&date_to={date_to or ''}&opponent={opponent or ''}&competition={competition or ''}&role={role or ''}&per_page={per_page}",
                      hx_target="#appearances-content",
                      cls="button"
                    )
                ]),
                cls="pagination-controls"
            ),
            cls="pagination"
        ) if total_pages > 1 else None,
        id="appearances-content"
    )

@rt('/player/{player_id}')
def get(player_id: str, group_by: str = 'overall'):
    # First get the player details and debut info (previous SQL query)
    cursor = db.conn.execute('''
        WITH debut AS (
            SELECT 
                game_date,
                role,
                CAST(shirt_no AS INTEGER) as shirt_no
            FROM player_apps
            WHERE player_id = ?
            ORDER BY game_date ASC
            LIMIT 1
        ),
        debut_manager AS (
            SELECT 
                m.manager_name
            FROM debut d
            JOIN manager_reigns mr ON d.game_date BETWEEN mr.mgr_date_from AND COALESCE(mr.mgr_date_to, '9999-12-31')
            JOIN managers m ON m.manager_id = mr.manager_id
            LIMIT 1
        )
        SELECT 
            p.player_id, 
            p.display_name, 
            p.player_name, 
            p.surname, 
            p.forename,
            COALESCE(p.player_dob, p.dob_display) as display_dob,
            p.comp_rec_pos, 
            p.soccerbase_pos, 
            p.tm_pos_1, 
            p.tm_pos_2, 
            p.tm_pos_3, 
            p.position,
            d.game_date as debut_date,
            d.role as debut_role,
            d.shirt_no as debut_shirt_no,
            dm.manager_name as debut_manager
        FROM players p
        LEFT JOIN debut d ON 1=1
        LEFT JOIN debut_manager dm ON 1=1
        WHERE p.player_id = ?
    ''', [player_id, player_id])
    
    columns = [description[0] for description in cursor.description]
    player = dict(zip(columns, cursor.fetchone()))

    # Now get all appearances
    appearances_cursor = db.conn.execute('''
        SELECT 
            pa.game_date,
            r.opposition,
            r.venue,
            r.competition,
            r.score,
            pa.role,
            CAST(pa.shirt_no AS INTEGER) as shirt_no
        FROM player_apps pa
        JOIN results r ON r.game_date = pa.game_date
        WHERE pa.player_id = ?
        ORDER BY pa.game_date DESC
    ''', [player_id])
    
    appearances = [dict(zip([d[0] for d in appearances_cursor.description], row)) 
                  for row in appearances_cursor.fetchall()]
    
    starts = len([app for app in appearances if app['role'] == 'starter'])
    subs = len([app for app in appearances if app['role'] == 'sub'])

    summary_cursor = db.conn.execute('''
        WITH grouped_data AS (
            SELECT 
                CASE 
                    WHEN ? = 'season' THEN strftime('%Y', r.game_date)
                    WHEN ? = 'opposition' THEN r.opposition 
                    WHEN ? = 'competition' THEN r.competition
                    ELSE 'All' 
                END as group_by,
                pa.role,
                r.outcome,
                r.goals_for,
                r.goals_against,
                r.generic_comp
            FROM player_apps pa
            JOIN results r ON r.game_date = pa.game_date
            WHERE pa.player_id = ?
        )
        SELECT 
            group_by,
            SUM(CASE WHEN role = 'starter' THEN 1 ELSE 0 END) as starts,
            SUM(CASE WHEN role = 'sub' THEN 1 ELSE 0 END) as subs,
            SUM(CASE WHEN outcome = 'W' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'D' THEN 1 ELSE 0 END) as draws,
            SUM(CASE WHEN outcome = 'L' THEN 1 ELSE 0 END) as losses,
            SUM(goals_for) as goals_for,
            SUM(goals_against) as goals_against,
            ROUND(CAST(
                SUM(CASE 
                    WHEN role = 'starter' 
                    AND generic_comp IN ('Football League', 'Non-League')
                    THEN (CASE 
                            WHEN outcome = 'W' THEN 3 
                            WHEN outcome = 'D' THEN 1 
                            ELSE 0 
                        END)
                    ELSE 0 
                END) AS FLOAT) / 
                NULLIF(SUM(CASE 
                    WHEN role = 'starter' 
                    AND generic_comp IN ('Football League', 'Non-League')
                    THEN 1 
                    ELSE 0 
                END), 0), 2) as league_ppg
        FROM grouped_data
        GROUP BY group_by
        ORDER BY group_by ASC
    ''', [group_by, group_by, group_by, player_id])

    summaries = [dict(zip([d[0] for d in summary_cursor.description], row)) for row in summary_cursor.fetchall()]
    
    cursor = db.conn.execute('''
        SELECT 
            MIN(pa.game_date) as min_date,
            MAX(pa.game_date) as max_date,
            GROUP_CONCAT(DISTINCT r.opposition) as opponents,
            GROUP_CONCAT(DISTINCT r.competition) as competitions,
            GROUP_CONCAT(DISTINCT pa.role) as roles
        FROM player_apps pa
        JOIN results r ON r.game_date = pa.game_date
        WHERE pa.player_id = ?
    ''', [player_id])

    columns = [description[0] for description in cursor.description]
    filter_values = dict(zip(columns, cursor.fetchone()))

    appearances_card = None
    if appearances:
        # Create the appearances card with filters
        appearances_card = Card(
            H3(f"Appearances ({starts}+{subs})"),
            Div(
                create_filter_form(player_id, filter_values, None, None, None, None, None, 20),
                Table(
                    Thead(
                        Tr(
                            Th("Date"),
                            Th("Opponent"),
                            Th("Venue"),
                            Th("Competition"),
                            Th("Score"),
                            Th("Role"),
                            Th("Shirt")
                        )
                    ),
                    Tbody(
                        *[Tr(
                            Td(A(
                                datetime.strptime(app['game_date'], '%Y-%m-%d').strftime('%d/%m/%Y'),
                                href=f"/game/{app['game_date']}",
                                cls="date-link"
                            )),
                            Td(app['opposition']),
                            Td(app['venue']),
                            Td(app['competition']),
                            Td(app['score']),
                            Td(app['role'].capitalize()),
                            Td(str(app['shirt_no']))
                        ) for app in appearances[:20]]
                    ),
                    cls="appearances-table"
                ),
                Div(
                    Div(
                        Span(f"Showing 1-{min(20, len(appearances))} of {len(appearances)} results"),
                        cls="pagination-info"
                    ),
                    Div(
                        Span(f"Page 1 of {ceil(len(appearances)/20)}", cls="page-info"),
                        *([] if len(appearances) <= 20 else [
                            A("Next →", 
                            hx_get=f"/player/{player_id}/appearances?page=2&per_page=20",
                            hx_target="#appearances-content",
                            cls="button"
                            ),
                            A("Last →", 
                            hx_get=f"/player/{player_id}/appearances?page={ceil(len(appearances)/20)}&per_page=20",
                            hx_target="#appearances-content",
                            cls="button"
                            )
                        ]),
                        cls="pagination-controls"
                    ),
                    cls="pagination"
                ) if len(appearances) > 20 else None,
                id="appearances-content"
            ),
            cls="appearances-card"
        )
        
    # Rest of the function remains similar, but with updated layout
    def create_field(label, value):
        if value is not None and value != '':
            return P(f"{label}: {value}")
        return None
    
    player_details = [
        H3("Player Details"),
        create_field("Full Name", f"{player['forename']} {player['surname']}"),
        create_field("Position", player['position']),
        create_field("Date of Birth", player['display_dob']),
        create_field("Competition Record Position", player['comp_rec_pos']),
        create_field("Soccerbase Position", player['soccerbase_pos'])
    ]
    player_details = [field for field in player_details if field is not None]
    
    debut_info = None
    if player['debut_date']:
        debut_date = datetime.strptime(player['debut_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
        role = player['debut_role'].capitalize() if player['debut_role'] else 'Unknown'
        shirt_no = int(player['debut_shirt_no']) if player['debut_shirt_no'] is not None else 'Unknown'
        
        debut_info = Card(
            H3("Debut Information"),
            P(f"Date: {debut_date}"),
            P(f"Manager: {player['debut_manager'] or 'Unknown'}"),
            P(f"Role: {role}"),
            P(f"Shirt Number: {shirt_no}"),
            cls="debut-card"
        )

    # Add right after the player details and debut info cards
    summary_controls = Card(
        H3("Appearance Summary"),
        Form(
            Select(
                Option("Overall", value="overall", selected=group_by=="overall"),
                Option("By Season", value="season", selected=group_by=="season"),
                Option("By Opposition", value="opposition", selected=group_by=="opposition"),
                Option("By Competition", value="competition", selected=group_by=="competition"),
                Option("By Manager", value="manager", selected=group_by=="manager"),
                name="group_by",
                hx_get=f"/player/{player_id}/summary",  # New endpoint just for summary
                hx_target="#summary-table",  # Target just the table
                hx_swap="innerHTML"
            ),
            cls="summary-controls"
        ),
        Table(
            Thead(
                Tr(
                    Th("Group"),
                    Th("Starts (Sub)"),
                    Th("W"),
                    Th("D"),
                    Th("L"),
                    Th("GF"),
                    Th("GA"),
                    Th("League Pts")
                )
            ),
            Tbody(
                *[Tr(
                    Td(s['group_by']),
                    Td(f"{s['starts']} ({s['subs']})"),
                    Td(s['wins']),
                    Td(s['draws']),
                    Td(s['losses']),
                    Td(s['goals_for']),
                    Td(s['goals_against']),
                    Td(s['league_ppg'])
                ) for s in summaries]
            ),
            id="summary-table",  # Add ID for HTMX target
            cls="summary-table"
        ),
        cls="summary-card"
    )
    
    return Titled(player['display_name'],
        Container(
            Grid(
                Card(*player_details),
                debut_info if debut_info else None,
                cls="details-grid"
            ),
            summary_controls,
            appearances_card if appearances_card else None,
            Style("""
                .details-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 1.5rem;
                    margin-top: 2rem;
                }
                
                .debut-card {
                    height: fit-content;
                }
                
                .appearances-card {
                    margin-top: 2rem;
                    width: 100%;
                }
                
                .appearances-table {
                    width: 100%;
                    text-align: left;
                    border-collapse: collapse;
                }
                
                .appearances-table th,
                .appearances-table td {
                    padding: 0.75rem;
                    border-bottom: 1px solid var(--card-border-color);
                }
                
                .appearances-table thead {
                    border-bottom: 2px solid var(--card-border-color);
                }
                
                .appearances-table tr:hover {
                    background: var(--card-hover-color);
                }
                
                :root {
                    --card-border-color: #ddd;
                    --card-hover-color: rgba(0,0,0,0.02);
                }
                
                @media (prefers-color-scheme: dark) {
                    :root {
                        --card-border-color: #444;
                        --card-hover-color: rgba(255,255,255,0.02);
                    }
                }
                
                @media (max-width: 640px) {
                    .details-grid {
                        grid-template-columns: 1fr;
                    }
                    
                    .appearances-table {
                        display: block;
                        overflow-x: auto;
                    }
                }
                  
                .summary-controls {
                    margin-bottom: 1rem;
                }
                
                .summary-table {
                    width: 100%;
                    text-align: left;
                    border-collapse: collapse;
                }
                
                .summary-table th,
                .summary-table td {
                    padding: 0.75rem;
                    border-bottom: 1px solid var(--card-border-color);
                    text-align: center;
                }
                
                .summary-table th:first-child,
                .summary-table td:first-child {
                    text-align: left;
                }
                
                .summary-table thead {
                    border-bottom: 2px solid var(--card-border-color);
                }
                
                .summary-table tr:hover {
                    background: var(--card-hover-color);
                }
                  
                .pagination {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 1rem;
                    margin-top: 1rem;
                }
                
                .pagination .button {
                    margin: 0;
                }
                
                .appearances-table thead {
                    position: sticky;
                    top: 0;
                    background: var(--card-background-color);
                    z-index: 1;
                }
                
                .filter-controls {
                    margin-bottom: 1rem;
                }
                
                .filter-controls form {
                    display: grid;
                    gap: 1rem;
                }
                  
                .pagination {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 1rem;
                    margin-top: 1rem;
                }

                .pagination-info {
                    text-align: center;
                    color: var(--text-muted);
                }

                .pagination-controls {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 1rem;
                }

                .pagination-controls .button {
                    margin: 0;
                }

                .page-info {
                    margin: 0 1rem;
                }
                  
                .date-link {
                  color: var(--primary);
                  text-decoration: none;
                }
                
                .date-link:hover {
                  text-decoration: underline;
                }
            """),
            A("← Back to Players", href="/", cls="button"),
        )
    )

@rt('/game/{game_date}')
def get(game_date: str):
    # Validate date format
    try:
        datetime.strptime(game_date, '%Y-%m-%d')
    except ValueError:
        return Titled("Invalid Date Format",
            Container(
                H2("Invalid date format"),
                P("Please use the format YYYY-MM-DD"),
                A("← Back to Players", href="/", cls="button")
            )
        )

    # Get game details
    game_cursor = db.conn.execute('''
        SELECT * FROM results WHERE game_date = ?
    ''', [game_date])
    
    game_row = game_cursor.fetchone()
    if not game_row:
        return Titled("Game Not Found",
            Container(
                H2("No game found for this date"),
                P(f"There was no game played on {game_date}"),
                A("← Back to Players", href="/", cls="button")
            )
        )
        
    game_details = dict(zip([d[0] for d in game_cursor.description], game_row))
    
    # Get match stats if available
    stats_cursor = db.conn.execute('''
        SELECT * FROM match_stats WHERE game_date = ?
    ''', [game_date])
    match_stats = [dict(zip([d[0] for d in stats_cursor.description], row)) 
                  for row in stats_cursor.fetchall()]
    
    # Get league table if it's a league game
    league_table = []
    if game_details['game_type'] == 'League':
        table_cursor = db.conn.execute('''
            SELECT * FROM league_tables 
            WHERE game_date = ? 
            ORDER BY pos
        ''', [game_date])
        league_table = [dict(zip([d[0] for d in table_cursor.description], row)) 
                       for row in table_cursor.fetchall()]

    home_stats = next((s for s in match_stats if s['team_venue'] == 'home'), None)
    away_stats = next((s for s in match_stats if s['team_venue'] == 'away'), None)

    stats_fields = [
        ('possessionPercentage', 'Possession %'),
        ('shotsTotal', 'Total Shots'),
        ('shotsOnTarget', 'Shots on Target'),
        ('shotsOffTarget', 'Shots off Target'),
        ('shotsBlocked', 'Blocked Shots'),
        ('shotsSaved', 'Saves'),
        ('foulsCommitted', 'Fouls'),
        ('cornersWon', 'Corners'),
        ('touchesInBox', 'Touches in Box'),
        ('aerialsWon', 'Aerials Won')
    ]

    return Titled(f"Match Details - {game_date}",
        Container(
            A("← Back to Players", href="/", cls="button"),
            
            # Match Details Card
            Card(
                H2("Match Details", cls="text-center"),
                Table(
                    Tbody(
                        Tr(Td("Competition"), Td(game_details['competition'])),
                        Tr(Td("Opposition"), Td(game_details['opposition'])),
                        Tr(Td("Venue"), Td(game_details['venue'])),
                        Tr(Td("Score"), Td(game_details['score'])),
                        Tr(Td("Outcome"), Td(game_details['outcome'])),
                        Tr(Td("Attendance"), Td(str(game_details['attendance']))),
                        Tr(Td("Referee"), Td(game_details['referee'])),
                        Tr(Td("Kickoff Time"), Td(game_details['ko_time'])),
                        Tr(Td("Stadium"), Td(game_details['stadium'])),
                        Tr(Td("League Position"), Td(str(game_details['league_pos']))),
                        Tr(Td("League Points"), Td(str(game_details['league_pts'])))
                    ),
                    cls="match-details-table"
                )
            ),

            # Match Stats Card (if stats exist)
            Card(
                H2("Match Statistics", cls="text-center"),
                Table(
                    Thead(
                        Tr(
                            Th(home_stats['team_name'] if home_stats else 'Home'),
                            Th("Statistic"),
                            Th(away_stats['team_name'] if away_stats else 'Away')
                        )
                    ),
                    Tbody(
                        *[Tr(
                            Td(str(home_stats[key]) if home_stats else '-'),
                            Td(label),
                            Td(str(away_stats[key]) if away_stats else '-')
                        ) for key, label in stats_fields]
                    ) if home_stats and away_stats else [
                        Tr(Td("No statistics available", colspan="3", cls="text-center"))
                    ],
                    cls="match-stats-table"
                )
            ) if match_stats else None,

            # League Table Card (if league game)
            Card(
                H2("League Table", cls="text-center"),
                Table(
                    Thead(
                        Tr(
                            Th("Pos"),
                            Th("Team"),
                            Th("P"),
                            Th("W"),
                            Th("D"),
                            Th("L"),
                            Th("GF"),
                            Th("GA"),
                            Th("GD"),
                            Th("Pts")
                        )
                    ),
                    Tbody(
                        *[Tr(
                            Td(str(row['pos'])),
                            Td(row['team_name']),
                            Td(str(row['pld'])),
                            Td(str(row['w'])),
                            Td(str(row['d'])),
                            Td(str(row['l'])),
                            Td(str(row['gf'])),
                            Td(str(row['ga'])),
                            Td(str(row['gd'])),
                            Td(str(row['pts']))
                        ) for row in league_table]
                    ) if league_table else [
                        Tr(Td("No league table available", colspan="10", cls="text-center"))
                    ],
                    cls="league-table"
                )
            ) if game_details['game_type'] == 'League' else None,

            Style("""
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-bottom: 1rem;
                }
                th, td {
                    padding: 0.75rem;
                    text-align: left;
                    border-bottom: 1px solid var(--card-border-color);
                }
                th {
                    font-weight: bold;
                    background: var(--card-background-color);
                }
                .match-stats-table td:first-child,
                .match-stats-table td:last-child {
                    text-align: center;
                }
                .league-table td {
                    text-align: center;
                }
                .league-table td:nth-child(2) {
                    text-align: left;
                }
                .text-center {
                    text-align: center;
                }
            """)
        )
    )

@rt("/seasons")
def get(): 
   seasons = db.query("SELECT DISTINCT season FROM results ORDER BY season DESC")
   seasons = [s['season'] for s in seasons]
   return Form(
       Div(
           *[Div(Label(CheckboxX(id=s, name="seasons[]", value=s), s)) for s in seasons],
           style="max-height: 300px; overflow-y: auto;"
       ),
       Button("Submit"), 
       hx_post="/filter"
   )


@rt("/managers")
def get():
    return Title("All Managers"), Div(
        Div(
            H1("All managers"),
            Form(
                P('Season range'),
                Input(type="range", name="min_season", min=1921, max=2024, value=1921),
                Input(type="range", name="max_season", min=1921, max=2024, value=2024),
                Hr(),

                Fieldset(
                    Legend('League Tiers'),
                    Label(
                        Input(type='checkbox', name='league_tier', value=2, checked='checked'),
                        "2: Championship",
                    ),
                    Label(
                        Input(type='checkbox', name='league_tier', value=3, checked='checked'),
                        "3: League One"
                    ),
                    Label(
                        Input(type='checkbox', name='league_tier', value=4, checked='checked'),
                        "4: League Two"
                    ),
                    Label(
                        Input(type='checkbox', name='league_tier', value=5, checked='checked'),
                        "5: National League"
                    )
                ),
                Button("All leagues"),
                Button("Clear", cls="secondary"),
                Hr(),

                Fieldset(
                    Legend("Include play-off games?"),
                    Label(
                        Input(type="radio", name="play_offs", value="Y", checked="checked"),
                        "Yes"
                    ),
                    Label(
                        Input(type="radio", name="play_offs", value="N"),
                        "No"
                    )
                ),
                Hr(),

                Fieldset(
                    Legend("Cup competitions:"),
                    Label(
                        Input(type="checkbox", name="competition", value="Anglo-Italian Cup", checked="checked"),
                        "Anglo-Italian Cup"
                    ),
                    Label(
                        Input(type="checkbox", name="competition", value="Associate Members' Cup", checked="checked"),
                        "Associate Members' Cup"
                    ),
                    Label(
                        Input(type="checkbox", name="competition", value="FA Cup", checked="checked"),
                        "FA Cup"
                    ),
                    Label(
                        Input(type="checkbox", name="competition", value="FA Trophy", checked="checked"),
                        "FA Trophy"
                    ),
                    Label(
                        Input(type="checkbox", name="competition", value="Full Members' Cup", checked="checked"),
                        "Full Members' Cup"
                    ),
                    Label(
                        Input(type="checkbox", name="competition", value="League Cup", checked="checked"),
                        "League Cup"
                    ),
                    Label(
                        Input(type="checkbox", name="competition", value="War League", checked="checked"),
                        "War League"
                    )
                ),
                Button("All cups"),
                Button("Clear", cls="secondary"),
                Hr(),
                
                Fieldset(
                    Legend('Venues'),
                    Label(
                        Input(type='checkbox', name='venue', value='H', checked='checked'),
                        "Home"
                    ),
                    Label(
                        Input(type='checkbox', name='venue', value='A', checked='checked'),
                        "Away"
                    ),
                    Label(
                        Input(type='checkbox', name='venue', value='N', checked='checked'),
                        "Neutral"
                    )
                ),
                Hr(),

                Label(
                    'Minimum number of games managed:',
                    Input(type="range", name="min_games", min=1, max=100, value=10)
                ),
                id="manager-options", hx_trigger="input", hx_post="/managers-update", hx_target="#man_records", hx_swap="innerHTML"
            ),
            Hr(),
            Button("Reset all", cls="secondary")
        ),
        Div(
            Div("", id="man_records")
        ),
    cls='grid')

@rt("/manager-rec/{manager_name}")
def get(manager_name):
    print(manager_name)
    return Div(
        H1(f"{manager_name}"),
    style=f"display: {'grid' if show else 'none'}; gap: 10rem;")

# Refer example here for removing Javascript
# https://gallery.fastht.ml/split/widgets/show_hide

@rt("/manager-rec/{manager_name}")
def get(manager_name: str):
    """Route to fetch manager record details"""
    # Your existing logic to fetch manager records
    return f"Details for {manager_name} " * 20  # Replace with your actual manager record fetch logic

def show_hide(subject_id: str, target_route: str):
    return Span(
        # "→ Show", id=f"expand-{subject_id}",
        "+", id=f"expand-{subject_id}",
        onclick=f"toggleRequestInfo('{subject_id}')",
        style="cursor: pointer;",
        hx_get=f"/{target_route}/{subject_id}",
        hx_target=f"#expanded-{subject_id.replace(' ', '_') if subject_id else ''}"
    ),

@rt("/managers-update")
def post(data: dict):
    """Handle POST request to update manager statistics table.
    
    Args:
        data: Dictionary containing filter parameters
        
    Returns:
        Tuple of (data, Card) containing filtered manager statistics
    """
    def format_cell(value, col):
        """Format cell value based on column type."""
        if value is None:
            return "-"
        if col == 'win_pc':
            return f"{value:.1f}%"
        return str(value)

    columns = [
        ('manager_name', 'Manager'),
        ('P', 'P'),
        ('W', 'W'),
        ('D', 'D'),
        ('L', 'L'),
        ('GF', 'GF'),
        ('GA', 'GA'),
        ('GD', 'GD'),
        ('win_pc', 'Win %')
    ]
    
    manager_records = filter_managers(data)
    manager_streaks = get_manager_streaks(data)

    return Card(
        H2("Overall Records"),
        Div(
            # Header row
            Div(Span(),
                *[Div(header) for _, header in columns],
                style="display: grid; grid-template-columns: repeat(10, 1fr); font-weight: bold;"
            ),
                *[Div(Div(
                    # Span(
                    #     "→ Show", id=f"expand-{record['manager_name']}",
                    #     onclick=f"toggleRequestInfo('{record['manager_name']}')",
                    #     style="cursor: pointer;",
                    #     hx_get=f"/manager-rec/{record['manager_name']}",
                    #     hx_target=f"#expanded-{record['manager_name'].replace(' ', '_') if record['manager_name'] else ''}"
                    # ),
                    show_hide(record['manager_name'], 'manager-rec'),
                    *[Div(format_cell(record[col], col))
                      for col, _ in columns],
                style="display: grid; grid-template-columns: repeat(10, 1fr);"
                ),
                Span(
                    id=f"expanded-{record['manager_name'].replace(' ', '_') if record['manager_name'] else ''}",
                ),
                id=f"{record['manager_name']}") for record in manager_records],
        style="display: grid; gap: 1rem;"
        )
    )

def join_list(lst):
    return ','.join(f"'{l.replace("'", "''")}'" for l in lst)

def filter_managers(data, manager=None):
    if 'league_tier' in data:
        league_tiers = join_list(data['league_tier'])
    else:
        league_tiers = None
    if 'competition' in data:
        competitions = join_list(data['competition'])
    else:
        competitions = None

    venues = ','.join(f"'{v}'" for v in data['venue'])

    min_games = data['min_games']
    
    filters = 'AND '
    if league_tiers and competitions:
        filters += f"(slt.league_tier IN ({league_tiers}) OR r.competition IN ({competitions}))"
    elif league_tiers:
        filters += f"slt.league_tier IN ({league_tiers})"
    elif competitions:
        filters += f"r.competition IN ({competitions})"

    man_query = f'AND m.manager_name = "{manager}"'
    
    query  = f'''
        SELECT 
            m.manager_name,
            COUNT(*) as P,
            COUNT(CASE WHEN r.outcome = 'W' THEN 1 END) as W,
            COUNT(CASE WHEN r.outcome = 'D' THEN 1 END) as D,
            COUNT(CASE WHEN r.outcome = 'L' THEN 1 END) as L,
            SUM(r.goals_for) as GF,
            SUM(r.goals_against) as GA,
            SUM(r.goals_for) - SUM(r.goals_against) as GD,
            ROUND(CAST(COUNT(CASE WHEN r.outcome = 'W' THEN 1 END) AS FLOAT) / COUNT(*) * 100, 2) as win_pc
        FROM results r
        LEFT JOIN manager_reigns mr ON r.game_date >= mr.mgr_date_from
            AND (r.game_date <= mr.mgr_date_to OR mr.mgr_date_to IS NULL)
        LEFT JOIN managers m ON mr.manager_id = m.manager_id
        LEFT JOIN season_league_tiers slt ON r.season = slt.season AND r.game_type = 'League'
        WHERE CAST(SUBSTRING(r.season, 1, 4) AS INTEGER) >= {data['min_season']} AND CAST(SUBSTRING(r.season, 1, 4) AS INTEGER) <= {data['max_season']}
            AND r.venue IN ({venues})
            {filters}
            {f"{man_query if manager else ''}"}
        GROUP BY m.manager_name
        HAVING COUNT(*) >= {min_games}
        ORDER BY P DESC
    '''
    
    managers_cursor = db.conn.execute(
        query
    )
    
    if not manager:
        return [dict(zip([d[0] for d in managers_cursor.description], row)) for row in managers_cursor.fetchall()]
    else:
        return managers_cursor.fetchall()

def get_manager_streaks(data: dict):
    if 'league_tier' in data:
        league_tiers = join_list(data['league_tier'])
    else:
        league_tiers = None
    if 'competition' in data:
        competitions = join_list(data['competition'])
    else:
        competitions = None

    venues = ','.join(f"'{v}'" for v in data['venue'])

    min_games = data['min_games']
    
    filters = 'AND '
    if league_tiers and competitions:
        filters += f"(slt.league_tier IN ({league_tiers}) OR r.competition IN ({competitions}))"
    elif league_tiers:
        filters += f"slt.league_tier IN ({league_tiers})"
    elif competitions:
        filters += f"r.competition IN ({competitions})"

    query  = f'''
        SELECT 
            m.manager_name,
            r.*
        FROM results r
        LEFT JOIN manager_reigns mr ON r.game_date >= mr.mgr_date_from
            AND (r.game_date <= mr.mgr_date_to OR mr.mgr_date_to IS NULL)
        LEFT JOIN managers m ON mr.manager_id = m.manager_id
        LEFT JOIN season_league_tiers slt ON r.season = slt.season AND r.game_type = 'League'
        WHERE CAST(SUBSTRING(r.season, 1, 4) AS INTEGER) >= {data['min_season']} AND CAST(SUBSTRING(r.season, 1, 4) AS INTEGER) <= {data['max_season']}
            AND r.venue IN ({venues})
            {filters}
    '''

    # Load base data
    df = pd.read_sql(query, db.conn)

    # Basic stats
    stats = df.groupby('manager_name').agg({
        'outcome': ['count',
                lambda x: (x == 'W').sum(),
                lambda x: (x == 'D').sum(),
                lambda x: (x == 'L').sum()],
        'goals_for': 'sum',
        'goals_against': 'sum'
    }).reset_index()

    # Calculate streaks
    def get_streak_lengths(group, condition):
        # Creates groups of consecutive True values and returns their lengths
        streak_groups = (group != group.shift()).cumsum()
        return group.groupby(streak_groups).sum()

    # Example for win streaks
    df['is_win'] = df['outcome'] == 'W'
    streaks = df.groupby('manager_name')['is_win'].apply(
        lambda x: get_streak_lengths(x, True).max()
    )

    # Similarly for other streaks...
    df['is_unbeaten'] = df['outcome'] != 'L'
    df['is_clean_sheet'] = df['goals_against'] == 0
    # etc.
    return df

serve()