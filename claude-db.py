from fasthtml.common import *
from dataclasses import dataclass

# Connect to your existing database
db = database('trfc.db')

# Create your FastHTML app and get route decorator
app, rt = fast_app()

def get_players(search_term=None, sort_by='display_name'):
    query = '''SELECT player_id, display_name, player_name, surname, forename,
               COALESCE(player_dob, dob_display) as display_dob,
               comp_rec_pos, soccerbase_pos, tm_pos_1, tm_pos_2, tm_pos_3, position 
               FROM players'''
    params = []
    
    if search_term:
        query += ''' WHERE display_name LIKE ? 
                    OR position LIKE ? 
                    OR player_name LIKE ?'''
        search_param = f'%{search_term}%'
        params = [search_param, search_param, search_param]
    
    query += f' ORDER BY {sort_by}'
    
    cursor = db.conn.execute(query, params)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, player)) for player in cursor.fetchall()]

def player_grid_html(players):
    return [  # Return just the cards without an outer Grid
        Card(
            H3(p['display_name']),
            P(f"Position: {p['position']}"),
            P(f"Date of Birth: {p['display_dob']}"),
            A("View Details", href=f"/player/{p['player_id']}", cls="button"),
            cls="card"
        ) for p in players
    ] if players else [P("No players found")]

@rt('/')
def get(request, q: str = '', sort: str = 'display_name'):
    players = get_players(search_term=q, sort_by=sort)
    
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
                Select(
                    Option("Name", value="display_name", selected=sort=="display_name"),
                    Option("Position", value="position", selected=sort=="position"),
                    Option("Date of Birth", value="player_dob", selected=sort=="player_dob"),
                    name="sort",
                    hx_get="/",
                    hx_target="#player-grid"
                ),
            ),
            cls="search-controls"
        )
    )
    
    return Titled("Tranmere Rovers Players",
        Container(
            controls,
            Grid(*player_grid_html(players), id="player-grid", cls="results-grid"),  # Wrap cards in Grid here
            Style("""
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
            """)
        )
    )

# Keep the player detail route the same as before
@rt('/player/{player_id}')
def get(player_id: str):
    cursor = db.conn.execute('''
        SELECT player_id, display_name, player_name, surname, forename,
               COALESCE(player_dob, dob_display) as display_dob,
               comp_rec_pos, soccerbase_pos, tm_pos_1, tm_pos_2, tm_pos_3, position 
        FROM players 
        WHERE player_id = ?
    ''', [player_id])
    columns = [description[0] for description in cursor.description]
    player = dict(zip(columns, cursor.fetchone()))
    
    return Titled(player['display_name'],
        Container(
            A("← Back to Players", href="/", cls="button"),
            H2(player['display_name']),
            Card(
                H3("Player Details"),
                P(f"Full Name: {player['forename']} {player['surname']}"),
                P(f"Position: {player['position']}"),
                P(f"Date of Birth: {player['display_dob']}"),
                P(f"Competition Record Position: {player['comp_rec_pos']}"),
                P(f"Soccerbase Position: {player['soccerbase_pos']}"),
            )
        )
    )

serve()