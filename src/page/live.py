from utils.styling import set_df_time_style, highlight_state, style_dataframe
from utils.calls import get_calls_df, get_ended_calls_df, update_calls_df
import streamlit as st
import pandas as pd
import time
from utils.config import ZYLINC_NAME


def display_live_data():
    st.title(f"{ZYLINC_NAME} Live Data")

    old_calls_df = pd.DataFrame()
    ended_calls_df = pd.DataFrame()
    placeholder = st.empty()

    while True:
        with st.spinner('Venter på opkald...'):
            while True:
                new_calls_df = get_calls_df()
                if not new_calls_df.empty:
                    break
                time.sleep(1)

        if not new_calls_df.empty:
            updated_calls_df = update_calls_df(old_calls_df, new_calls_df)
            ended_calls_df = get_ended_calls_df(old_calls_df, updated_calls_df, ended_calls_df)

            old_calls_df = updated_calls_df.copy()

            incoming_calls = updated_calls_df[updated_calls_df['direction'] == 'Incoming'].copy()
            incoming_calls = set_df_time_style(incoming_calls)
        else:
            if not old_calls_df.empty:
                incoming_calls = old_calls_df[old_calls_df['direction'] == 'Incoming'].copy()
                incoming_calls = set_df_time_style(incoming_calls)
            else:
                incoming_calls = pd.DataFrame()

        placeholder.empty()
        with placeholder.container():
            if not incoming_calls.empty:
                st.write("Incoming calls")
                st.write(style_dataframe(incoming_calls[['start', 'queue', 'state', 'agent_name', 'wait_time', 'duration']].style.apply(highlight_state, axis=1), 'lightblue').to_html(), unsafe_allow_html=True)

            if not ended_calls_df.empty:
                st.write("Ended calls")
                tmp_df = ended_calls_df.head(10).copy()
                tmp_df = set_df_time_style(tmp_df)
                tmp_df['state'] = tmp_df.apply(lambda row: 'Missed' if row['state'] not in ['Connected', 'Transferred'] else row['state'], axis=1)
                st.write(style_dataframe(tmp_df[['start', 'queue', 'state', 'agent_name', 'wait_time', 'duration']].style.apply(highlight_state, axis=1), 'lightblue').to_html(), unsafe_allow_html=True)

        time.sleep(1)
