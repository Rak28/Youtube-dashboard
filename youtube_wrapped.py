import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from wordcloud import WordCloud

def load_youtube_watch_history(data):
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     data = json.load(f)
    df = pd.read_json(data)
    df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
    df['video_title'] = df['title'].astype(str)
    df['video_title'] = df['video_title'].str.extract(r'Watched(.*)')
    df['channel'] = df['subtitles'].apply(lambda x: x[0]['name'] if isinstance(x, list) and 'name' in x[0] else None)
    df['url'] = df['titleUrl']
    df=df[df.details.isna()]
    return df[['timestamp', 'video_title', 'channel', 'url']]

def load_youtube_search_history(data):
    df=pd.read_json(data)
    # df = pd.json_normalize(data)
    df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
    df['query'] = df['title'].str.extract(r'Searched for (.*)')
    return df[['timestamp', 'query']].dropna()

# --- PREPROCESSING FUNCTIONS ---
def classify_videos(df, threshold_seconds=90):
    # df = flag_likely_shorts_by_title(df)
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['time_diff'] = df['timestamp'].diff().dt.total_seconds().fillna(9999)

    short_gaps = df['time_diff'] <= threshold_seconds
    cluster_id = (short_gaps == False).cumsum()
    cluster_sizes = cluster_id.map(cluster_id.value_counts())
    df['rapid_flag'] = cluster_sizes >= 2

    # Combine flags: consider video Short if either condition met
    df['video_type'] = 'Long'
    df.loc[df['rapid_flag'], 'video_type'] = 'Short'
    return df

def estimate_watch_time_hours(df, short_duration_min=1, max_long_duration_min=20, default_long_duration_min=5):
    df = df.sort_values('timestamp').reset_index(drop=True)

    # Time until next video
    df['time_to_next'] = df['timestamp'].shift(-1) - df['timestamp']
    df['time_to_next_sec'] = df['time_to_next'].dt.total_seconds()

    # Classify Shorts vs Long
    df = classify_videos(df)  # this should add a 'video_type' column

    # Estimate watch time in seconds
    def compute_watch_time(row):
        if row['video_type'] == 'Short':
            return short_duration_min * 60
        elif pd.isna(row['time_to_next_sec']) or row['time_to_next_sec'] > max_long_duration_min * 60:
            return default_long_duration_min * 60
        else:
            return row['time_to_next_sec']

    df['watch_time_sec'] = df.apply(compute_watch_time, axis=1)
    df['watch_time_hours'] = df['watch_time_sec'] / 3600
    df['date'] = df['timestamp'].dt.date

    # Summarize by day and type
    daily_watch_time = df.groupby(['date', 'video_type'])['watch_time_hours'].sum().unstack(fill_value=0)

    # Ensure both video types exist
    if 'Short' not in daily_watch_time.columns:
        daily_watch_time['Short'] = 0
    if 'Long' not in daily_watch_time.columns:
        daily_watch_time['Long'] = 0

    return df

# --- ANALYTICS FUNCTIONS ---
def top_10_videos(df):
    return df.groupby('video_title')['watch_time_hours'].sum().sort_values(ascending=False).head(10)

def active_day_hour(df):
    df['weekday'] = df['timestamp'].dt.day_name()
    df['hour'] = df['timestamp'].dt.hour
    return df.groupby('weekday')['watch_time_hours'].sum(), df.groupby('hour')['watch_time_hours'].sum()

def binge_session(df):
    df = df.sort_values('timestamp').copy()
    df['gap_min'] = df['timestamp'].diff().dt.total_seconds().div(60).fillna(0)
    df['session_id'] = (df['gap_min'] > 10).cumsum()
    sessions = df.groupby('session_id').agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max'),
        video_count=('video_title', 'count'),
        total_hours=('watch_time_hours', 'sum')
    )
    return sessions.sort_values('total_hours', ascending=False).iloc[0]

def watch_type_totals(df):
    return df.groupby('video_type')['watch_time_hours'].sum()

# --- Interactive Plotting with Plotly ---
def plot_watch_time_interactive(daily_watch_time):
    daily_watch_time = daily_watch_time.sort_index()
    if 'Short' not in daily_watch_time.columns:
        daily_watch_time['Short'] = 0
    if 'Long' not in daily_watch_time.columns:
        daily_watch_time['Long'] = 0
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
        title="Daily Watch Time (Interactive Stacked Area)",
        xaxis_title="Date",
        yaxis_title="Hours Watched",
        hovermode='x unified',
        legend_title_text='Video Type',
        template='plotly_dark',
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

