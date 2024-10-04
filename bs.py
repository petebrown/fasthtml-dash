from fasthtml.common import *

def create_season_selector():
    seasons = [f"{year}/{str(year+1)[-2:]}" for year in range(2024, 1921, -1)]
    
    options = [Option(season, value=season) for season in seasons]
    
    select = Select(
        *options,
        id="season-selector",
        cls="form-select",
        multiple=True,
        data_bs_toggle="SelectizeCustom",
        style="width: 100%;"
    )
    
    dropdown = Div(
        select,
        cls="season-selector-wrapper"
    )
    
    return dropdown

app, rt = fast_app(
    pico=False,
    hdrs=(
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'),
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css'),
        Link(rel="stylesheet", href="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.13.3/css/selectize.bootstrap4.min.css"),
        Script(src='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js'),
        Script(src="https://code.jquery.com/jquery-3.6.0.min.js"),
        Script(src="https://cdnjs.cloudflare.com/ajax/libs/selectize.js/0.15.2/js/selectize.min.js"),
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
        """)
    )
)

@rt('/')
def get():
    navbar = Nav(
        Div(
            A(
                Img(src="https://raw.githubusercontent.com/petebrown/trfcdash/refs/heads/main/inst/app/www/images/crest.svg", alt="Logo", width="50", height="50", cls="d-inline-block align-text-top"),
                "Soccer Dashboard",
                cls="navbar-brand"
            ),
            cls="container-fluid"
        ),
        cls="navbar navbar-expand-lg navbar-light bg-light fixed-top"
    )

    icon_sidebar = Div(
        Ul(
            Li(A(I(cls='bi bi-trophy'), href='#', cls='nav-link', data_bs_toggle='tooltip', data_bs_placement='right', title='Seasons'), cls='nav-item'),
            Li(A(I(cls='bi bi-people'), href='#', cls='nav-link', data_bs_toggle='tooltip', data_bs_placement='right', title='Head to Head'), cls='nav-item'),
            Li(A(I(cls='bi bi-person-badge'), href='#', cls='nav-link', data_bs_toggle='tooltip', data_bs_placement='right', title='Managers'), cls='nav-item'),
            Li(A(I(cls='bi bi-person-circle'), href='#', cls='nav-link', data_bs_toggle='tooltip', data_bs_placement='right', title='Players'), cls='nav-item'),
            Li(A(I(cls='bi bi-graph-up'), href='#', cls='nav-link', data_bs_toggle='tooltip', data_bs_placement='right', title='Attendances'), cls='nav-item'),
            Li(A(I(cls='bi bi-calendar-event'), href='#', cls='nav-link', data_bs_toggle='tooltip', data_bs_placement='right', title='On This Day'), cls='nav-item'),
        ),
        id='icon-sidebar', cls='sidebar bg-light'
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
            cls='container-fluid'
        ),
        id='main-content',
        cls='main-content'
    )
    
    toggle_script = Script("""
        document.getElementById('collapsible-sidebar').addEventListener('hide.bs.collapse', function () {
            document.getElementById('main-content').classList.add('sidebar-collapsed');
        });
        document.getElementById('collapsible-sidebar').addEventListener('show.bs.collapse', function () {
            document.getElementById('main-content').classList.remove('sidebar-collapsed');
        });
        
        // Initialize tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
        });

        // Initialize Selectize
        $(document).ready(function() {
            $('#season-selector').selectize({
                plugins: ['remove_button'],
                placeholder: 'Select seasons...',
                maxItems: null
            });
        });
    """)
    
    return Div(
        navbar, icon_sidebar, toggle_button, collapsible_sidebar, main_content, toggle_script
    )

serve()