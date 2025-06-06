import inspect
import uuid
import pandas as pd
import streamlit as st

period_map = {"Month": "M","Week": "W","Year": "Y"}

def periodize(df, key):
    period_ch = st.radio("📅 Period Type", ["Entire", "Year", "Month", "Week"], horizontal=True, key=key+"_radio")
    selected_period=None
    if not period_ch=="Entire":
        df['period'] = df['timestamp'].dt.tz_localize(None).dt.to_period(period_map.get(period_ch, "Y"))
        period_labels = sorted(df['period'].astype(str).unique().tolist())
        selected_period = st.select_slider(f"Select the {period_ch}",options=period_labels,value=period_labels[-1], key=key+"_slider")
    if not selected_period==None:
        selected_period = selected_period or str(df['period'].max())
        df = df[df['period'].astype(str) == selected_period]
        period_label = selected_period
    else:
        period_label = "All Time"

    return df, period_label