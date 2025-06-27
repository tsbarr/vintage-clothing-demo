import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import psycopg2
# Since this script is in sync directory, go back one in sys path to access shared config files
import sys
sys.path.append('..')
# Import shared configuration from main directory
from config import load_config

app = dash.Dash(__name__)

# Database connection function
def get_data():
    # database connection code here
    pass

# Basic layout
app.layout = html.Div([
    html.H1("Social Media Analytics"),
    # add components here
])

if __name__ == '__main__':
    app.run_server(debug=True)
