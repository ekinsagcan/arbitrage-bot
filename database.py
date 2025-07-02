import os
import psycopg2
from psycopg2 import sql, errors
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT")
        )
        self.cur = self.conn.cursor()
        
    def execute(self, query, params=None):
        try:
            self.cur.execute(query, params or ())
            self.conn.commit()
            return self.cur
        except errors.UniqueViolation:
            self.conn.rollback()
            return None
        except Exception as e:
            self.conn.rollback()
            raise e

    def fetch_one(self, query, params=None):
        self.cur.execute(query, params or ())
        return self.cur.fetchone()

    def fetch_all(self, query, params=None):
        self.cur.execute(query, params or ())
        return self.cur.fetchall()

    def close(self):
        self.cur.close()
        self.conn.close()
