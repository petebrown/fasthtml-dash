from fasthtml.common import *
from dataclasses import dataclass
from datetime import datetime
from math import ceil


# Connect to your existing database
db = database('trfc.db')

# Create your FastHTML app and get route decorator
app, rt = fast_app()

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
        Grid(
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
                END), 0), 2) as points_per_league_start
        FROM grouped_data
        GROUP BY group_by
        ORDER BY group_by ASC
    ''', [group_by, group_by, group_by, player_id])
    
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
    
    print("Final Query:", final_query)
    print("Params:", params)
    
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
                    Td(datetime.strptime(app['game_date'], '%Y-%m-%d').strftime('%d/%m/%Y')),
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
                            Td(datetime.strptime(app['game_date'], '%Y-%m-%d').strftime('%d/%m/%Y')),
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
            """),
            A("← Back to Players", href="/", cls="button"),
        )
    )

serve()