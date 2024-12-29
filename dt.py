from fasthtml.common import *
import pandas as pd
import json
from datetime import datetime

app, rt = fast_app()

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, pd.Timestamp)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@rt('/')
def get():
    # Fetch and process CSV data
    url = 'https://raw.githubusercontent.com/petebrown/data-updater/refs/heads/main/data/results.csv'
    df = pd.read_csv(url, parse_dates=['game_date'])
    cols = ['season', 'game_date', 'game_no', 'opposition', 'venue', 'score']
    data = df[cols].to_dict(orient='records')
    
    # Debug: Print first few rows of data
    print("First 5 rows of data:", data[:5])
    
    # Create table
    table = Table(id="example", cls="display", style="width:100%")(
        Thead(
            Tr(
                Th(""),
                *[Th(col.replace('_', ' ').title()) for col in cols]
            )
        ),
        Tfoot(
            Tr(
                Th(""),
                *[Th(col.replace('_', ' ').title()) for col in cols]
            )
        )
    )
    
    # JavaScript to initialize DataTable
    script = Script(f"""
    // Function to load scripts in sequence
    function loadScript(url, callback) {{
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = url;
        script.onload = callback;
        document.head.appendChild(script);
    }}

    // Load scripts in sequence
    loadScript('https://code.jquery.com/jquery-3.6.0.min.js', function() {{
        loadScript('https://cdn.datatables.net/1.10.25/js/jquery.dataTables.min.js', function() {{
            // All scripts are loaded, now we can initialize DataTable
            $(document).ready(function() {{
                console.log("Scripts loaded, initializing DataTable");
                
                // Debug: Log the data received
                console.log("Data received:", {json.dumps(data[:5], default=json_serial)});

                // Formatting function for row details
                function format(d) {{
                    return (
                        '<table cellpadding="5" cellspacing="0" border="0" style="padding-left:50px;">' +
                        '<tr><td>Season:</td><td>' + d.season + '</td></tr>' +
                        '<tr><td>Game Date:</td><td>' + d.game_date + '</td></tr>' +
                        '<tr><td>Game Number:</td><td>' + d.game_no + '</td></tr>' +
                        '<tr><td>Opposition:</td><td>' + d.opposition + '</td></tr>' +
                        '<tr><td>Venue:</td><td>' + d.venue + '</td></tr>' +
                        '<tr><td>Score:</td><td>' + d.score + '</td></tr>' +
                        '</table>'
                    );
                }}

                let table = $('#example').DataTable({{
                    data: {json.dumps(data, default=json_serial)},
                    columns: [
                        {{
                            className: 'dt-control',
                            orderable: false,
                            data: null,
                            defaultContent: ''
                        }},
                        {{ data: 'season' }},
                        {{ 
                            data: 'game_date',
                            render: function(data, type, row) {{
                                if (type === 'display' || type === 'filter') {{
                                    return new Date(data).toLocaleDateString();
                                }}
                                return data;
                            }}
                        }},
                        {{ data: 'game_no' }},
                        {{ data: 'opposition' }},
                        {{ data: 'venue' }},
                        {{ data: 'score' }}
                    ],
                    order: [[2, 'asc']],  // Sort by game date
                    rowId: 'game_no'
                }});
                
                // Debug: Log the DataTable object
                console.log("DataTable object:", table);

                // Add event listener for opening and closing details
                $('#example').on('click', 'td.dt-control', function () {{
                    var tr = $(this).closest('tr');
                    var row = table.row(tr);
             
                    if (row.child.isShown()) {{
                        // This row is already open - close it
                        row.child.hide();
                        tr.removeClass('shown');
                    }}
                    else {{
                        // Open this row
                        row.child(format(row.data())).show();
                        tr.addClass('shown');
                    }}
                }});
            }});
        }});
    }});
    """)
    
    # CSS for styling
    style = Style("""
        # td.dt-control {
        #     background: url('https://www.datatables.net/examples/resources/details_open.png') no-repeat center center;
        #     cursor: pointer;
        # }
        # tr.shown td.dt-control {
        #     background: url('https://www.datatables.net/examples/resources/details_close.png') no-repeat center center;
        # }
    """)
    
    # Include CSS link
    css_link = Link(rel="stylesheet", href="https://cdn.datatables.net/1.10.25/css/jquery.dataTables.min.css")
    
    return Titled("Results Table", css_link, style, table, script)

serve()