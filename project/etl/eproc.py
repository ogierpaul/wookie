import pandas as pd
from paco.utils import clean_inputs, pg_conn, copy_from, es_index
import elasticsearch
from psycopg2 import sql
import datetime

from paco.utils import es_create, es_create_load


def read_file(filepath):
    nrows = 100
    df = pd.read_csv(filepath, sep=',', nrows=nrows, dtype=str)
    df['ts'] = datetime.datetime.now().strftime('%Y-%m-%d')
    return df


def clean_file(df):
    usecols = pd.Series(
        index=['id', 'name', 'street', 'city', 'postalcode', 'state', 'country', 'iban', 'duns', 'ssn', 'ts'],
        data=['ariba', 'name', 'street', 'city', 'postalcode', 'state', 'countrycode', 'iban', 'duns', 'ssn',
              'extract_ts']
    )
    coltypes = {
        'ariba': 'str',
        'postalcode': 'str',
        'duns': 'str',
        'extract_ts': 'ts'
    }
    colzeroes = {
        'ariba': 6,
        'arp': 6,
            'duns': 9
    }

    def eproc_filter(df):
        """
        Dummy filter and transform function for df
        Args:
            df (pd.DataFrame)
        Returns:
            pd.DataFrame
        """
        df2 = df.loc[df['countrycode'] != 'ZA']
        df2['duns'] = df2['duns'].str.replace('-', '')
        return df2

    df2 = clean_inputs(df=df, pkey='ariba', usecols=usecols, sep_csv='|', coltypes=coltypes, colzeroes=colzeroes,
                       transform_func=eproc_filter)
    return df2


def pg_create_table(conn, tablename):
    # noinspection SyntaxError
    create_sql = sql.SQL("""
    CREATE TABLE IF NOT EXISTS {tablename} (
        ariba VARCHAR,
        name VARCHAR,
        street VARCHAR,
        city VARCHAR,
        postalcode VARCHAR ,
        state VARCHAR ,
        countrycode VARCHAR,
        iban VARCHAR ,
        duns VARCHAR,
        ssn VARCHAR,
        extract_ts TIMESTAMP,
        PRIMARY KEY (ariba)
    );
    """).format(tablename=sql.Identifier(tablename))
    cur = conn.cursor()
    cur.execute(create_sql)
    conn.commit()
    cur.close()
    return True


def pg_model(df):
    """
    Model the data for ingestion into Postgres
    Do nothing
    Args:
        df (pd.DataFrame):

    Returns:
        pd.DataFrame
    """
    return df


def pg_create_load(df, conn, drop, create, tablename, staging_dir, pkey):
    """
    Create the table and load the data into it
    Args:
        df(pd.DataFrame): Data
        conn (psycopg2.connection): Connector
        drop (bool): If True, proceed first to drop the table
        create (bool): If True, proceed then to create the table
        tablename (str): Name of the table in Postgres
        staging_dir (str): Path of the dir where to write the csv for COPY FROM
        pkey (str/list): Primary key in Postgres

    Returns:
        pd.DataFrame
    """
    cur = conn.cursor()
    if drop is True:
        for t in tablename, 'temp_' + tablename:
            cur.execute(sql.SQL("""DROP TABLE IF EXISTS {tablename};""").format(tablename=sql.Identifier(t)))
        conn.commit()
        cur.close()
    if create is True:
        pg_create_table(conn=conn, tablename=tablename)
    copy_from(df=df, conn=conn, tablename=tablename, staging_dir=staging_dir, pkey=pkey)
    return None




def es_model(df):
    """
    Model the data for ingestion into ElasticSearch
    Change Timestamp format
    Args:
        df (pd.DataFrame):

    Returns:
        pd.DataFrame
    """
    df2 = df
    timecol = 'extract_ts'
    df2[timecol] = df[timecol].apply(lambda r: r.isoformat())
    return df


def main():
    tablename = 'ariba'
    extract_path = '../tests/extract_dir/ariba.csv'
    staging_dir = '../../tests/staging'
    e = elasticsearch.Elasticsearch()

    # Extract and Clean
    df = read_file(filepath=extract_path)
    df2 = clean_file(df=df)

    # LOAD INTO PG
    df_pg = pg_model(df2)
    pg_create_load(df=df_pg, conn=pg_conn(), drop=True, create=True, tablename=tablename, staging_dir=staging_dir,
                   pkey=tablename)

    # LOAD INTO ES
    df_es = es_model(df2)
    es_create_load(df=df_es, es_client=e, drop=True, create=True, indexname=tablename, pkey=tablename)
    print('successfull')


if __name__ == '__main__':
    main()