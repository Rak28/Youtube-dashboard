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
    min_date, max_date = watch_df['timestamp'].iloc[-1], watch_df['timestamp'].iloc[0]

    total_days = (watch_df['timestamp'].max().date() - watch_df['timestamp'].min().date()).days + 1

    st.sidebar.markdown("## 🎛️ Filters")
    year_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year), 1)
    video_type_filter = st.sidebar.radio("🎞️ Video Type", ["All", "Short", "Long"])

    filtered_df = watch_df[(watch_df['year'] >= year_range[0]) & (watch_df['year'] <= year_range[1])]
    df = estimate_watch_time_hours(filtered_df)
    if video_type_filter != "All":
        df = df[df['video_type'] == video_type_filter]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("⌛ Total Hours", f"{df['watch_time_hours'].sum():.1f} hrs", help="Total hours spent on youtube", delta_color="off")
    col2.metric("🟠 Shorts", f"{df[df['video_type'] == 'Short']['watch_time_hours'].sum():.1f} hrs")
    col3.metric("🔵 Longs", f"{df[df['video_type'] == 'Long']['watch_time_hours'].sum():.1f} hrs")
    col4.metric("📺 Channels", f"{df['channel'].nunique()}")
    col5.metric("🎞️ Videos", f"{df['video_title' ].nunique()}")

tab_labels = ["🗓️ Highlights", "📈 Watch Trends", "🎥 Top Channels", "🎬 Top Videos", "📅 Behavioural Insights"] if watch_flag else []
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
            st.subheader("Viewing Patterns")
            active_days = df['date'].nunique()
            by_day, day_vids, by_hour, hour_vids = active_day_hour(df)

            kpis = calculate_kpis(df)

            # --- KPIs in 3 Columns ---
            col1, col2, col3 = st.columns(3)
            col1.metric("📆 Busiest Day", kpis["busiest_day"], f"{kpis['hours_watched']:.2f} hrs | {kpis['videos_watched']} video(s)", border=True)
            col2.metric("⏰ Peak Hour", f"{by_hour.idxmax()}:00", f"{by_hour.max():.2f} hrs | {hour_vids[by_hour.idxmax()]} video(s)", border=True)
            col3.metric("🔥 Longest Binge", f"{kpis['binge']['total_hours']:.2f} hrs", f"{kpis['binge']['video_count']} video(s)", border=True)

            col4, col5, col6 = st.columns(3)
            col4.metric("📅 Consistency", f"{kpis['consistency']:.1f}%", f"{kpis['active_days']:,} active / {kpis['total_days']:,} days", border=True)
            col5.metric("🕒 Preferred Time", f"{int(kpis['median_hour'])}:00", kpis["period"], border=True)
            col6.metric("❤️ Favorite Creator", kpis["top_channel"], f"{max(df['channel'].value_counts())} video(s) | {kpis['avg_watch_time']:.1f} hrs", border=True)
            
            # --- Expander: Detailed Stats ---
            with st.expander("📌 Detailed Insights", expanded=True):
                st.markdown("## 🎯 Viewing Highlights")

                total_hours = df['watch_time_hours'].sum()
                total_days = total_hours / 24
                streak = longest_streak(df['date'])
                top5_watched = df.sort_values('watch_time_hours', ascending=False).drop_duplicates('url').head(5)
                top5_titles = df['url'].value_counts().head(5).index
                top5_replayed_rows = df[df['url'].isin(top5_titles)].drop_duplicates(subset='url', keep='first')

                col1, col2 = st.columns(2)
                col1.metric("⏱️ Total Watch Time", f"{int(total_days)} days of YouTube", f"{int(total_hours)} hrs")
                col2.metric("📈 Longest Streak", f"{streak} days", "Consecutively active")
                st.write("")
                st.markdown("### 📽️ Milestone Moments")
                cols = st.columns(3)
                milestones = [(0, "1st"), (99, "100th"), (999, "1000th")]
                j=0
                for index, label in milestones:
                    if index < len(df):
                        row = df.sort_values('timestamp').iloc[index]
                        video_card_in_col(cols[j],row['video_title'],row['url'],row['timestamp'].strftime('%Y-%m-%d'),label)
                        j+=1
                st.write("")

                st.markdown("### 🏆 Top 5 Videos Watched")
                cols = st.columns(5)
                for j, (_, row) in enumerate(top5_watched.iterrows()):
                    video_card_in_col(cols[j], row['video_title'], row['url'], row['timestamp'].strftime('%Y-%m-%d'),j+1)
                st.write("")

                st.markdown("### 🔁 Top 5 Replayed Videos")
                cols = st.columns(5)
                for j, (_, row) in enumerate(top5_replayed_rows.iterrows()):
                    video_card_in_col(cols[j], row['video_title'], row['url'], row['timestamp'].strftime('%Y-%m-%d'),f"{df['url'].value_counts()[row['url']]}× views")

                st.write("")
                st.caption("💡 These highlight cards reflect your top moments on YouTube.")
            i+=1

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
            st.subheader("🗓️ Viewing by Weekday")
            plot_viewing_by_weekday(df)

            st.subheader("Weekend vs Weekday")
            plot_weekend_vs_weekday(df)

            st.subheader("🎥 Video Type Distribution")
            plot_video_type_distribution(df)

            st.subheader("⏰ Hour vs Day Activity")
            plot_hour_day_heatmap(df)

            st.subheader("📆 Weekly Viewing Rhythm")
            plot_weekly_viewing_rhythm(df)
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