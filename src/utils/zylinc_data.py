import pandas as pd
import pytz
from datetime import datetime
from utils.database_connection import get_zylinc_db_client
from datetime import timedelta
import re
from utils.config import ZYLINC_TABLE_NAME

zylinc_db_client = get_zylinc_db_client()


def convert_milliseconds_to_minutes(ms):
    return ms / (1000 * 60)


def convert_to_denmark_time(utc_time):
    utc = pytz.utc
    cet = pytz.timezone('Europe/Copenhagen')
    utc_dt = utc.localize(datetime.strptime(utc_time, '%Y-%m-%d %H:%M:%S'))
    cet_dt = utc_dt.astimezone(cet)
    return cet_dt.strftime('%Y-%m-%d %H:%M:%S')


def load_and_process_data_from_zylinc_db(table_name, queue_name=None):
    query = f"""
        SELECT "Result", "StartTimeUtc", "TotalDurationInMilliseconds", "EventDurationInMilliseconds", "ConversationEventType", "AgentDisplayName", "QueueName"
        FROM "{table_name}"
    """
    if queue_name:
        query += f" WHERE \"QueueName\" = '{queue_name}'"

    try:
        result = zylinc_db_client.execute_sql(query)
        if result is not None:
            historical_data = pd.DataFrame(result, columns=['Result', 'StartTimeUtc', 'TotalDurationInMilliseconds', 'EventDurationInMilliseconds', 'ConversationEventType', 'AgentDisplayName', 'QueueName'])
            historical_data['DurationMinutes'] = historical_data['TotalDurationInMilliseconds'].apply(convert_milliseconds_to_minutes).round(2)
            historical_data['QueueDurationMinutes'] = historical_data['EventDurationInMilliseconds'].apply(convert_milliseconds_to_minutes).round(2)
            historical_data['StartTimeDenmark'] = historical_data['StartTimeUtc'].apply(convert_to_denmark_time)
            historical_data['StartTimeDenmark'] = pd.to_datetime(historical_data['StartTimeDenmark'])
            return historical_data
        else:
            return None
    finally:
        zylinc_db_client.close_connection()


def convert_minutes_to_hms(minutes):
    if pd.isna(minutes):
        return "0:00:00"
    seconds = int(minutes * 60)
    return str(timedelta(seconds=seconds))


def get_zylinc_table_names():
    table_names = ZYLINC_TABLE_NAME
    return table_names


def get_all_queues_with_tables():
    table_names = get_zylinc_table_names()
    queue_table_mapping = {}

    for table_name in table_names:
        query = f"SELECT DISTINCT \"QueueName\" FROM \"{table_name}\""
        result = zylinc_db_client.execute_sql(query)
        if result:
            for row in result:
                original_queue_name = row[0]
                cleaned_queue_name = re.sub(r"Jobcenter[_ ]?", "", original_queue_name, flags=re.IGNORECASE)
                cleaned_queue_name = re.sub(r"tm[_ ]?", "", original_queue_name, flags=re.IGNORECASE)
                cleaned_queue_name = re.sub(r"_\d+$", "", cleaned_queue_name).strip()
                match = re.search(r"_(\d+)$", original_queue_name)
                extension_number = match.group(1) if match else ""
                cleaned_queue_name_with_extension = f"{cleaned_queue_name} - {extension_number}"
                queue_table_mapping[cleaned_queue_name_with_extension] = (original_queue_name, table_name)

    return queue_table_mapping
