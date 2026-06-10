"""
Database connection — Supabase (PostgreSQL) via psycopg2
Drop-in replacement for the old Flask-MySQLdb interface.
Usage in routes:  from db import db
                  conn = db.connection
                  cur = conn.cursor()   # returns RealDictCursor
"""
import psycopg2
import psycopg2.pool
import psycopg2.extras
from flask import g

_pool = None


class Database:
    """Provides a mysql.connection-compatible interface for PostgreSQL."""

    def init_app(self, app):
        global _pool
        db_url = app.config.get('DATABASE_URL')
        if not db_url:
            raise ValueError(
                "DATABASE_URL is not set. "
                "Add it to your .env file with your Supabase connection string."
            )
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=db_url,
        )

        @app.teardown_appcontext
        def _return_conn(exc=None):
            conn = g.pop('db_conn', None)
            if conn is not None:
                if exc:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                try:
                    _pool.putconn(conn)
                except Exception:
                    pass

    @property
    def connection(self):
        """Per-request connection stored in Flask g."""
        if 'db_conn' not in g:
            conn = _pool.getconn()
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            g.db_conn = conn
        return g.db_conn


db = Database()
