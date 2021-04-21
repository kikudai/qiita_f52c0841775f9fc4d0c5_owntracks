# Owntracks のテレメトリを Amazon Timestream に格納する。
#
# Database や Table がある前提で処理する。
# なかった場合、 ResourceNotFoundException で検知して Database や Table を作成。

import boto3
import datetime
import sys
from botocore.exceptions import ClientError


__author__: str = 'kikudai'


timestream_write = boto3.client(
    'timestream-write',
    region_name='us-east-1'
)


DATABASE_NAME = 'qiita_f52c0841775f9fc4d0c5_owntracks'

# 1時間
PERIOD_HOURS: int = 1
# 200年
PERIOD_DAYS: int = 365 * 200

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
    vel='BIGINT',
    event_t='BIGINT',
    clientid='VARCHAR'
)


def get_tags():
    """
    Database, Table作成のときに付けるタグ
    一律デフォルトでタグ付けしたいものに利用
    """
    dt_now = datetime.datetime.now()
    dt = dt_now.strftime('%Y/%m/%d %H:%M:%S')

    return [
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


def ts_create_database():
    """
    Database を作成
    実装上は Database がまだ作成されていないときにのみ処理
    """
    try:
        response = timestream_write.create_database(
            DatabaseName=DATABASE_NAME,
            Tags=get_tags()
        )

    except Exception as err:
        print("Error:", err)
        sys.exit(1)

    status = response['ResponseMetadata']['HTTPStatusCode']
    print(f'CreateDatabase {DATABASE_NAME} Status: {status}')


def is_database() -> bool:
    """
    データベース存在フラグ
    ResourceNotFoundException = データベースが存在しない
    と限らないと考えたためこのフラグを用意
    """
    response = None
    try:
        response = timestream_write.describe_database(
            DatabaseName=DATABASE_NAME
        )
    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
    except Exception as err:
        print("Error:", err)
        sys.exit(1)
    else:
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'DescribeDatabase {DATABASE_NAME} Status: {status}')

        return response['Database']['DatabaseName'] == DATABASE_NAME


def is_table(table) -> bool:
    """
    テーブル存在フラグ
    ResourceNotFoundException = テーブルが存在しない
    と限らないと考えたためこのフラグを用意
    """
    response = None
    try:
        response = timestream_write.describe_table(
            DatabaseName=DATABASE_NAME,
            TableName=table
        )

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            if is_database():
                return False
    except Exception as err:
        print("Error:", err)
        sys.exit(1)
    else:
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'DescribeTable {table} Status: {status}')

        return response['Table']['TableName'] == table


def ts_create_table(table):
    """
    Table を作成
    実装上は Table がまだ作成されていないときにのみ処理
    """
    response = None
    try:
        response = timestream_write.create_table(
            DatabaseName=DATABASE_NAME,
            TableName=table,
            RetentionProperties={
                'MemoryStoreRetentionPeriodInHours': PERIOD_HOURS,
                'MagneticStoreRetentionPeriodInDays': PERIOD_DAYS
            },
            Tags=get_tags()
        )

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            # Databaseがない場合、Databaseを作成しテーブル作成
            if not is_database():
                ts_create_database()
                ts_create_table(table)
            else:
                print("Databaseはあるが、未知の ResourceNotFoundException")
                print("Error:", err)
                sys.exit(1)
        else:
            print("Error:", err)
            sys.exit(1)
    except Exception as err:
        print("Error:", err)
        sys.exit(1)
    else:
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'CreateTable {table} Status: {status}')


def prepare_common_attributes(name, Value, dimensionValueType):
    return {
        'Name': name,
        'Value': Value,
        'DimensionValueType': dimensionValueType
    }


def prepare_record(measure_name, measure_value, measure_value_type):
    return {
        'MeasureName': measure_name,
        'MeasureValue': measure_value,
        'MeasureValueType': measure_value_type,
    }


def create_records(event):
    """
    event （MQTT テレメトリ）を Timestream 用レコードに変換
    """
    _table_name = None
    _common_attributes = {
        'Dimensions': [],
        'Time': str(event['tst']),
        'TimeUnit': 'SECONDS'
    }
    _records = []

    print('------ payload: ', event)
    for k, v in event.items():
        # tst は _common_attributes で利用済みのため捨てる
        if k == 'tst':
            continue

        # clientid, t _common_attributes で利用
        if k == 'clientid' or k == 't':
            _common_attributes['Dimensions'].append(
                prepare_common_attributes(k, str(v), field_type.get(k))
            )
            continue

        if k == '_type':
            _table_name = v
            continue

        _records.append(
            prepare_record(k, str(v), field_type.get(k))
        )

    print('------ _common_attributes: ', _common_attributes)
    print('------ records: ', _records)

    return _table_name, _common_attributes, _records


def ts_write_records(event, table, common_attributes, records):
    """
    IoT Core より連携される event （MQTT テレメトリ）を書き込む
    """
    response = None
    try:
        response = timestream_write.write_records(
            DatabaseName=DATABASE_NAME,
            TableName=table,
            CommonAttributes=common_attributes,
            Records=records
        )

    except ClientError as err:
        if err.response['Error']['Code'] == 'ResourceNotFoundException':
            # テーブルがない場合、テーブル作成してデータ書込
            if not is_table(table):
                print(f'ts_write_records: Table: {table} に書込しようとしたところ存在しないため create_table します')
                ts_create_table(table)
                ts_write_records(event, table, common_attributes, records)
            else:
                print(f'Table: {table} はあるが、未知の ResourceNotFoundException')
                print("Error:", err)
                sys.exit(1)
        else:
            print("Error:", err)
            sys.exit(1)
    except Exception as err:
        print("Error:", err)
        sys.exit(1)
    else:
        status = response['ResponseMetadata']['HTTPStatusCode']
        print(f'Processed {len(records)} records. WriteRecords Status: {status}')


def lambda_handler(event, context):
    ts_write_records(event, *create_records(event))
