import json
import os
from datetime import datetime, timedelta

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from dash import Input, Output, callback, dcc, html
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# Database configuration
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://ai_platform_user:your_password@postgres:5432/ai_platform_db",
)

# Initialize Dash app with dark Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "ARM Edge AI Platform - Vector Space Visualization"

# Custom CSS for dropdown text fix
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Fix dropdown visibility */
            .Select-menu-outer {
                background-color: #343a40 !important;
                border: 1px solid #495057 !important;
            }
            .Select-option {
                background-color: #343a40 !important;
                color: #fff !important;
            }
            .Select-option:hover, .Select-option.is-focused {
                background-color: #495057 !important;
                color: #fff !important;
            }
            .dropdown-menu {
                background-color: #343a40 !important;
            }
            .dropdown-item {
                color: #fff !important;
            }
            .dropdown-item:hover {
                background-color: #495057 !important;
                color: #fff !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


def get_vector_data():
    """Fetch vector analytics data from PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)

        # Get vector analytics with metrics
        query = """
        SELECT 
            va.id,
            va.vector_id,
            va.timestamp,
            va.analytics_type,
            va.metrics,
            va.decisions
        FROM vector_analytics va
        WHERE va.timestamp > NOW() - INTERVAL '24 hours'
        ORDER BY va.timestamp DESC
        LIMIT 1000
        """

        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return pd.DataFrame()

        # Parse JSON metrics and decisions
        df["metrics_parsed"] = df["metrics"].apply(json.loads)
        df["decisions_parsed"] = df["decisions"].apply(json.loads)

        # Extract key metrics
        df["magnitude"] = df["metrics_parsed"].apply(lambda x: x.get("magnitude", 0))
        df["entropy"] = df["metrics_parsed"].apply(lambda x: x.get("entropy", 0))
        df["anomaly_score"] = df["metrics_parsed"].apply(
            lambda x: x.get("anomaly_score", 0)
        )
        df["should_store"] = df["decisions_parsed"].apply(
            lambda x: x.get("should_store", False)
        )
        df["is_duplicate"] = df["decisions_parsed"].apply(
            lambda x: x.get("is_duplicate", False)
        )

        return df

    except Exception as e:
        print(f"Database error: {e}")
        return pd.DataFrame()


def generate_sample_3d_data(df):
    """Generate sample 3D coordinates from vector metrics"""
    if df.empty:
        # Generate sample data for demo
        n_points = 100
        np.random.seed(42)

        sample_df = pd.DataFrame(
            {
                "x": np.random.randn(n_points),
                "y": np.random.randn(n_points),
                "z": np.random.randn(n_points),
                "magnitude": np.random.uniform(0.1, 2.0, n_points),
                "entropy": np.random.uniform(0, 5, n_points),
                "anomaly_score": np.random.uniform(0, 1, n_points),
                "should_store": np.random.choice([True, False], n_points),
                "is_duplicate": np.random.choice([True, False], n_points, p=[0.1, 0.9]),
                "timestamp": pd.date_range(
                    start="2025-06-17", periods=n_points, freq="5min"
                ),
            }
        )
        return sample_df

    # Use PCA to reduce metrics to 3D space for visualization
    metrics_cols = ["magnitude", "entropy", "anomaly_score"]
    available_cols = [col for col in metrics_cols if col in df.columns]

    if len(available_cols) >= 2:
        # Create feature matrix
        X = df[available_cols].fillna(0)

        if len(available_cols) == 2:
            # Add a third dimension
            X = np.column_stack([X, np.random.randn(len(X)) * 0.1])
        elif len(available_cols) > 3:
            # Reduce to 3D with PCA
            pca = PCA(n_components=3)
            X = pca.fit_transform(X)

        df_3d = df.copy()
        df_3d["x"] = X[:, 0]
        df_3d["y"] = X[:, 1] if X.shape[1] > 1 else np.random.randn(len(X)) * 0.1
        df_3d["z"] = X[:, 2] if X.shape[1] > 2 else np.random.randn(len(X)) * 0.1

        return df_3d
    else:
        # Fallback to random data
        df_3d = df.copy()
        df_3d["x"] = np.random.randn(len(df))
        df_3d["y"] = np.random.randn(len(df))
        df_3d["z"] = np.random.randn(len(df))
        return df_3d


# App layout
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3(
                            "Claude OS - Vector Space Visualization",
                            className="text-center mb-2",
                        ),  # Menší nadpis
                        html.Hr(),
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4("Controls", className="card-title"),
                                        html.Label("Color By:"),
                                        dcc.Dropdown(
                                            id="color-dropdown",
                                            options=[
                                                {
                                                    "label": "Magnitude",
                                                    "value": "magnitude",
                                                },
                                                {
                                                    "label": "Entropy",
                                                    "value": "entropy",
                                                },
                                                {
                                                    "label": "Anomaly Score",
                                                    "value": "anomaly_score",
                                                },
                                                {
                                                    "label": "Should Store",
                                                    "value": "should_store",
                                                },
                                                {
                                                    "label": "Is Duplicate",
                                                    "value": "is_duplicate",
                                                },
                                            ],
                                            value="magnitude",
                                            className="mb-3",
                                        ),
                                        html.Label("Size By:"),
                                        dcc.Dropdown(
                                            id="size-dropdown",
                                            options=[
                                                {
                                                    "label": "Magnitude",
                                                    "value": "magnitude",
                                                },
                                                {
                                                    "label": "Entropy",
                                                    "value": "entropy",
                                                },
                                                {
                                                    "label": "Anomaly Score",
                                                    "value": "anomaly_score",
                                                },
                                            ],
                                            value="magnitude",
                                            className="mb-3",
                                        ),
                                        html.Label("Filter by Analytics Type:"),
                                        dcc.Dropdown(
                                            id="type-filter",
                                            options=[
                                                {"label": "All", "value": "all"},
                                                {
                                                    "label": "Pre Storage",
                                                    "value": "pre_storage",
                                                },
                                                {
                                                    "label": "Post Storage",
                                                    "value": "post_storage",
                                                },
                                            ],
                                            value="all",
                                            className="mb-3",
                                        ),
                                        dbc.Button(
                                            "Refresh Data",
                                            id="refresh-btn",
                                            color="primary",
                                            className="w-100",
                                        ),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=2,
                ),  # Zmenšený sidebar
                dbc.Col(
                    [dcc.Graph(id="3d-scatter", style={"height": "500px"})], width=10
                ),  # Menší graf  # Větší graf
            ]
        ),
        dbc.Row([dbc.Col([html.Div(id="stats-cards", className="mt-4")])]),
        # Auto-refresh interval
        dcc.Interval(
            id="interval-component", interval=30 * 1000, n_intervals=0
        ),  # Update every 30 seconds
    ],
    fluid=True,
)


@callback(
    [Output("3d-scatter", "figure"), Output("stats-cards", "children")],
    [
        Input("color-dropdown", "value"),
        Input("size-dropdown", "value"),
        Input("type-filter", "value"),
        Input("refresh-btn", "n_clicks"),
        Input("interval-component", "n_intervals"),
    ],
)
def update_3d_plot(color_by, size_by, type_filter, refresh_clicks, n_intervals):
    """Update the 3D scatter plot"""

    # Get fresh data
    df = get_vector_data()
    df_3d = generate_sample_3d_data(df)

    if df_3d.empty:
        # Empty plot
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        stats = html.Div("No data to display")
        return fig, stats

    # Filter by analytics type
    if type_filter != "all" and "analytics_type" in df_3d.columns:
        df_3d = df_3d[df_3d["analytics_type"] == type_filter]

    if df_3d.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data matches filter", x=0.5, y=0.5, showarrow=False)
        stats = html.Div("No data matches current filter")
        return fig, stats

    # Prepare color and size arrays
    color_values = df_3d[color_by] if color_by in df_3d.columns else df_3d["magnitude"]
    size_values = df_3d[size_by] if size_by in df_3d.columns else df_3d["magnitude"]

    # Normalize size values
    size_normalized = (size_values - size_values.min()) / (
        size_values.max() - size_values.min() + 1e-6
    ) * 20 + 5

    # Create hover text
    hover_text = []
    for i, row in df_3d.iterrows():
        hover_info = f"Vector ID: {row.get('vector_id', 'N/A')}<br>"
        hover_info += f"Timestamp: {row.get('timestamp', 'N/A')}<br>"
        hover_info += f"Magnitude: {row.get('magnitude', 0):.3f}<br>"
        hover_info += f"Entropy: {row.get('entropy', 0):.3f}<br>"
        hover_info += f"Anomaly Score: {row.get('anomaly_score', 0):.3f}<br>"
        hover_info += f"Should Store: {row.get('should_store', False)}<br>"
        hover_info += f"Is Duplicate: {row.get('is_duplicate', False)}"
        hover_text.append(hover_info)

    # Create 3D scatter plot
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=df_3d["x"],
                y=df_3d["y"],
                z=df_3d["z"],
                mode="markers",
                marker=dict(
                    size=size_normalized,
                    color=color_values,
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title=color_by.replace("_", " ").title()),
                    opacity=0.8,
                ),
                text=hover_text,
                hovertemplate="%{text}<extra></extra>",
                name="Vectors",
            )
        ]
    )

    # Update layout
    fig.update_layout(
        title=f"Vector Space - Colored by {color_by.replace('_', ' ').title()}",
        scene=dict(
            xaxis=dict(
                showgrid=False,  # Vypnout grid
                showbackground=False,  # Vypnout pozadí
                showticklabels=False,  # Vypnout čísla
                showline=False,  # Vypnout axis line
                zeroline=False,  # Vypnout zero line
                title="",  # Vypnout title
                visible=False,  # Úplně skrýt osu
            ),
            yaxis=dict(
                showgrid=False,
                showbackground=False,
                showticklabels=False,
                showline=False,
                zeroline=False,
                title="",
                visible=False,
            ),
            zaxis=dict(
                showgrid=False,
                showbackground=False,
                showticklabels=False,
                showline=False,
                zeroline=False,
                title="",
                visible=False,
            ),
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        ),
        margin=dict(l=0, r=0, t=40, b=0),  # Menší marginy
        height=500,
        template="plotly_dark",  # Dark theme pro graf
        paper_bgcolor="rgba(0,0,0,0)",  # Transparentní pozadí
        plot_bgcolor="rgba(0,0,0,0)",  # Transparentní plot area
    )

    # Generate statistics cards
    stats_cards = []

    if not df_3d.empty:
        total_vectors = len(df_3d)
        stored_vectors = (
            df_3d["should_store"].sum() if "should_store" in df_3d.columns else 0
        )
        duplicates = (
            df_3d["is_duplicate"].sum() if "is_duplicate" in df_3d.columns else 0
        )
        avg_magnitude = df_3d["magnitude"].mean() if "magnitude" in df_3d.columns else 0

        stats_cards = dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            f"{total_vectors}", className="text-primary"
                                        ),
                                        html.P("Total Vectors", className="mb-0"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            f"{stored_vectors}",
                                            className="text-success",
                                        ),
                                        html.P("Stored Vectors", className="mb-0"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            f"{duplicates}", className="text-warning"
                                        ),
                                        html.P("Duplicates", className="mb-0"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            f"{avg_magnitude:.3f}",
                                            className="text-info",
                                        ),
                                        html.P("Avg Magnitude", className="mb-0"),
                                    ]
                                )
                            ]
                        )
                    ],
                    width=3,
                ),
            ]
        )

    return fig, stats_cards


@app.server.route("/health")
def health_check():
    return {"status": "healthy", "service": "plotly-viz"}


if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=8003, debug=False)
