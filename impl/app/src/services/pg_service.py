# Instances of this class are used to interact with an Azure PostgreSQL
# database.  Primary functionality is to obtain a DB connection and
# cursor, and to close these properly.  See main_pg.py for usage.
# Chris Joakim, Microsoft
#
# See https://learn.microsoft.com/en-us/azure/postgresql/single-server/connect-python
# See https://wiki.postgresql.org/wiki/Psycopg2_Tutorial

import logging
import os

import psycopg2
from psycopg2 import pool

from src.services.config_service import ConfigService


class PGService(object):

    def __init__(self, envname, dbname):
        self.envname = envname
        self.dbname = dbname
        self.pgpool = None
        self.conn = None
        self.cursor = None

        if str(envname).lower() == "azure":
            host = ConfigService.pg_flex_server()
            user = ConfigService.pg_flex_user()
            password = ConfigService.pg_flex_password()
            sslmode = "sslmode=require"
        else:
            # default to 'localhost'
            host = "localhost"
            user = os.environ["USERNAME"]
            password = os.environ["LOCAL_PG_PASS"]
            sslmode = ""

        # Build a connection string from the variables
        self.conn_string = "host={} user={} dbname={} password={} {}".format(
            host, user, dbname, password, sslmode
        )

        self.pgpool = psycopg2.pool.SimpleConnectionPool(1, 20, self.conn_string)
        if self.pgpool != None:
            logging.info("PGService - connection pool created")

        self.conn = self.pgpool.getconn()
        if self.conn != None:
            logging.info("PGService - connection created")

    def get_cursor(self):
        self.cursor = self.conn.cursor()
        return self.cursor

    def close(self) -> None:
        """commit the cursor and close the db connection, if they exist"""
        if self.cursor != None:
            self.cursor.close()
        if self.conn != None:
            self.conn.commit()
            self.conn.close()
            logging.info("PGService - connection closed")
