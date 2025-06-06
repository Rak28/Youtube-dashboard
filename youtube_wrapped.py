from os import name
import zipfile
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from wordcloud import WordCloud

import Handler.Helper as Helper
import Handler.Utils as Utils
from Plotter import *
from Processors import *

# --- Streamlit APP ---

watch_flag = False 
search_flag = False

st.set_page_config(page_title="YouTube Wrapped Dashboard", layout="wide", page_icon="📺")

st.title("📺 YouTube Wrapped Dashboard")
st.sidebar.markdown("## 🎭 How Are You Feeling?")
mood = st.sidebar.selectbox("Pick your YouTube mood:", ["🎉 Loving it!", "🤔 Could be better", "😴 Too much binge", "🚀 On fire!", "😱 OMG!"])

st.sidebar.markdown("## 📁 Upload Your Data")

uploaded_zip = st.sidebar.file_uploader("Upload a ZIP file (Eg:`takeout-20250531T201211Z-001.zip`)", type="zip")
if uploaded_zip is not None:
    with zipfile.ZipFile(uploaded_zip) as z:
        for filename in z.namelist():
            if filename.endswith("watch-history.json"):
                with z.open(filename) as f:
                    watch_df = Utils.load_youtube_watch_history(f)
                    watch_flag=True
            if filename.endswith("search-history.json"):
                with z.open(filename) as f:
                    search_df = Utils.load_youtube_search_history(f)
                    search_flag=True

if watch_flag and search_flag:

    min_year, max_year = int(watch_df['year'].min()), int(watch_df['year'].max())

    st.sidebar.markdown("## 🎛️ Filters")
    year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year), 1)
    video_type_filter = st.sidebar.radio("🎞️ Video Type", ["All", "Short", "Long"])

    filtered_df = watch_df[(watch_df['year'] >= year_range[0]) & (watch_df['year'] <= year_range[1])]
    df = estimate_watch_time_hours(filtered_df)
    if video_type_filter != "All":
        df = df[df['video_type'] == video_type_filter]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("⌛ Total Hours", f"{df['watch_time_hours'].sum():.1f} hrs")
    col2.metric("🟠 Shorts", f"{df[df['video_type'] == 'Short']['watch_time_hours'].sum():.1f} hrs")
    col3.metric("🔵 Longs", f"{df[df['video_type'] == 'Long']['watch_time_hours'].sum():.1f} hrs")
    col4.metric("📺 Channels", f"{df['channel'].nunique()}")
    col5.metric("🎞️ Videos", f"{df['video_title' ].nunique()}")

tab_labels = ["📈 Watch Trends", "🎥 Top Channels", "🎬 Top Videos", "🗓️ Patterns", "📅 Weekday vs Weekend"] if watch_flag else []
if search_flag:
    tab_labels.append("🔍 Search Trends")

if not tab_labels:
    st.info("Please upload Google takeout zip file to see the dashboard.")
else:
    tabs = st.tabs(tab_labels)
    i=0
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    if not watch_df.empty:
        with tabs[i]:
            st.subheader("Daily Watch Time")
            val_ret=Helper.periodize(df, "watch")
            plot_daily_video_watch_time_by_type(*val_ret)
            plot_daily_video_watch_count_by_type(*val_ret)
            i+=1

        with tabs[i]:
            st.subheader("Most Watched Channels")
            val_ret=Helper.periodize(df, "channel")
            plot_top_channels_clicked(*val_ret)
            plot_top_channels_watched(*val_ret)
            i+=1

        with tabs[i]:
            st.subheader("Top Videos")
            val_ret=Helper.periodize(df, "video")
            plot_top_videos_clicked(*val_ret)
            plot_top_videos_watched(*val_ret) 
            i+=1

        with tabs[i]:
            st.subheader("Viewing Patterns")
            by_day, by_hour = active_day_hour(df)
            st.write(f"📆 Busiest Day: `{by_day.idxmax()}` — `{by_day.max():.2f}` hours")
            st.write(f"⏰ Peak Hour: `{by_hour.idxmax()}:00` — `{by_hour.max():.2f}` hours")
            # Additional highlights
            st.markdown("---")
            st.markdown("### 🔥 Highlights")
            st.write("**🎬 First Video Watched:**", df.sort_values('timestamp').iloc[0]['video_title'])
            binge = binge_session(df)
            st.write(f"**📺 Longest Binge:** {binge['total_hours']:.2f} hrs across {binge['video_count']} videos")
            st.write(f"🕒 From `{binge['start']}` to `{binge['end']}`")
            i+=1

        with tabs[i]:
            st.subheader("Weekend vs Weekday")
            st.plotly_chart(plot_weekend_vs_weekday(df), use_container_width=True)
            # fig = plot_animated_weekend_weekday(df)
            # st.plotly_chart(fig, use_container_width=True)
            i+=1

    if not search_df.empty:
        with tabs[i]:
            st.markdown("### 🔍 Your YouTube Searches")
            st.plotly_chart(plot_search_intensity_gauge(search_df, df), use_container_width=True)

            st.markdown("⏱️ Search Timing Heatmap")
            plot_search_temporal_patterns_interactive(search_df)

            if not watch_df.empty:
                st.markdown("🔁 Compare Search vs Watch Activity")
                compare_search_watch_trends_interactive(search_df, df)
                i+=1