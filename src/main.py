import streamlit as st
from streamlit_option_menu import option_menu
from page.conversation_activity_daily import show_conversation_activity_daily
from page.conversation_result import show_conversation_result
from page.conversation_calls import show_conversation_call
from page.conversation_queue_time import show_queue_time
from page.conversation_duration import show_conversation_duration
from page.conversation_activity_weekly import show_conversation_activity_weekly
from utils.logo import get_logo
from page.live import display_live_data
from utils.config import ZYLINC_NAME


st.set_page_config(page_title=ZYLINC_NAME.capitalize(), page_icon="assets/favicon.ico", layout="wide")

with st.sidebar:
    st.sidebar.markdown(get_logo(), unsafe_allow_html=True)
    selected = option_menu(
        ZYLINC_NAME[:1].upper() + ZYLINC_NAME[1:],
        ['Live Data', 'Varighed af samtale', 'Resultat af opkald', 'Ventetid pr opkald', 'Antal af samtaler', 'Opkaldsaktivitet Døgnet', 'Opkaldsaktivitet Ugen'],
        icons=['broadcast', 'bi bi-clock-history', 'bi bi-check2-square', 'hourglass-split', 'bi bi-telephone-outbound-fill', 'calendar-day', 'calendar-week'],
        menu_icon="headset",
        default_index=0,
    )

if selected == 'Live Data':
    display_live_data()
elif selected == 'Varighed af samtale':
    show_conversation_duration()
elif selected == 'Resultat af opkald':
    show_conversation_result()
elif selected == 'Ventetid pr opkald':
    show_queue_time()
elif selected == 'Antal af samtaler':
    show_conversation_call()
elif selected == 'Opkaldsaktivitet Døgnet':
    show_conversation_activity_daily()
elif selected == 'Opkaldsaktivitet Ugen':
    show_conversation_activity_weekly()
