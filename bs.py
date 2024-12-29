from fasthtml.common import *
from fh_altair import altair2fasthtml, altair_headers
from fh_plotly import plotly2fasthtml, plotly_headers
import altair as alt
import plotly.express as px
import pandas as pd

results = pd.read_csv('https://raw.githubusercontent.com/petebrown/data-updater/main/data/results.csv', parse_dates=['game_date'])
seasons = results['season'].sort_values(ascending=False).unique()

res_with_comp = results[['game_date', 'season', 'competition']].copy()

goals = pd.read_csv('data/goals.csv', parse_dates=['game_date'])

players = pd.read_csv('data/players.csv')
player_names = players[['player_id', 'player_name']].copy()

scorers_df = goals.merge(player_names, on='player_id', how='left') \
    .merge(res_with_comp, on='game_date', how='left') \
    .query('own_goal != 1') \
    .groupby(['season', 'player_name', 'competition']) \
    .size() \
    .reset_index(name='goals')

def create_season_selector():
    seasons = [f"{year}/{str(year+1)[-2:]}" for year in range(2024, 1921, -1)]
    
    options = [Option(season, value=season, selected=season in ['2023/24', '2024/25']) for season in seasons]
    
    select = Select(
        *options,
        id="season-selector",
        name="seasons",
        cls="form-select",
        multiple=True,
        data_bs_toggle="SelectizeCustom",
        style="width: 100%;",
        hx_post="/update_seasons",
        hx_trigger="change",
        hx_target="#selected-seasons"
    )
    
    return Div(select, cls="season-selector-wrapper")

