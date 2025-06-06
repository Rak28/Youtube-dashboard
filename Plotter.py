import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# --- Interactive Plotting with Plotly ---
def plot_daily_video_watch_time_by_type(df, label):
    daily_watch_time = df.groupby(['date', 'video_type'])['watch_time_hours'].sum().unstack(fill_value=0)

    # Sort by date index
    daily_watch_time = daily_watch_time.sort_index()

    # Make sure 'Short' and 'Long' columns exist
    for col in ['Short', 'Long']:
        if col not in daily_watch_time.columns:
            daily_watch_time[col] = 0

    # Fill any missing values
    daily_watch_time = daily_watch_time.fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_watch_time.index,
        y=daily_watch_time['Short'],
        mode='lines',
        stackgroup='one',
        name='Shorts',
        line=dict(color='orange')
    ))
    fig.add_trace(go.Scatter(
        x=daily_watch_time.index,
        y=daily_watch_time['Long'],
        mode='lines',
        stackgroup='one',
        name='Longs',
        line=dict(color='blue')
    ))

    fig.update_layout(
        title=f"Daily Watch Time (Interactive Stacked Area) - {label}",
        xaxis_title="Date",
        yaxis_title="Hours Watched",
        hovermode='x unified',
        legend_title_text='Video Type',
        template='plotly_dark',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_daily_video_watch_count_by_type(df, label):
    daily_counts = df.groupby(['date', 'video_type']).size().unstack(fill_value=0)

    # Ensure columns for 'Short' and 'Long' exist
    if 'Short' not in daily_counts.columns:
        daily_counts['Short'] = 0
    if 'Long' not in daily_counts.columns:
        daily_counts['Long'] = 0

    daily_counts = daily_counts.sort_index()

    # Prepare figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_counts.index,
        y=daily_counts['Short'],
        mode='lines',
        name='Shorts',
        line=dict(color='orange')
    ))
    fig.add_trace(go.Scatter(
        x=daily_counts.index,
        y=daily_counts['Long'],
        mode='lines',
        name='Longs',
        line=dict(color='blue')
    ))

    fig.update_layout(
        title=f'📊 Daily Video Watch Count by Type - {label}',
        xaxis_title='Date',
        yaxis_title='Number of Videos Watched',
        template='plotly_dark',
        hovermode='x unified',
        legend_title_text='Video Type',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_top_channels_clicked(df, label, top_n=15):
    top_channels = df['channel'].value_counts().head(top_n)
    top_channels_df = top_channels.reset_index()
    top_channels_df.columns = ['channel', 'count']
    fig = px.bar(
        top_channels_df,
        x='count',
        y='channel',
        orientation='h',
        labels={'count': 'Watch Count', 'channel': 'Channel'},
        title=f"📺 Top {top_n} most clicked channels - {label}",
        color="count",
        template='plotly_dark'
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

def plot_top_channels_watched(df, label, top_n=10):
    top_channels = (
        df.groupby('channel')['watch_time_hours']
        .sum()
        .nlargest(top_n)
        .sort_values(ascending=True)  # To invert the bar order
        .reset_index()
    )

    fig = px.bar(
        top_channels,
        x='watch_time_hours',
        y='channel',
        orientation='h',
        color='watch_time_hours',
        title=f"📺 Top {top_n} most watched channels - {label}",
        labels={'watch_time_hours': 'Watch Hours', 'channel': 'Channel'},
        template='plotly_dark'
    )
    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def plot_youtube_usage_trend_interactive(df):
    df['date'] = df['timestamp'].dt.date
    trend = df.groupby('date').size().reset_index(name='count')
    fig = px.line(trend, x='date', y='count',
                  title='Daily YouTube Watch Count',
                  labels={'count': 'Video Count', 'date': 'Date'},
                  template='plotly_dark', height=400)
    st.plotly_chart(fig, use_container_width=True)

def plot_top_youtube_queries_interactive(df, top_n=20):
    top_queries = df['query'].value_counts().head(top_n)
    fig = px.bar(
        x=top_queries.values,
        y=top_queries.index,
        orientation='h',
        labels={'x': 'Search Count', 'y': 'Query'},
        title=f"Top {top_n} YouTube Search Queries",
        color=top_queries.values,
        color_continuous_scale='RdBu',
        template='plotly_dark',
        height=450
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

def plot_top_videos_clicked(df, label, top_n=10):
    watched_videos = df['video_title'].value_counts().head(top_n)
    fig = px.bar(
        x=watched_videos.values,
        y=watched_videos.index,
        orientation='h',
        labels={'x': 'Watch Count', 'y': 'Video Title'},
        title=f"Top {top_n} most clicked videos - {label}",
        color=watched_videos.values,
        color_continuous_scale='Plasma',
        template='plotly_dark',
        height=450
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

def plot_top_videos_watched(df, label, top_n=10):
    # Get top N videos
    top_videos = (
        df.groupby('video_title')['watch_time_hours']
        .sum()
        .nlargest(top_n)
        .reset_index()
    )
    fig = px.bar(
        top_videos,
        x='watch_time_hours',
        y='video_title',
        color='watch_time_hours',
        orientation='h',
        title=f"🎬 Top {top_n} most watched videos - {label}",
        labels={'watch_time_hours': 'Watch Hours', 'video_title': 'Video'},
        template='plotly_dark'
    )
    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def plot_search_intensity_gauge(search_df, watch_df):
    ratio = len(search_df) / max(len(watch_df), 1)
    percent = ratio * 100

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=percent,
        title={'text': "🔍 Search Intensity"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "purple"},
            'steps': [
                {'range': [0, 25], 'color': "gray"},
                {'range': [25, 50], 'color': "orange"},
                {'range': [50, 100], 'color': "green"}
            ]
        }
    ))
    return fig

def compare_search_watch_trends_interactive(search_df, watch_df):
    search_df['date'] = search_df['timestamp'].dt.date
    watch_df['date'] = watch_df['timestamp'].dt.date
    search_counts = search_df.groupby('date').size()
    watch_counts = watch_df.groupby('date').size()
    combined = pd.DataFrame({
        'Searches': search_counts,
        'Watched': watch_counts
    }).fillna(0).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=combined['date'], y=combined['Searches'], mode='lines+markers', name='Searches', line=dict(color='lightgreen')))
    fig.add_trace(go.Scatter(x=combined['date'], y=combined['Watched'], mode='lines+markers', name='Watched', line=dict(color='red')))
    fig.update_layout(
        title="YouTube Search vs Watch Activity Over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        template='plotly_dark',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_search_temporal_patterns_interactive(df):
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.day_name()
    pivot = pd.pivot_table(df, index='day', columns='hour', aggfunc='size', fill_value=0) # type: ignore
    ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex(ordered_days)

    fig = px.imshow(
        pivot.values,
        labels=dict(x="Hour of Day", y="Day of Week", color="Search Count"),
        x=list(pivot.columns),
        y=ordered_days,
        color_continuous_scale='Inferno',
        aspect="auto",
        title="YouTube Searches by Hour and Day",
        template='plotly_dark',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_weekend_vs_weekday(df):
    df['day_of_week'] = df['timestamp'].dt.day_name()
    df['is_weekend'] = df['day_of_week'].isin(['Saturday', 'Sunday'])
    # df['watch_time_hours'] = df['watch_time'] / 3600

    agg = df.groupby(['is_weekend', 'video_type'])['watch_time_hours'].sum().unstack().fillna(0)
    agg.index = ['Weekday', 'Weekend']

    fig = px.bar(agg, barmode='group', title="📅 Weekend vs Weekday Watching",
                labels={'value': 'Watch Hours', 'is_weekend': 'Day Type'},
                text_auto=True)
    return fig

