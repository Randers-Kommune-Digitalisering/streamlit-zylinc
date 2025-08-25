import pandas as pd


def set_df_time_style(df):
    if 'wait_time' in df:
        df['wait_time'] = pd.to_timedelta(df['wait_time'])
        df['wait_time'] = df['wait_time'].dt.floor('s').astype(str).str.replace('0 days ', '')
    if 'duration' in df:
        df['duration'] = pd.to_timedelta(df['duration'])
        df['duration'] = df['duration'].dt.floor('s').astype(str).str.replace('0 days ', '')
    if 'start' in df:
        df['start'] = df['start'].dt.strftime('%d-%m-%Y %H:%M:%S')
    return df


def highlight_state(row):
    if 'state' in row:
        if row['state'] == 'Queued':
            css = 'background-color: red; color: white'
        elif row['state'] == 'Connected':
            css = 'background-color: green; color: white'
        elif row['state'] == 'Transferred':
            css = 'background-color: #4CBB17; color: white'
        elif row['state'] == 'Missed':
            css = 'background-color: red; color: white'
        else:
            css = 'background-color: white'
    else:
        css = 'background-color: white'

    return [css] * len(row)


def style_dataframe(styler, color):
    return styler.set_table_styles(
        [
            {
                'selector': 'th',
                'props': [
                    ('background-color', f'{color}'),
                    ('color', 'black'),
                    ('font-family', 'Arial, sans-serif'),
                    ('font-size', '16px')
                ]
            },
            {
                'selector': 'td, th',
                'props': [
                    ('border', f'2px solid {color}')
                ]
            }
        ]
    ).hide()
