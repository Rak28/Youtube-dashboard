import pandas as pd

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