import streamlit as st
import streamlit_antd_components as sac
import altair as alt
from datetime import datetime
import pandas as pd
from utils.zylinc_data import load_and_process_data_from_zylinc_db, get_all_queues_with_tables
from utils.config import ZYLINC_NAME


def show_conversation_activity_weekly():
    st.sidebar.header(f"{ZYLINC_NAME} Kø")
    queue_table_mapping = get_all_queues_with_tables()
    all_queues = list(queue_table_mapping.keys())

    selected_queue_display = st.sidebar.selectbox("Vælg en kø", all_queues, key='queue_select_act')
    original_queue_name, selected_table = queue_table_mapping[selected_queue_display]

    historical_data = load_and_process_data_from_zylinc_db(table_name=selected_table, queue_name=original_queue_name)
    if historical_data is None:
        st.error("Failed to fetch data from the database.")
        st.stop()

    historical_data["Result"] = historical_data["Result"].replace({
        "Answered": "Besvaret",
        "Missed": "Ikke besvaret"
    })

    weekday_names = {0: "Mandag", 1: "Tirsdag", 2: "Onsdag", 3: "Torsdag", 4: "Fredag"}
    historical_data["Weekday"] = historical_data["StartTimeDenmark"].dt.weekday
    historical_data["WeekdayName"] = historical_data["Weekday"].map(weekday_names)

    historical_data = historical_data[
        historical_data['StartTimeDenmark'].dt.time.between(
            datetime.strptime('05:00', '%H:%M').time(),
            datetime.strptime('18:00', '%H:%M').time()
        )
    ]

    col_1 = st.columns([1])[0]
    with col_1:
        content_tabs = sac.tabs([
            sac.TabsItem('Uge', tag='Uge', icon='calendar-week'),
            sac.TabsItem('Måned', tag='Måned', icon='calendar-month'),
            sac.TabsItem('Kvartal', tag='Kvartal', icon='bi bi-calendar-minus'),
            sac.TabsItem('Halvår', tag='Halvår', icon='calendar'),
        ], color='dark', size='md', position='top', align='start', use_container_width=True)

    def plot_weekday_activity(data, title):
        weekday_names_short = {0: "Mandag", 1: "Tirsdag", 2: "Onsdag", 3: "Torsdag", 4: "Fredag"}
        data = data[data["Weekday"].isin(weekday_names_short.keys())]

        grouped = data.groupby(['Weekday', 'WeekdayName', 'Result']).size().reset_index(name='Antal opkald')

        all_days = pd.DataFrame({
            'Weekday': list(weekday_names_short.keys()),
            'WeekdayName': [weekday_names_short[i] for i in weekday_names_short]
        })
        grouped = all_days.merge(grouped, on=['Weekday', 'WeekdayName'], how='left').fillna({'Antal opkald': 0})
        grouped['Antal opkald'] = grouped['Antal opkald'].astype(int)

        total_calls = grouped.groupby('WeekdayName')['Antal opkald'].sum()
        if not total_calls.empty:
            max_calls = total_calls.max()
            peak_days = total_calls[total_calls == max_calls].index.tolist()
            peak_days_str = ', '.join(peak_days)
            st.info(f"**Flest opkald modtaget på:** {peak_days_str} ({max_calls} opkald)")

        chart = alt.Chart(grouped).mark_bar().encode(
            x=alt.X('WeekdayName:N', title='Ugedag', sort=list(weekday_names_short.values())),
            y=alt.Y('Antal opkald:Q', title='Antal opkald'),
            color=alt.Color(
                'Result:N',
                title='Resultat',
                scale=alt.Scale(
                    domain=['Besvaret', 'Ikke besvaret'],
                    range=['#7EC8FF', '#E53935'],  # lyseblå, rød
                ),
                sort=['Besvaret', 'Ikke besvaret'],
            ),
            tooltip=[
                alt.Tooltip('WeekdayName:N', title='Ugedag'),
                alt.Tooltip('Antal opkald:Q', title='Antal opkald'),
                alt.Tooltip('Result:N', title='Resultat')
            ]
        ).properties(height=400, width=800)

        st.header(title, divider="gray")
        st.altair_chart(chart, use_container_width=True)

    if content_tabs == 'Uge':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_act_week', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_week = st.selectbox("Vælg år", unique_years, key='year_select_act_week', index=unique_years.index(session_year))
        unique_weeks = sorted(historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_week]['StartTimeDenmark'].dt.isocalendar().week.unique())

        if len(unique_weeks) == 0:
            st.error("Ingen uger med data for valgt år.")
            st.stop()

        default_week = max(unique_weeks)
        session_week = st.session_state.get('week_select_act', default_week)

        if session_week not in unique_weeks:
            session_week = default_week

        selected_week = st.selectbox("Vælg uge", unique_weeks, format_func=lambda x: f'Uge {x}', key='week_select_act', index=unique_weeks.index(session_week))
        start_of_week = pd.to_datetime(f'{selected_year_week}-W{int(selected_week)}-1', format='%Y-W%W-%w')
        end_of_week = start_of_week + pd.Timedelta(days=6)
        data_week = historical_data[
            (historical_data['StartTimeDenmark'] >= start_of_week) &
            (historical_data['StartTimeDenmark'] <= end_of_week)
        ]
        plot_weekday_activity(data_week, f"Opkaldsaktivitet fordelt på ugedage (Uge {selected_week}, {selected_year_week})")

    if content_tabs == 'Måned':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_act_month', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_month = st.selectbox("Vælg år", unique_years, key='year_select_act_month', index=unique_years.index(session_year))
        months = historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_month]['StartTimeDenmark'].dt.month.unique()
        unique_months = sorted(months)

        if len(unique_months) == 0:
            st.error("Ingen måneder med data for valgt år.")
            st.stop()

        default_month = max(unique_months)
        session_month = st.session_state.get('month_select_act', default_month)

        if session_month not in unique_months:
            session_month = default_month

        month_names = {1: "Januar", 2: "Februar", 3: "Marts", 4: "April", 5: "Maj", 6: "Juni", 7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "December"}
        selected_month = st.selectbox("Vælg måned", unique_months, format_func=lambda x: month_names[x], key='month_select_act', index=unique_months.index(session_month))
        data_month = historical_data[
            (historical_data['StartTimeDenmark'].dt.year == selected_year_month) &
            (historical_data['StartTimeDenmark'].dt.month == selected_month)
        ]
        plot_weekday_activity(data_month, f"Opkaldsaktivitet fordelt på ugedage ({month_names[selected_month]} {selected_year_month})")

    if content_tabs == 'Kvartal':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_act_quarter', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_quarter = st.selectbox("Vælg år", unique_years, key='year_select_act_quarter', index=unique_years.index(session_year))
        historical_data['Quarter'] = historical_data['StartTimeDenmark'].dt.quarter
        quarters = historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_quarter]['Quarter'].unique()
        unique_quarters = sorted(quarters)

        if len(unique_quarters) == 0:
            st.error("Ingen kvartaler med data for valgt år.")
            st.stop()

        default_quarter = max(unique_quarters)
        session_quarter = st.session_state.get('quarter_select_act', default_quarter)

        if session_quarter not in unique_quarters:
            session_quarter = default_quarter

        quarter_names = {1: "1. kvartal", 2: "2. kvartal", 3: "3. kvartal", 4: "4. kvartal"}
        selected_quarter = st.selectbox("Vælg kvartal", unique_quarters, format_func=lambda x: quarter_names[x], key='quarter_select_act', index=unique_quarters.index(session_quarter))
        data_quarter = historical_data[
            (historical_data['StartTimeDenmark'].dt.year == selected_year_quarter) &
            (historical_data['Quarter'] == selected_quarter)
        ]
        plot_weekday_activity(data_quarter, f"Opkaldsaktivitet fordelt på ugedage ({quarter_names[selected_quarter]} {selected_year_quarter})")

    if content_tabs == 'Halvår':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_act_half', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_half = st.selectbox("Vælg år", unique_years, key='year_select_act_half', index=unique_years.index(session_year))
        historical_data['Half'] = historical_data['StartTimeDenmark'].dt.month.apply(lambda m: 1 if m <= 6 else 2)
        half_names = {1: '1. halvår', 2: '2. halvår'}
        unique_halves = sorted(historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_half]['Half'].unique())

        if len(unique_halves) == 0:
            st.error("Ingen halvår med data for valgt år.")
            st.stop()

        default_half = max(unique_halves)
        session_half = st.session_state.get('half_select_act', default_half)
        if session_half not in unique_halves:
            session_half = default_half
        selected_half = st.selectbox("Vælg halvår", unique_halves, format_func=lambda x: half_names[x], key='half_select_act', index=unique_halves.index(session_half))
        data_half = historical_data[
            (historical_data['StartTimeDenmark'].dt.year == selected_year_half) &
            (historical_data['Half'] == selected_half)
        ]
        plot_weekday_activity(data_half, f"Opkaldsaktivitet fordelt på ugedage ({half_names[selected_half]} {selected_year_half})")
