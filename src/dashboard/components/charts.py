from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_health_gauge(score: float) -> go.Figure:
    """Builds an enterprise gauge chart for the Composite Data Health Score."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            domain={"x": [0, 1], "y": [0, 1]},
            number={"suffix": "%", "font": {"size": 36, "color": "#f8fafc"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8"},
                "bar": {"color": "#3b82f6", "thickness": 0.3},
                "bgcolor": "#1e293b",
                "borderwidth": 1,
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, 80], "color": "rgba(239, 68, 68, 0.2)"},
                    {"range": [80, 95], "color": "rgba(245, 158, 11, 0.2)"},
                    {"range": [95, 100], "color": "rgba(16, 185, 129, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": "#10b981", "width": 4},
                    "thickness": 0.75,
                    "value": 95,
                },
            },
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94a3b8", "family": "Inter, sans-serif"},
        margin=dict(l=20, r=20, t=30, b=20),
        height=220,
    )
    return fig


def render_dimensions_radar(dimensions: Dict[str, float]) -> go.Figure:
    """Radar chart showing 5 dimensions: Completeness, Validity, Uniqueness, Timeliness, Consistency."""
    categories = list(dimensions.keys())
    values = list(dimensions.values())

    # Close the radar polygon
    categories.append(categories[0])
    values.append(values[0])

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            fillcolor="rgba(59, 130, 246, 0.25)",
            line=dict(color="#3b82f6", width=2),
            marker=dict(size=6, color="#60a5fa"),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10, color="#64748b"),
                gridcolor="#334155",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="#cbd5e1", family="Inter"),
                gridcolor="#334155",
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=30),
        height=260,
        showlegend=False,
    )
    return fig


def render_trend_chart(metrics: List[Dict[str, Any]]) -> go.Figure:
    """Time-series chart showing Health Score and Quarantined Record count trend."""
    if not metrics:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="No batch history available",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#64748b"),
                )
            ],
        )
        return fig

    df = pd.DataFrame(metrics)
    if "executed_at" in df.columns:
        df["executed_at"] = pd.to_datetime(df["executed_at"])
        df = df.sort_values("executed_at")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["batch_id"],
            y=df["overall_health_score"],
            name="Health Score (%)",
            mode="lines+markers",
            line=dict(color="#10b981", width=3),
            marker=dict(size=7),
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["batch_id"],
            y=df["quarantined_records"],
            name="Quarantined Records",
            marker_color="rgba(239, 68, 68, 0.6)",
            yaxis="y2",
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94a3b8"},
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(gridcolor="#1e293b", title="Batch Identifier"),
        yaxis=dict(
            title="Health Score (%)",
            range=[0, 105],
            gridcolor="#1e293b",
            side="left",
        ),
        yaxis2=dict(
            title="Quarantined Count",
            side="right",
            overlaying="y",
            showgrid=False,
        ),
        margin=dict(l=40, r=40, t=30, b=40),
        height=320,
    )
    return fig


def render_violations_bar(violations: Dict[str, int]) -> go.Figure:
    """Horizontal bar chart of top rule violation categories."""
    if not violations:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text="Zero Violations Recorded",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#10b981"),
                )
            ],
        )
        return fig

    items = sorted(violations.items(), key=lambda x: x[1], reverse=True)
    df = pd.DataFrame(items, columns=["Violation Type", "Count"])

    fig = px.bar(
        df,
        x="Count",
        y="Violation Type",
        orientation="h",
        color="Count",
        color_continuous_scale="Reds",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#94a3b8"},
        coloraxis_showscale=False,
        yaxis=dict(autorange="reversed", gridcolor="#1e293b"),
        xaxis=dict(gridcolor="#1e293b"),
        margin=dict(l=20, r=20, t=20, b=20),
        height=260,
    )
    return fig
