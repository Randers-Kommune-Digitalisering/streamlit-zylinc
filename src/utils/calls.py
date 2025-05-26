import pytz
import pandas as pd

from datetime import datetime
from utils.api_requests import APIClient
from utils.config import ZYLINC_URL, ZYLINC_REALM, ZYLINC_CLIENT, ZYLINC_SECRET, QUEUES

zylinc_client = APIClient(ZYLINC_URL, client_id=ZYLINC_CLIENT, client_secret=ZYLINC_SECRET, realm=ZYLINC_REALM)


def get_calls_df():
    res = zylinc_client.make_request(path='api/open/v1/contactcenter/conversations')
    now = datetime.now(pytz.timezone('Europe/Copenhagen'))

    if res:
        calls = []
        if len(res) > 0:
            for c in res:
                if c.get('QueueDetails', {}).get('QueueName', None) in QUEUES:
                    agent_join_time = next((item for item in c.get('Participants', {}) if item.get('Id', None) == c.get('AgentDetails', {}).get('UserId', None)), {}).get('JoinedConversationTimeUtc', None)
                    agent_name = c.get('AgentDetails', {}).get('Name', None)

                    transferred_to = None

                    state = c.get('ConversationState', None)

                    if agent_name and not agent_join_time and next((item for item in c.get('Participants', {}) if item.get('Id', None) != c.get('Originator', {}).get('Id', None)), {}).get('Endpoint', {}).get('Address', None):
                        transferred_to = next((item for item in c.get('Participants', {}) if item.get('Id', None) != c.get('Originator', {}).get('Id', None)), {}).get('Endpoint', {}).get('Address', None)
                        state = 'Transferred'

                    calls.append({
                        'id': c.get('Id', None),
                        'direction': c.get('Direction', None),
                        'queue': c.get('QueueDetails', {}).get('QueueName', None),
                        'state': state,
                        'now': now,
                        'start': c.get('InitiationTimeUtc', None),
                        'agent_name': agent_name,
                        'agent_join_time': agent_join_time,
                        'transferred_to': transferred_to,
                        'wait_time': None,
                        'duration': None
                    })

        df = pd.DataFrame(calls)

        if not df.empty:
            df['start'] = pd.to_datetime(df['start']).map(lambda x: x.tz_convert('Europe/Copenhagen'))
            df['agent_join_time'] = pd.to_datetime(df['agent_join_time']).map(lambda x: x.tz_convert('Europe/Copenhagen'))

            df['wait_time'] = df.apply(lambda row: row['now'] - row['start'] if row['state'] not in ['Connected', 'Transferred']
                                       else row['agent_join_time'] - row['start'] if pd.notnull(row['agent_join_time']) and row['state'] != 'Transferred'
                                       else row['wait_time'] if pd.notnull(row['wait_time'])
                                       else pd.NaT, axis=1)

            df['duration'] = df.apply(lambda row: row['now'] - row['agent_join_time'] if row['state'] == 'Connected' and pd.notnull(row['agent_join_time']) else None, axis=1)

            if not df['wait_time'].isnull().all():
                df['wait_time'] = pd.to_timedelta(df['wait_time'])

            return df
    return pd.DataFrame()


def get_ended_calls_df(old_calls_df, new_calls_df, ended_calls_df):
    if not old_calls_df.empty and not new_calls_df.empty:
        result = old_calls_df[~old_calls_df['id'].isin(new_calls_df['id'])]
        if result.empty:
            return ended_calls_df
        else:
            return pd.concat([ended_calls_df, result], ignore_index=True)
    else:
        return ended_calls_df


def update_calls_df(old_calls_df, new_calls_df):
    if not old_calls_df.empty:
        merged_df = pd.merge(new_calls_df, old_calls_df, on='id', suffixes=('_new', '_old'))
        new_calls_df['state'] = merged_df.apply(lambda row: row['state_new'] if row['state_old'] not in ['Connected', 'Transferred'] else row['state_new'] if row['state_new'] == 'Transferred' and row['state_old'] == 'Connected' else row['state_old'], axis=1)
        new_calls_df['wait_time'] = merged_df.apply(lambda row: row['wait_time_old'] if row['state_old'] in ['Connected', 'Transferred'] or row['state_new'] in ['Connected', 'Transferred'] else row['wait_time_new'], axis=1)
        new_calls_df['duration'] = merged_df.apply(lambda row: row['duration_old'] if row['state_old'] != 'Connected' or pd.isnull(row['duration_new']) else row['duration_new'], axis=1)
    return new_calls_df
