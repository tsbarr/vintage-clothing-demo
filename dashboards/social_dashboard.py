import dash
from dash import dcc, html, Input, Output, Dash, dash_table
import plotly.express as px
import pandas as pd
import psycopg2
import warnings
warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
# Since this script is in dashboards directory, find parent directory to access shared config files
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import shared configuration from main directory
from config import load_config

# Initialize app
app = dash.Dash(__name__)

# Function to connect to db and get data to display
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

# App layout
app.layout = html.Div([
    html.H1("Social Media Analytics - Vintage Clothing Demo"),
    # 1
    
    html.H2("Performance Summary"),
    html.Div(id='summary-cards', style={'display': 'flex', 'gap': '20px', 'margin': '20px 0'}),
    # 2
    html.Hr(),
    html.H2("Viral Content Detection"),
    
    
    # Add a graph component
    dcc.Graph(id='engagement-scatter'),
    
    # Add a dropdown for filtering
    html.Label("Platform:"),
    dcc.Dropdown(
        id='platform-filter',
        options=[
            {'label': 'All Platforms', 'value': 'all'},
            {'label': 'Instagram', 'value': 'instagram'},
            {'label': 'TikTok', 'value': 'tiktok'}
        ],
        value='all'
    ),
    # 2
    html.Hr(),
    html.H2("Clientbase Building Analysis"),
    dcc.Graph(id='clientbase-metrics'),

    html.Label("Metric to Analyze:"),
    dcc.Dropdown(
        id='metric-selector',
        options=[
            {'label': 'Save Rate (Future Customers)', 'value': 'saves'},
            {'label': 'Comment Engagement', 'value': 'comments'},
            {'label': 'Share Potential', 'value': 'shares'}
        ],
        value='saves'
    )
    
    
    ])

@app.callback(
    Output('engagement-scatter', 'figure'),
    Input('platform-filter', 'value')
)
def update_engagement_scatter(selected_platform):
    df = get_data()  # Get your data
    
    # Filter by platform if not 'all'
    if selected_platform != 'all':
        df = df[df['platform'] == selected_platform]
    
    # Create scatter plot
    fig = px.scatter(
        df, 
        x='impressions', 
        y='engagement_rate',
        color='platform',
        size='saves',
        title='Engagement Rate vs Impressions (Viral Content Detection)')
    return fig

@app.callback(
    Output('clientbase-metrics', 'figure'),
    Input('metric-selector', 'value')
)
def update_clientbase_graph(selected_metric):
    df = get_data()
    
    # Create different visualizations based on selected metric
    if selected_metric == 'saves':
        # Show save rate vs impressions (people bookmarking = future clients)
        fig = px.bar(
            df, 
            x='post_id', 
            y='saves',
            color='platform',
            title='Save Rate Analysis (Future Client Interest)')
    elif selected_metric == 'comments':
        # Show comment engagement over time
        fig = px.line(
            df, 
            x='posted_date', 
            y='comments',
            color='platform',
            title='Comment Engagement Over Time')
    else:  # shares
        # Show sharing potential
        fig = px.scatter(
            df,
            x='impressions',
            y='shares', 
            color='platform',
            size='engagement_rate',
            title='Share Potential Analysis')
    
    return fig

@app.callback(
    Output('summary-cards', 'children'),
    Input('platform-filter', 'value')  # Updates when platform filter changes
)
def update_summary_cards(selected_platform):
    df = get_data()
    
    # Filter by platform if not 'all'
    if selected_platform != 'all':
        df = df[df['platform'] == selected_platform]
    
    # Calculate key metrics
    total_posts = len(df)
    avg_engagement = df['engagement_rate'].mean()
    total_impressions = df['impressions'].sum()
    viral_posts = len(df[df['engagement_rate'] > 0.10])  # >10% engagement
    
    # Create summary cards
    cards = [
        html.Div([
            html.H3(f"{total_posts:,}", style={'margin': '0', 'color': '#1f77b4'}),
            html.P("Total Posts", style={'margin': '0'})
        ], style={'textAlign': 'center', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
        
        html.Div([
            html.H3(f"{avg_engagement:.1%}", style={'margin': '0', 'color': '#ff7f0e'}),
            html.P("Avg Engagement", style={'margin': '0'})
        ], style={'textAlign': 'center', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
        
        html.Div([
            html.H3(f"{total_impressions:,}", style={'margin': '0', 'color': '#2ca02c'}),
            html.P("Total Impressions", style={'margin': '0'})
        ], style={'textAlign': 'center', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px'}),
        
        html.Div([
            html.H3(f"{viral_posts}", style={'margin': '0', 'color': '#d62728'}),
            html.P("Viral Posts (>10%)", style={'margin': '0'})
        ], style={'textAlign': 'center', 'padding': '20px', 'border': '1px solid #ddd', 'borderRadius': '5px'})
    ]
    
    return cards

if __name__ == '__main__':
    app.run_server(debug=True)
