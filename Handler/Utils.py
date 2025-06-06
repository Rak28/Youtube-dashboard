import pandas as pd

def load_youtube_watch_history(data):
    # with open(file_path, 'r', encoding='utf-8') as f:
    #     data = json.load(f)
    df = pd.read_json(data)
    df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df['year'] = df['timestamp'].dt.year
    df['video_title'] = df['title'].astype(str)
    df['video_title'] = df['video_title'].str.extract(r'Watched(.*)')
    df['channel'] = df['subtitles'].apply(lambda x: x[0]['name'] if isinstance(x, list) and 'name' in x[0] else None)
    df['url'] = df['titleUrl']
    df=df[df.details.isna()]
    return df[['timestamp', 'video_title', 'channel', 'url', 'date','year']]

def load_youtube_search_history(data):
    df=pd.read_json(data)
    # df = pd.json_normalize(data)
    df['timestamp'] = pd.to_datetime(df['time'], errors='coerce')
    df['query'] = df['title'].str.extract(r'Searched for (.*)')
    return df[['timestamp', 'query']].dropna()