def plot_top_channels_interactive(df, top_n=15):
    top_channels = df['channel'].value_counts().head(top_n)
    fig = px.bar(
        x=top_channels.values,
        y=top_channels.index,
        orientation='h',
        labels={'x': 'Watch Count', 'y': 'Channel'},
        title=f"Top {top_n} Most Watched YouTube Channels",
        color=top_channels.values,
        color_continuous_scale='Viridis',
        template='plotly_dark',
        height=450
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
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

def plot_most_watched_video_interactive(df, top_n=20):
    watched_videos = df['video_title'].value_counts().head(top_n)
    fig = px.bar(
        x=watched_videos.values,
        y=watched_videos.index,
        orientation='h',
        labels={'x': 'Watch Count', 'y': 'Video Title'},
        title=f"Top {top_n} Most Watched YouTube Videos",
        color=watched_videos.values,
        color_continuous_scale='Plasma',
        template='plotly_dark',
        height=450
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

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

# --- Streamlit APP ---

st.set_page_config(page_title="YouTube Wrapped Dashboard", layout="wide", page_icon="📺")

st.title("📊 YouTube Wrapped Dashboard")

# Add a fun emoji mood selector for user engagement
st.sidebar.header("Your YouTube Mood Today")
mood = st.sidebar.selectbox("How do you feel about your YouTube watching habits?", 
                            options=["🎉 Loving it!", "🤔 Could be better", "😴 Too much binge", "🚀 On fire!", "😱 OMG!"])

st.sidebar.header("📁 Upload Your Files")
uploaded_file_watch = st.sidebar.file_uploader("Upload your `watch-history.json`", type="json")
uploaded_file_search = st.sidebar.file_uploader("Upload your `search-history.json`", type="json")

if uploaded_file_watch:
    watch_df = load_youtube_watch_history(uploaded_file_watch)
    watch_df['year'] = watch_df['timestamp'].dt.year
    min_year, max_year = int(watch_df['year'].min()), int(watch_df['year'].max())

    # with st.sidebar.expander("🔍 Filters"):
    year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year), 1)
        # video_tabs = st.tabs(["📺 All Videos", "⏱️ Shorts", "🎬 Long Videos"])
    video_type_filter = st.sidebar.radio(
        "🎞️ Select Video Type",
        options=["All", "Short", "Long"],
        index=0,
        horizontal=False  # set True if you want horizontal layout in main area
    )

    filtered_df = watch_df[(watch_df['year'] >= year_range[0]) & (watch_df['year'] <= year_range[1])]

    df = estimate_watch_time_hours(filtered_df)

    if video_type_filter != "All":
        df = df[df['video_type'] == video_type_filter]

    # Fun summary card with emojis
    total_hours = df['watch_time_hours'].sum()
    shorts_hours = df[df['video_type'] == 'Short']['watch_time_hours'].sum()
    longs_hours = df[df['video_type'] == 'Long']['watch_time_hours'].sum()
    unique_channels = df['channel'].nunique()
    unique_videos = df['video_title'].nunique()

    st.markdown(f"### 🎉 Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("⌛ Total Hours Watched", f"{total_hours:.1f} hrs", "🔥")
    col2.metric("🟠 Shorts Hours", f"{shorts_hours:.1f} hrs", f"{shorts_hours/total_hours*100:.1f}%" if total_hours else "0%")
    col3.metric("🔵 Longs Hours", f"{longs_hours:.1f} hrs", f"{longs_hours/total_hours*100:.1f}%" if total_hours else "0%")
    col4.metric("📺 Channels", f"{unique_channels}", "👍")
    col5.metric("📺 Videos", f"{unique_videos}", "👍")

    # Totals with animated progress bars
    st.subheader("Total Hours by Video Type")
    total_short = totals_short = df[df['video_type'] == 'Short']['watch_time_hours'].sum()
    total_long = totals_long = df[df['video_type'] == 'Long']['watch_time_hours'].sum()
    total_all = total_short + total_long

    short_bar = st.progress(0)
    long_bar = st.progress(0)

    import time
    for pct in range(101):
        short_bar.progress(min(int(pct * total_short / total_all), 100))
        long_bar.progress(min(int(pct * total_long / total_all), 100))
        time.sleep(0.01)

    st.write(f"🟠 Shorts: `{total_short:.2f}` hours")
    st.write(f"🔵 Longs : `{total_long:.2f}` hours")

    # Collapsible visualizations for clean UI
    with st.expander("📆 Daily Watch Time (Shorts vs Longs)"):
        daily_watch = df.groupby(['date', 'video_type'])['watch_time_hours'].sum().unstack(fill_value=0)
        plot_watch_time_interactive(daily_watch)

    with st.expander("Top Channels Watched"):
        plot_top_channels_interactive(df)

    with st.expander("Daily Usage Trend"):
        plot_youtube_usage_trend_interactive(df)

    with st.expander("Most Watched Videos"):
        plot_most_watched_video_interactive(df)

    # More stats and fun facts
    st.subheader("🏆 Top 10 Most Watched Videos")
    st.dataframe(top_10_videos(df).reset_index().rename(columns={'watch_time_hours': 'Hours Watched'}))

    st.subheader("🕒 Most Active Times")
    by_day, by_hour = active_day_hour(df)
    st.write(f"📆 Day: `{by_day.idxmax()}` with `{by_day.max():.2f}` hours")
    st.write(f"⏰ Hour: `{by_hour.idxmax()}:00` with `{by_hour.max():.2f}` hours")

    st.subheader("🎬 First Ever Video Watched")
    first_row = df.sort_values('timestamp').iloc[0]
    st.write(f"**{first_row['video_title']}** on `{first_row['timestamp']}`")

    st.subheader("🔥 Longest Binge Session")
    binge = binge_session(df)
    st.write(f"{binge['total_hours']:.2f} hours across {binge['video_count']} videos")
    st.write(f"🕒 From `{binge['start']}` to `{binge['end']}`")

if uploaded_file_search:
    search_df = load_youtube_search_history(uploaded_file_search)
    # with st.expander("Top 20 Searches"):
    #     plot_top_youtube_queries_interactive(search_df)

    with st.expander("Temporal Search Pattern"):
        plot_search_temporal_patterns_interactive(search_df)

if uploaded_file_search and uploaded_file_watch:
    with st.expander("Search vs Watch Pattern"):
        compare_search_watch_trends_interactive(search_df, df)