app, rt = fast_app(
    pico=False,
    hdrs=(
        plotly_headers,
        altair_headers,
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'),
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css'),
        Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.13.3/css/selectize.bootstrap4.min.css"),
        Link(rel="stylesheet", type="text/css", href="https://cdn.datatables.net/1.10.24/css/jquery.dataTables.css"),
        Script(src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'),
        Script(src="https://code.jquery.com/jquery-3.6.0.min.js"),
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.15.2/js/selectize.min.js"),
        Script(src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.js"),
        Style("""
            body {
                min-height: 100vh;
                padding-top: 70px;
            }
            .navbar {
                height: 70px;
            }
            .navbar-brand {
                display: flex;
                align-items: center;
            }
            .navbar-brand img {
                margin-right: 10px;
            }
            #icon-sidebar {
                width: 4.5rem;
                left: 0;
                border-right: 0.3px darkgrey solid;
                top: 70px;
                padding-top: 50px;
            }
            #icon-sidebar ul {
                list-style-type: none;
                padding: 0;
                margin: 0;
            }
            #icon-sidebar ul li {
                padding: 0;
                margin: 0;
            }
            #icon-sidebar .nav-link {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 4.5rem;
                width: 4.5rem;
            }
            #icon-sidebar .bi {
                font-size: 1.5rem;
            }
            #collapsible-sidebar {
                width: 250px;
                left: 4.5rem;
                border-right: 0.3px darkgrey solid;
                padding: 0;
                top: 70px;
            }
            .sidebar {
                position: fixed;
                bottom: 0;
                z-index: 100;
                padding: 0;
                height: calc(100vh - 70px);
                overflow-x: hidden;
                overflow-y: auto;
            }
            .main-content {
                margin-left: calc(4.5rem + 250px);
                transition: margin-left 0.3s ease-in-out;
                padding: 2rem;
            }
            .main-content.sidebar-collapsed {
                margin-left: 4.5rem;
            }
            #toggle-btn {
                position: fixed;
                left: 1rem;
                top: 5rem;
                z-index: 1000;
            }
            .season-selector-wrapper {
                padding: 0.6rem 1rem 1rem 1rem;
            }
            .season-selector-wrapper .form-select {
                --bs-form-select-bg-img: none;
                padding: .375rem .75rem .375rem .75rem;
            }
            .season-selector-wrapper .selectize-input {
                border: none;
                border-radius: 0.25rem;
                padding: 0.375rem 0.75rem;
            }
            .season-selector-wrapper .selectize-dropdown {
                border: 1px solid #ced4da;
                border-radius: 0.25rem;
            }
            .season-selector-wrapper .selectize-dropdown-content {
                max-height: 200px;
                overflow-y: auto;
            }
            .season-selector-wrapper .selectize-dropdown-content .option {
                padding: 0.375rem 0.75rem;
            }
            .season-selector-wrapper .selectize-dropdown-content .option:hover {
              background-color: #f8f9fa;
            }
            .full-width-chart {
                width: 100%;
                max-width: 100%;
                overflow-x: auto;  /* Add this line to enable horizontal scrolling if needed */
            }
            .full-width-chart > * {
                width: 100% !important;
                max-width: 100% !important;
            }
        """)
    )
)

def get_navbar():
    navbar = Nav(
        Div(
            A(
                Img(src='https://raw.githubusercontent.com/petebrown/trfcdash/refs/heads/main/inst/app/www/images/crest.svg', alt='Tranmere Rovers: A Complete Record', height='45'),
                "A Complete Record",
                href='#',
                cls='navbar-brand d-flex align-items-center'
            ),
            cls='container-fluid'
        ),
        cls='navbar navbar-expand-lg navbar-light bg-light fixed-top'
    )
    return navbar

@rt('/')
def get():
    navbar = get_navbar()

    def sidebar_item(icon_class, title, href='#'):
        return Li(
            A(
                I(cls=f'bi {icon_class}'),
                href=href,
                cls='nav-link',
                data_bs_toggle='tooltip',
                data_bs_placement='right',
                title=title
            ),
            cls='nav-item'
        )

    icon_sidebar = Div(
        Ul(
            sidebar_item('bi-trophy', 'Seasons'),
            sidebar_item('bi-people', 'Head to Head'),
            sidebar_item('bi-person-badge', 'Managers'),
            sidebar_item('bi-person-circle', 'Players'),
            sidebar_item('bi-graph-up', 'Attendances'),
            sidebar_item('bi-calendar-event', 'On This Day'),
        ),
        id='icon-sidebar',
        cls='sidebar bg-light'
    )
    
    season_selector = create_season_selector()
    
    collapsible_sidebar = Div(
        Div(
            P("Select Seasons", cls='sidebar-heading d-flex justify-content-between align-items-center px-3 mb-1 text-muted'),
            season_selector,
            cls='position-sticky pt-3'
        ),
        id='collapsible-sidebar', cls='sidebar bg-light collapse collapse-horizontal show'
    )
    
    toggle_button = Button(
        I(cls='bi bi-list'),
        id='toggle-btn',
        cls='btn btn-primary',
        data_bs_toggle='collapse',
        data_bs_target='#collapsible-sidebar'
    )
    
    main_content = Main(
        Div(
            H1("Soccer Dashboard"),
            P("Welcome to the Soccer Dashboard. Use the sidebar to select seasons and navigate the app."),
            H2("Selected Seasons"),
            Div(id="selected-seasons"),
            cls='container-fluid'
        ),
        id='main-content',
        cls='main-content'
    )

    
    
    toggle_script = Script("""
        document.addEventListener('DOMContentLoaded', function() {
            var collapsibleSidebar = document.getElementById('collapsible-sidebar');
            var mainContent = document.getElementById('main-content');

            collapsibleSidebar.addEventListener('hide.bs.collapse', function () {
                mainContent.classList.add('sidebar-collapsed');
            });

            collapsibleSidebar.addEventListener('show.bs.collapse', function () {
                mainContent.classList.remove('sidebar-collapsed');
            });
            
            // Initialize tooltips
            var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.forEach(function (tooltipTriggerEl) {
                new bootstrap.Tooltip(tooltipTriggerEl);
            });

            // Initialize Selectize
            var $select = $('#season-selector').selectize({
                plugins: ['remove_button'],
                placeholder: 'Select seasons...',
                maxItems: null,
                onChange: function() {
                    // Trigger HTMX request
                    htmx.trigger('#season-selector', 'change');
                }
            });

            // Set default values
            var selectize = $select[0].selectize;
            selectize.setValue(['2023/24', '2024/25']);
            
            // Trigger initial update
            htmx.trigger('#season-selector', 'change');
        });
    """)
    
    return Div(
        navbar, icon_sidebar, toggle_button, collapsible_sidebar, main_content, toggle_script
    )

@rt('/update_seasons', methods=['POST'])
async def update_seasons(request):
    form = await request.form()
    seasons = form.getlist('seasons')
    
    if not seasons:
        seasons = ['2023/24', '2024/25']  # Use default seasons if none selected
    
    print(f"Selected seasons: {seasons}")  # Server-side console log
    
    return Div(
        H3("You have selected the following seasons:"),
        Ul(*[Li(season) for season in seasons]),
        # Card(plot_positions(seasons), cls="full-width-chart"),
        # Card(plot_points(seasons), cls="full-width-chart"),
        # Card(plot_ppg(seasons), cls="full-width-chart"),

        Div(
            Div(
                Card(altair_positions(seasons), cls="col full-width-chart"),
            cls='row'),
        cls='container'),
        Div(
            Div(
                Card(altair_points(seasons), cls="col full-width-chart"),
                Card(altair_ppg(seasons), cls="col full-width-chart"),
            cls='row'),
        cls='container'),
        Div(
            Div(
                Card(*[create_stacked_bar_chart(scorers_df, season) for season in seasons], cls="col full-width-chart"),
            cls='row'),
        cls='container',),
        id='selected-seasons'
    )

def plot_positions(seasons):
    df = results[(results['season'].isin(seasons)) & (results['game_type']=='League')]
    fig = px.line(df, x='ssn_comp_game_no', y='league_pos', color='season', title=f'Positions for {seasons}')
    return plotly2fasthtml(fig)

def altair_positions(seasons):
    df = results[(results['season'].isin(seasons)) & (results['game_type']=='League')]
    chart = alt.Chart(df).mark_line().encode(
        x='ssn_comp_game_no',
        y='league_pos',
        color='season',
        tooltip=['season', 'ssn_comp_game_no', 'league_pos']
    ).properties(
        title=f'Positions for {seasons}',
        width='container',
        height=600
    )
    return altair2fasthtml(chart)

def plot_ppg(seasons):
    df = results[(results['season'].isin(seasons)) & (results['game_type']=='League')]
    df['ppg'] = df['pts'] / df['ssn_comp_game_no']
    fig = px.line(df, x='ssn_comp_game_no', y='ppg', color='season', title=f'Points per game for {seasons}')
    return plotly2fasthtml(fig)

def altair_ppg(seasons):
    df = results[(results['season'].isin(seasons)) & (results['game_type']=='League')].copy()
    df['ppg'] = df['pts'] / df['ssn_comp_game_no']
    chart = alt.Chart(df).mark_line().encode(
        x='ssn_comp_game_no',
        y='ppg',
        color='season',
        tooltip=['season', 'ssn_comp_game_no', 'ppg']
    ).properties(
        title=f'Points per game for {seasons}',
        width='container',
        height=400
    )
    return altair2fasthtml(chart)

def plot_points(seasons):
    df = results[(results['season'].isin(seasons)) & (results['game_type']=='League')]
    fig = px.line(df, x='ssn_comp_game_no', y='pts', color='season', title=f'Points per game for {seasons}')
    return plotly2fasthtml(fig)

def altair_points(seasons):
    df = results[(results['season'].isin(seasons)) & (results['game_type']=='League')]
    chart = alt.Chart(df).mark_line().encode(
        x='ssn_comp_game_no',
        y='pts',
        color='season',
        tooltip=['season', 'ssn_comp_game_no', 'pts']
    ).properties(
        title=f'Point accumulation {seasons}',
        width='container',
        height=400
    )
    return altair2fasthtml(chart)

def create_stacked_bar_chart(df, season, n_scorers=3):
    # Filter the DataFrame for the given season
    season_df = df[df['season'] == season].copy()
    
    # Calculate total goals for each player across all competitions
    player_totals = season_df.groupby('player_name')['goals'].sum().reset_index()
    player_totals = player_totals.rename(columns={'goals': 'total_goals'})
    
    # Sort players by total goals (descending order) and select top n_scorers
    player_order = player_totals.sort_values('total_goals', ascending=False)['player_name'].head(n_scorers).tolist()
    
    # Filter season_df to include only top n_scorers
    season_df = season_df[season_df['player_name'].isin(player_order)]
    
    # Merge the totals back to the main dataframe
    season_df = season_df.merge(player_totals, on='player_name')
    
    # Define the custom order for competitions
    competition_order = ['League Two', 'The Emirates FA Cup', 'Carabao Cup']
    
    # Create a mapping for competition order
    competition_order_map = {comp: i for i, comp in enumerate(competition_order)}
    
    # Add a new column for competition order
    season_df['competition_order'] = season_df['competition'].map(competition_order_map)
    
    # Calculate height based on number of players (50 pixels per player, minimum 200)
    chart_height = max(len(player_order) * 50, 200)
    
    # Create the base chart
    base = alt.Chart(season_df).encode(
        y=alt.Y('player_name:N', sort=player_order, title=None)
    )
    
    # Create the stacked bar chart with custom competition order
    bars = base.mark_bar().encode(
        x=alt.X('goals:Q', title=None),
        color=alt.Color('competition:N', 
                        scale=alt.Scale(domain=competition_order),
                        title='Competition'),
        order=alt.Order('competition_order:Q', sort='ascending'),
        tooltip=['player_name', 'competition', 'goals']
    )
    
    # Add text labels for total goals
    text = base.mark_text(align='left', dx=5).encode(
        x=alt.X('total_goals:Q'),
        text=alt.Text('total_goals:Q', format='.0f')
    )
    
    # Combine the chart elements
    chart = (bars + text).properties(
        title=f'Top {n_scorers} Goal Scorers by Competition ({season} Season)',
        width='container',
        height=chart_height
    ).configure_legend(
        orient='bottom'  # Move legend to the bottom
    ).resolve_scale(
        x='independent'
    )
    
    return altair2fasthtml(chart)


serve()