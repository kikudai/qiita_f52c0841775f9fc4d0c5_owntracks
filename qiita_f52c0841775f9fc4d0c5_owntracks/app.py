import boto3
import datetime
from botocore.exceptions import ClientError
import sys


timestream_write = boto3.client('timestream-write', region_name='us-east-1')

DATABASE_NAME = 'Qiita_f52c0841775f9fc4d0c5_Owntracks'
PERIOD_HOURS = 24 * 12
PERIOD_DAYS = 365 * 200

dt_now = datetime.datetime.now()
dt = dt_now.strftime('%Y/%m/%d %H:%M:%S')

tags = [
    {
        'Key': 'create_user',
        'Value': 'lambda_function'
    },
    {
        'Key': 'create_date',
        'Value': dt
    },
    {
        'Key': 'qiita',
        'Value': 'f52c0841775f9fc4d0c5'
    },
]

field_type = dict(
    _type='VARCHAR',
    acc='BIGINT',
    alt='BIGINT',
    batt='BIGINT',
    bs='BIGINT',
    conn='VARCHAR',
    created_at='BIGINT',
    lat='DOUBLE',
    lon='DOUBLE',
    t='VARCHAR',
    tid='VARCHAR',
    tst='BIGINT',
    vac='BIGINT',
    vel='BIGINT'
)


def ts_create_database(database=DATABASE_NAME):
    try:
        response = timestream_write.create_database(
            DatabaseName=database,
            Tags=tags
        )
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'CreateDatabase {database} Status: {status}')

    except Exception as err:
        print("Error:", err)
        sys.exit(1)


def is_database(database=DATABASE_NAME):
    try:
        response = timestream_write.describe_database(
            DatabaseName=database
        )
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'DescribeDatabase {database} Status: {status}')

        return response['Database']['DatabaseName'] == database

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
    except Exception as err:
        print("Error:", err)
        sys.exit(1)


def is_table(table, database=DATABASE_NAME):
    try:
        response = timestream_write.describe_table(
            DatabaseName=database,
            TableName=table
        )
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'DescribeTable {table} Status: {status}')

        return response['Table']['TableName'] == table

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            if is_database():
                return False
    except Exception as err:
        print("Error:", err)
        sys.exit(1)


def ts_create_table(table, database=DATABASE_NAME):
    try:
        response = timestream_write.create_table(
            DatabaseName=database,
            TableName=table,
            RetentionProperties={
                'MemoryStoreRetentionPeriodInHours': PERIOD_HOURS,
                'MagneticStoreRetentionPeriodInDays': PERIOD_DAYS
            },
            Tags=tags
        )
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'CreateTable {table} Status: {status}')

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            # Databaseがない場合、Databaseを作成しテーブル作成
            if not is_database():
                ts_create_database()
                ts_create_table(table)
    except Exception as err:
        print("Error:", err)
        sys.exit(1)


def prepare_record(measure_name, measure_value, measure_value_type):
    return {
        'MeasureName': measure_name,
        'MeasureValue': str(measure_value),
        'MeasureValueType': measure_value_type,
    }


def create_records(event):

    _table_name = None
    _common_attributes = {
        'Dimensions': [
            {
                'Name': 'clientid',
                'Value': event['clientid'],
                'DimensionValueType': 'VARCHAR'
            }
        ],
        'Time': str(event['timestamp']),
        'TimeUnit': 'SECONDS'
    }
    _records = []

    print('------ payload: ', event)
    for k, v in event.items():
        # clientid, timestamp は _common_attributes で利用済みのため捨てる
        if k == 'clientid' or k == 'timestamp':
            continue

        if k == '_type':
            _table_name = v
            ts_create_table(_table_name)
        else:
            _records.append(
                prepare_record(k, str(v), field_type.get(k))
            )

    print('------ records: ', _records)

    return _table_name, _common_attributes, _records


def ts_write_records(event, table, common_attributes, records, database=DATABASE_NAME):
    try:
        response = timestream_write.write_records(
            DatabaseName=database,
            TableName=table,
            CommonAttributes=common_attributes,
            Records=records
        )
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'Processed {len(records)} records. WriteRecords Status: {status}')

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            # テーブルがない場合、テーブル作成してデータ書込
            if not is_table(table):
                ts_create_table(table)
                ts_write_records(event, table, common_attributes, records)
    except Exception as err:
        print("Error:", err)
        sys.exit(1)


def lambda_handler(event, context):
    ts_write_records(event, *create_records(event))
