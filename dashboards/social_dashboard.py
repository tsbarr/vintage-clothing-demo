import dash
from dash import dcc, html, Input, Output, Dash, dash_table
import plotly.express as px
import pandas as pd
import psycopg2
# Since this script is in dashboards directory, find parent directory to access shared config files
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import shared configuration from main directory
from config import load_config

app = dash.Dash(__name__)

# Database connection function
def get_data():
    try:
        config = load_config()
        # Connect to the database
        conn = psycopg2.connect(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.user,
            password=config.database.password
        )
        # Query to get data
        sql_text = '''
            SELECT 
                p.post_id,
                p.posted_date,
                p.post_type,
                p.is_promotional,
                m.impressions,
                m.reach,
                m.likes,
                m.comments,
                m.shares,
                m.saves,
                m.engagement_rate,
                a.platform
            FROM social_media_posts p
            JOIN social_media_metrics m ON p.post_id = m.post_id
            JOIN social_media_accounts a ON p.account_id = a.account_id
            ORDER BY p.posted_date DESC
        '''
        df = pd.read_sql_query(sql_text, conn)
        conn.close()
        return df


    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

# get df
df = get_data()

# Initialize the app
app = Dash()


# Basic layout
app.layout = html.Div([
    html.H1("Social Media Analytics"),
    dash_table.DataTable(data=df.to_dict('records'), page_size=10)
])

if __name__ == '__main__':
    app.run_server(debug=True)
