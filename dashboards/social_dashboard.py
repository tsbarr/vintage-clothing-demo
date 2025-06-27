import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine
# find parent directory to access shared config files
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import shared configuration from main directory
from config import load_config

# Initialize app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Function to connect to db and get data to display
def get_data():
    try:
        config = load_config()
        # Create SQLAlchemy connection engine
        engine = create_engine(config.database.connection_string)
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
        df = pd.read_sql_query(sql_text, engine)
        
        return df


    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

# # App layout

app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H1("Social Media Analytics", className="text-center mb-4"),
            html.H4("Vintage Clothing Demo", className="text-center text-muted mb-4")
        ])
    ]),
    # Filters
    dbc.Row([
        dbc.Col([
            dbc.Label("Platform Filter:", className="fw-bold"),
            dcc.Dropdown(
                id='platform-filter',
                options=[
                    {'label': 'All Platforms', 'value': 'all'},
                    {'label': 'Instagram', 'value': 'instagram'},
                    {'label': 'TikTok', 'value': 'tiktok'}
                ],
                value='all',
                className="mb-3"
            )
        ], width=6)
    ]),
    
    # Performance Summary Cards
    dbc.Row([
        dbc.Col([
            html.H3("Performance Summary", className="mb-3"),
            html.Div(id='summary-cards')
        ])
    ], className="mb-4"),
    
    
    
    # Main Charts
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Viral Content Detection", className="mb-0")),
                dbc.CardBody([
                    dcc.Graph(id='engagement-scatter')
                ])
            ])
        ])
    ], className="mb-4"),
    
    # Second row of analysis
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H4("Clientbase Building Analysis", className="mb-0")),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Metric to Analyze:", className="fw-bold"),
                            dcc.Dropdown(
                                id='metric-selector',
                                options=[
                                    {'label': 'Save Rate (Future Clients)', 'value': 'saves'},
                                    {'label': 'Comment Engagement', 'value': 'comments'},
                                    {'label': 'Share Potential', 'value': 'shares'}
                                ],
                                value='saves',
                                className="mb-3"
                            )
                        ], width=6)
                    ]),
                    dcc.Graph(id='clientbase-metrics')
                ])
            ])
        ])
    ])
], fluid=True, className="p-4")

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
        dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.H2(f"{total_posts:,}", className="text-primary mb-0"),
                html.P("Total Posts", className="text-muted mb-0")
            ])
        ], className="text-center")
    ], width=3),
    
    dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.H2(f"{avg_engagement:.1%}", className="text-warning mb-0"),
                html.P("Avg Engagement", className="text-muted mb-0")
            ])
        ], className="text-center")
    ], width=3),
    dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.H2(f"{total_impressions:,}", className="text-success mb-0"),
                html.P("Total Impressions", className="text-muted mb-0")
            ])
        ], className="text-center")
    ], width=3),
    
    dbc.Col([
        dbc.Card([
            dbc.CardBody([
                html.H2(f"{viral_posts:,}", className="text-danger mb-0"),
                html.P("Viral Posts (>10%)", className="text-muted mb-0")
            ])
        ], className="text-center")
    ], width=3)
    ]
    
    return dbc.Row(cards)

if __name__ == '__main__':
    app.run(debug=True)
