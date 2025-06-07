import pandas as pd
import streamlit as st

# --- PREPROCESSING FUNCTIONS ---
@st.cache_data
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

@st.cache_data
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
@st.cache_data
def top_10_videos(df):
    return df.groupby('video_title')['watch_time_hours'].sum().sort_values(ascending=False).head(10)

@st.cache_data
def active_day_hour(df):
    # Reorder days of the week
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df['weekday'] = df['timestamp'].dt.day_name()
    df['hour'] = df['timestamp'].dt.hour

    # Sum of watch time by weekday and hour
    day_hrs = df.groupby('weekday')['watch_time_hours'].sum()
    day_vids = df['timestamp'].dt.day_name().value_counts().reindex(weekday_order)
    
    hour_hrs = df.groupby('hour')['watch_time_hours'].sum()
    hour_vids = df.groupby('hour')['watch_time_hours'].size()
    day_hrs = day_hrs.reindex(weekday_order)

    return day_hrs, day_vids, hour_hrs, hour_vids

@st.cache_data
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

@st.cache_data
def longest_streak(dates):
    sorted_dates = sorted(set(dates))
    streak, max_streak = 1, 1
    for j in range(1, len(sorted_dates)):
        if (sorted_dates[j] - sorted_dates[j-1]).days == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1
    return max_streak

@st.cache_data
def calculate_kpis(df):
    active_days = df['date'].nunique()
    by_day, day_vids, by_hour, hour_vids = active_day_hour(df)
    total_days = (df['timestamp'].max().date() - df['timestamp'].min().date()).days + 1
    consistency = 100 * active_days / total_days
    median_hour = df['timestamp'].dt.hour.median()
    period = "🌅 Early Bird" if median_hour < 10 else "🌞 Daytime Viewer" if median_hour < 17 else "🌙 Night Owl"
    top_channel = df['channel'].value_counts().idxmax()
    busiest_day = by_day.idxmax()
    hours_watched = by_day.max()
    videos_watched = day_vids[busiest_day]
    binge = binge_session(df)
    loyal_channel = top_channel
    avg_watch_time = df[df['channel'] == loyal_channel]['watch_time_hours'].sum()

    return {
        "active_days": active_days,
        "total_days": total_days,
        "consistency": consistency,
        "median_hour": median_hour,
        "period": period,
        "top_channel": top_channel,
        "busiest_day": busiest_day,
        "hours_watched": hours_watched,
        "videos_watched": videos_watched,
        "binge": binge,
        "avg_watch_time": avg_watch_time
    }

@st.cache_data
def watch_type_totals(df):
    return df.groupby('video_type')['watch_time_hours'].sum()