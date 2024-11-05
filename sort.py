from bs4 import BeautifulSoup
from fasthtml.common import *
import pandas as pd
from fastcore.basics import merge

app, rt = fast_app()

# Sample DataFrame
df = pd.DataFrame({
    'Name': ['Alice', 'Bob', 'Charlie'],
    'Age': [25, 30, 35],
    'City': ['New York', 'London', 'Paris']
})

def df_to_sortable_table(df, sort_column=None, sort_order='asc'):
    # Convert DataFrame to HTML
    html_table = df.to_html(index=False, classes=['table'])
    
    # Parse the HTML table
    soup = BeautifulSoup(html_table, 'html.parser')
    
    # Add HTMX attributes to the header cells
    for th in soup.find_all('th'):
        column = th.text
        th['hx-get'] = f'/sort_table?column={column}&order={"desc" if column == sort_column and sort_order == "asc" else "asc"}'
        th['hx-target'] = '#table-container'
        th['hx-swap'] = 'innerHTML'
        
        # Add sorting indicator
        if column == sort_column:
            th.string = f'{column} {"▲" if sort_order == "asc" else "▼"}'
    
    # Wrap the table in a div with an id for targeting
    table_html = str(soup)
    return Div(NotStr(table_html), id='table-container')

@rt('/')
def get():
    return Titled("Sortable Table", df_to_sortable_table(df))

@rt('/sort_table')
def get(column: str, order: str):
    global df
    df_sorted = df.sort_values(by=column, ascending=(order == 'asc'))
    return df_to_sortable_table(df_sorted, sort_column=column, sort_order=order)

serve()