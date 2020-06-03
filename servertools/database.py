#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
from typing import Optional, List, Any
import pygsheets
import sqlite3
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pandas as pd
from pandas.core.dtypes.common import is_datetime_or_timedelta_dtype
from kavalkilu import Hosts, Keys


class MySQLLocal:
    """Stuff for connecting to local (LAN) MySQLdbs
    without having to remember the proper methods"""
    Base = declarative_base()

    def __init__(self, database_name: str, connection_dict: dict = None):
        """
        Args:
            connection_dict: dict, contains connection credentials
                expects (un, pw, database, [port], [host])
        """
        h = Hosts()
        k = Keys()

        if connection_dict is None:
            # Ignore connection dict, connecting to local/usual db
            # Read in username and password dict from path
            connection_dict = k.get_key('mysqldb')
            connection_dict['database'] = database_name
        # Determine if host and port is in dictionary, if not, use defaults
        if 'port' not in connection_dict.keys():
            connection_dict['port'] = 3306
        if 'host' not in connection_dict.keys():
            connection_dict['host'] = h.get_host(name='homeserv')['ip']

        connection_url = 'mysql+mysqldb://{un}:{pw}@{host}:{port}/{database}'
        connection_url = connection_url.format(**connection_dict)
        self.engine = create_engine(connection_url)
        self.connection = self.engine.connect()

    def write_sql(self, query: str):
        """Writes a sql query to the database"""

        cursor = self.connection.begin()

        try:
            self.connection.execute(query)
            cursor.commit()
        except:
            cursor.rollback()
            raise

    def write_df_to_sql(self, tbl_name: str, df: pd.DataFrame, debug: bool = False) -> Optional[str]:
        """
        Generates an INSERT statement from a pandas DataFrame
        Args:
            tbl_name: str, name of the table to write to
            df: pandas.DataFrame
            debug: bool, if True, will only return the formatted query
        """
        # Develop a way to mass-insert a dataframe to a table, matching its format
        query_base = """
            INSERT INTO {tbl} {cols}
            VALUES {vals}
        """
        query_dict = {
            'tbl': tbl_name,
            'cols': '({})'.format(', '.join('`{}`'.format(col) for col in df.columns)),
            'vals': ', '.join(
                ['({})'.format(', '.join('"{}"'.format(val) for val in row.tolist())) for idx, row in df.iterrows()])
        }
        formatted_query = query_base.format(**query_dict)
        if debug:
            return formatted_query
        else:
            query_log = self.write_sql(formatted_query)

    def write_dataframe(self, table_name: str, df: pd.DataFrame):
        """
        Writes a pandas dataframe to database
        Args:
            table_name: str, name of the table in the database
            df: pandas.DataFrame
        """
        list_to_write = df.to_dict(orient='records')

        metadata = sqlalchemy.MetaData(bind=self.engine)
        table = sqlalchemy.Table(table_name, metadata, autoload=True)
        # Open the session
        Session = sessionmaker(bind=self.engine)
        session = Session()

        self.connection.execute(table.insert(), list_to_write)

        session.commit()
        session.close()

    def __del__(self):
        """When last reference of this is finished, ensure the connection is closed"""
        self.connection.close()


class SQLLiteLocal:
    """Common methods for interacting with SQLite data structures"""
    DEFAULT_DB_PATH = os.path.join(os.path.expanduser('~'), *['data', 'homeauto.sqlite'])

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.con = sqlite3.connect(db_path)

    def write_sql(self, query: str):
        """Write to table with query"""
        self.con.execute(query)
        self.con.commit()

    @staticmethod
    def _convert_rows_to_val_list(df: pd.DataFrame) -> str:
        """Converts rows in a dataframe to a nested tuple of values for insertion into a table"""
        val_list = []
        for idx, row in df.iterrows():
            val_row = ', '.join(f'"{val}"' for val in row.tolist())
            val_list.append(f'({val_row})')
        return f', '.join(val_list)

    def write_df_to_sql(self, tbl_name: str, df: pd.DataFrame, debug: bool = False) -> Optional[str]:
        """
        Generates an INSERT statement from a pandas DataFrame
        Args:
            tbl_name: str, name of the table to write to
            df: pandas.DataFrame
            debug: bool, if True, will only return the formatted query
        """
        # Develop a way to mass-insert a dataframe to a table, matching its format
        cols_joined = ', '.join(f'`{col}`' for col in df.columns)
        vals_str = self._convert_rows_to_val_list(df)
        query = f"""
            INSERT INTO {tbl_name} ({cols_joined})
            VALUES {vals_str}
        """
        if debug:
            return query
        else:
            self.write_sql(query)

    def read_sql(self, query: str) -> pd.DataFrame:
        """Query the database"""
        df = pd.read_sql_query(query, self.con)
        df = self._convert_times_to_local(df)
        return df

    @staticmethod
    def _convert_times_to_local(df: pd.DataFrame) -> pd.DataFrame:
        """SQLite by default stores timestamps in UTC. This should convert outputs to US/Central tz"""
        for col in df.columns.tolist():
            if is_datetime_or_timedelta_dtype(df[col]):
                # Convert from UTC to local tz
                df[col] = df[col].dt.tz_localize('utc').dt.tz_convert('US/Central')
        return df

    def __del__(self):
        """When last reference of this is finished, ensure the connection is closed"""
        self.con.close()


class GSheetReader:
    """A class to help with reading in Google Sheets"""
    def __init__(self, sheet_key: str):
        k = Keys()
        pyg = pygsheets
        local_key_path = os.path.join(os.path.expanduser('~'), *['keys', 'GSHEET_READER'])
        try:
            gsheets_creds = k.get_key('gsheet-reader')
        except:
            with open(local_key_path) as f:
                gsheets_creds = json.loads(f.read())
        os.environ['GDRIVE_API_CREDENTIALS'] = json.dumps(gsheets_creds)
        self.gc = pyg.authorize(service_account_env_var='GDRIVE_API_CREDENTIALS')
        self.sheets = self.gc.open_by_key(sheet_key).worksheets()

    def get_sheet(self, sheet_name: str) -> pd.DataFrame:
        """Retrieves a sheet as a pandas dataframe"""
        for sheet in self.sheets:
            if sheet.title == sheet_name:
                return sheet.get_as_df()
        raise ValueError(f'The sheet name "{sheet_name}" was not found '
                         f'in the list of available sheets: ({",".join([x.title for x in self.sheets])})')

    def write_df_to_sheet(self, sheet_key: str, sheet_name: str, df: pd.DataFrame):
        """Write df to sheet"""
        wb = self.gc.open_by_key(sheet_key)
        sheet = wb.worksheet_by_title(sheet_name)
        sheet.clear()
        sheet.set_dataframe(df, (1, 1))
