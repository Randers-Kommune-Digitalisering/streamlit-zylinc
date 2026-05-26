import streamlit as st
import streamlit_antd_components as sac
import altair as alt
from datetime import datetime
import pandas as pd
from utils.zylinc_data import load_and_process_data_from_zylinc_db, get_all_queues_with_tables
from utils.config import ZYLINC_NAME


def show_conversation_activity_daily():
    st.sidebar.header(f"{ZYLINC_NAME} Kø")
    queue_table_mapping = get_all_queues_with_tables()
    all_queues = list(queue_table_mapping.keys())

    selected_queue_display = st.sidebar.selectbox("Vælg en kø", all_queues, key='queue_select_activity')
    original_queue_name, selected_table = queue_table_mapping[selected_queue_display]

    historical_data = load_and_process_data_from_zylinc_db(table_name=selected_table, queue_name=original_queue_name)
    if historical_data is None:
        st.error("Failed to fetch data from the database.")
        st.stop()

    col_1 = st.columns([1])[0]

    with col_1:
        content_tabs = sac.tabs([
            sac.TabsItem('Dag', tag='Dag', icon='calendar-day'),
            sac.TabsItem('Uge', tag='Uge', icon='calendar-week'),
            sac.TabsItem('Måned', tag='Måned', icon='calendar-month'),
            sac.TabsItem('Kvartal', tag='Kvartal', icon='bi bi-calendar-minus'),
            sac.TabsItem('Halvår', tag='Halvår', icon='calendar'),
        ], color='dark', size='md', position='top', align='start', use_container_width=True)

    def get_time_intervals():
        times = pd.date_range("05:00", "18:00", freq="30min").strftime('%H:%M')
        return times

    def plot_activity_daily(data, time_col):
        data = data[data['Result'].notnull()]
        data['TimeInterval'] = data[time_col].dt.floor('30T').dt.strftime('%H:%M')

        intervals = get_time_intervals()
        interval_df = pd.DataFrame({'TimeInterval': intervals})

        grouped = data.groupby(['TimeInterval', 'Result']).size().reset_index(name='Antal opkald')
        grouped = interval_df.merge(grouped, on='TimeInterval', how='left').fillna({'Antal opkald': 0})
        grouped['Antal opkald'] = grouped['Antal opkald'].astype(int)
        chart = alt.Chart(grouped).mark_bar().encode(
            x=alt.X(
                'TimeInterval:O',
                title='Tidspunkt på dagen',
                sort=list(intervals),
                axis=alt.Axis(labelAngle=0)
            ),
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
                alt.Tooltip('TimeInterval:O', title='Tidspunkt på dagen'),
                alt.Tooltip('Antal opkald:Q', title='Antal opkald'),
                alt.Tooltip('Result:N', title='Resultat')
            ]
        ).properties(height=400, width=800)
        st.altair_chart(chart, use_container_width=True)

    if content_tabs == 'Dag':
        unique_dates = sorted(historical_data['StartTimeDenmark'].dt.date.unique())

        if len(unique_dates) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_date = max(unique_dates)
        session_date = st.session_state.get('date_input_activity', default_date)

        if session_date not in unique_dates:
            session_date = default_date

        selected_date = st.date_input(
            "Vælg en dato",
            value=session_date,
            min_value=min(unique_dates),
            max_value=max(unique_dates),
            key='date_input_activity'
        )
        data_day = historical_data[
            (historical_data['StartTimeDenmark'].dt.date == selected_date) &
            (historical_data['StartTimeDenmark'].dt.time.between(
                datetime.strptime('05:00', '%H:%M').time(),
                datetime.strptime('18:00', '%H:%M').time()
            ))
        ]

        data_day["Result"] = data_day["Result"].replace({
            "Answered": "Besvaret",
            "Missed": "Ikke besvaret"
        })

        if not data_day.empty:
            data_day = data_day[data_day['Result'].notnull()]
            data_day['TimeInterval'] = data_day['StartTimeDenmark'].dt.floor('30T').dt.strftime('%H:%M')
            peak = data_day.groupby('TimeInterval').size().reset_index(name='Antal opkald')
            if not peak.empty:
                max_count = peak['Antal opkald'].max()
                peak_times = peak[peak['Antal opkald'] == max_count]['TimeInterval'].tolist()
                peak_times_str = ', '.join(peak_times)
                st.info(f"**Flest opkald modtaget kl.:** {peak_times_str} ({max_count} opkald)")

        st.header(f"Opkaldsaktivitet fordelt på døgnet ({selected_date.strftime('%d-%m-%Y')})", divider="gray")
        plot_activity_daily(data_day, 'StartTimeDenmark')

    if content_tabs == 'Uge':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_activity_week', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_week = st.selectbox("Vælg år", unique_years, key='year_select_activity_week', index=unique_years.index(session_year))
        unique_weeks = sorted(historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_week]['StartTimeDenmark'].dt.isocalendar().week.unique())

        if len(unique_weeks) == 0:
            st.error("Ingen uger med data for valgt år.")
            st.stop()

        default_week = max(unique_weeks)
        session_week = st.session_state.get('week_select_activity', default_week)

        if session_week not in unique_weeks:
            session_week = default_week

        selected_week = st.selectbox("Vælg uge", unique_weeks, format_func=lambda x: f'Uge {x}', key='week_select_activity', index=unique_weeks.index(session_week))
        start_of_week = pd.to_datetime(f'{selected_year_week}-W{int(selected_week)}-1', format='%Y-W%W-%w')
        end_of_week = start_of_week + pd.Timedelta(days=6)
        data_week = historical_data[
            (historical_data['StartTimeDenmark'] >= start_of_week) &
            (historical_data['StartTimeDenmark'] <= end_of_week) &
            (historical_data['StartTimeDenmark'].dt.time.between(
                datetime.strptime('05:00', '%H:%M').time(),
                datetime.strptime('18:00', '%H:%M').time()
            ))
        ]

        data_week["Result"] = data_week["Result"].replace({
            "Answered": "Besvaret",
            "Missed": "Ikke besvaret"
        })

        if not data_week.empty:
            data_week = data_week[data_week['Result'].notnull()]
            data_week['TimeInterval'] = data_week['StartTimeDenmark'].dt.floor('30T').dt.strftime('%H:%M')
            peak = data_week.groupby('TimeInterval').size().reset_index(name='Antal opkald')
            if not peak.empty:
                max_count = peak['Antal opkald'].max()
                peak_times = peak[peak['Antal opkald'] == max_count]['TimeInterval'].tolist()
                peak_times_str = ', '.join(peak_times)
                st.info(f"**Flest opkald modtaget kl.:** {peak_times_str} ({max_count} opkald)")

        st.header(f"Opkaldsaktivitet fordelt på døgnet (Uge {selected_week}, {selected_year_week})", divider="gray")
        plot_activity_daily(data_week, 'StartTimeDenmark')

    if content_tabs == 'Måned':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_activity_month', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_month = st.selectbox("Vælg år", unique_years, key='year_select_activity_month', index=unique_years.index(session_year))
        unique_months = sorted(historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_month]['StartTimeDenmark'].dt.month.unique())
        month_names = {1: 'Januar', 2: 'Februar', 3: 'Marts', 4: 'April', 5: 'Maj', 6: 'Juni', 7: 'Juli', 8: 'August', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'December'}

        if len(unique_months) == 0:
            st.error("Ingen måneder med data for valgt år.")
            st.stop()

        default_month = max(unique_months)
        session_month = st.session_state.get('month_select_activity', default_month)

        if session_month not in unique_months:
            session_month = default_month

        selected_month = st.selectbox("Vælg måned", unique_months, format_func=lambda x: month_names[x], key='month_select_activity', index=unique_months.index(session_month))
        data_month = historical_data[
            (historical_data['StartTimeDenmark'].dt.year == selected_year_month) &
            (historical_data['StartTimeDenmark'].dt.month == selected_month) &
            (historical_data['StartTimeDenmark'].dt.time.between(
                datetime.strptime('05:00', '%H:%M').time(),
                datetime.strptime('18:00', '%H:%M').time()
            ))
        ]

        data_month["Result"] = data_month["Result"].replace({
            "Answered": "Besvaret",
            "Missed": "Ikke besvaret"
        })

        if not data_month.empty:
            data_month = data_month[data_month['Result'].notnull()]
            data_month['TimeInterval'] = data_month['StartTimeDenmark'].dt.floor('30T').dt.strftime('%H:%M')
            peak = data_month.groupby('TimeInterval').size().reset_index(name='Antal opkald')
            if not peak.empty:
                max_count = peak['Antal opkald'].max()
                peak_times = peak[peak['Antal opkald'] == max_count]['TimeInterval'].tolist()
                peak_times_str = ', '.join(peak_times)
                st.info(f"**Flest opkald modtaget kl.:** {peak_times_str} ({max_count} opkald)")

        st.header(f"Opkaldsaktivitet fordelt på døgnet ({month_names[selected_month]} {selected_year_month})", divider="gray")
        plot_activity_daily(data_month, 'StartTimeDenmark')

    if content_tabs == 'Kvartal':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_activity_quarter', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_quarter = st.selectbox("Vælg år", unique_years, key='year_select_activity_quarter', index=unique_years.index(session_year))
        historical_data['Quarter'] = historical_data['StartTimeDenmark'].dt.quarter
        unique_quarters = sorted(historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_quarter]['Quarter'].unique())
        quarter_names = {1: '1. kvartal', 2: '2. kvartal', 3: '3. kvartal', 4: '4. kvartal'}

        if len(unique_quarters) == 0:
            st.error("Ingen kvartaler med data for valgt år.")
            st.stop()

        default_quarter = max(unique_quarters)
        session_quarter = st.session_state.get('quarter_select_activity', default_quarter)

        if session_quarter not in unique_quarters:
            session_quarter = default_quarter

        selected_quarter = st.selectbox("Vælg kvartal", unique_quarters, format_func=lambda x: quarter_names[x], key='quarter_select_activity', index=unique_quarters.index(session_quarter))
        data_quarter = historical_data[
            (historical_data['StartTimeDenmark'].dt.year == selected_year_quarter) &
            (historical_data['Quarter'] == selected_quarter) &
            (historical_data['StartTimeDenmark'].dt.time.between(
                datetime.strptime('05:00', '%H:%M').time(),
                datetime.strptime('18:00', '%H:%M').time()
            ))
        ]

        data_quarter["Result"] = data_quarter["Result"].replace({
            "Answered": "Besvaret",
            "Missed": "Ikke besvaret"
        })

        if not data_quarter.empty:
            data_quarter = data_quarter[data_quarter['Result'].notnull()]
            data_quarter['TimeInterval'] = data_quarter['StartTimeDenmark'].dt.floor('30T').dt.strftime('%H:%M')
            peak = data_quarter.groupby('TimeInterval').size().reset_index(name='Antal opkald')
            if not peak.empty:
                max_count = peak['Antal opkald'].max()
                peak_times = peak[peak['Antal opkald'] == max_count]['TimeInterval'].tolist()
                peak_times_str = ', '.join(peak_times)
                st.info(f"**Flest opkald modtaget kl.:** {peak_times_str} ({max_count} opkald)")

        st.header(f"Opkaldsaktivitet fordelt på døgnet ({quarter_names[selected_quarter]} {selected_year_quarter})", divider="gray")
        plot_activity_daily(data_quarter, 'StartTimeDenmark')

    if content_tabs == 'Halvår':
        unique_years = sorted(historical_data['StartTimeDenmark'].dt.year.unique())

        if len(unique_years) == 0:
            st.error("Ingen data tilgængelig for den valgte kø.")
            st.stop()

        default_year = max(unique_years)
        session_year = st.session_state.get('year_select_activity_half', default_year)

        if session_year not in unique_years:
            session_year = default_year

        selected_year_half = st.selectbox("Vælg år", unique_years, key='year_select_activity_half', index=unique_years.index(session_year))
        historical_data['Half'] = historical_data['StartTimeDenmark'].dt.month.apply(lambda m: 1 if m <= 6 else 2)
        half_names = {1: '1. halvår', 2: '2. halvår'}
        unique_halves = sorted(historical_data[historical_data['StartTimeDenmark'].dt.year == selected_year_half]['Half'].unique())

        if len(unique_halves) == 0:
            st.error("Ingen halvår med data for valgt år.")
            st.stop()

        default_half = max(unique_halves)
        session_half = st.session_state.get('half_select_activity', default_half)

        if session_half not in unique_halves:
            session_half = default_half

        selected_half = st.selectbox("Vælg halvår", unique_halves, format_func=lambda x: half_names[x], key='half_select_activity', index=unique_halves.index(session_half))
        data_half = historical_data[
            (historical_data['StartTimeDenmark'].dt.year == selected_year_half) &
            (historical_data['Half'] == selected_half) &
            (historical_data['StartTimeDenmark'].dt.time.between(
                datetime.strptime('05:00', '%H:%M').time(),
                datetime.strptime('18:00', '%H:%M').time()
            ))
        ]

        data_half["Result"] = data_half["Result"].replace({
            "Answered": "Besvaret",
            "Missed": "Ikke besvaret"
        })

        if not data_half.empty:
            data_half = data_half[data_half['Result'].notnull()]
            data_half['TimeInterval'] = data_half['StartTimeDenmark'].dt.floor('30T').dt.strftime('%H:%M')
            peak = data_half.groupby('TimeInterval').size().reset_index(name='Antal opkald')
            if not peak.empty:
                max_count = peak['Antal opkald'].max()
                peak_times = peak[peak['Antal opkald'] == max_count]['TimeInterval'].tolist()
                peak_times_str = ', '.join(peak_times)
                st.info(f"**Flest opkald modtaget kl.:** {peak_times_str} ({max_count} opkald)")

        st.header(f"Opkaldsaktivitet fordelt på døgnet ({half_names[selected_half]} {selected_year_half})", divider="gray")
        plot_activity_daily(data_half, 'StartTimeDenmark')
