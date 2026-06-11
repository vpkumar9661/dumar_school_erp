"""
Database connection — Supabase (PostgreSQL) via psycopg2
Drop-in replacement for the old Flask-MySQLdb interface.
Usage in routes:  from db import db
                  conn = db.connection
                  cur = conn.cursor()   # returns RealDictCursor
"""
import os
import logging
import psycopg2
import psycopg2.pool
import psycopg2.extras
from flask import g

logger = logging.getLogger(__name__)

_pool = None
_db_url = None


class Database:
    """Provides a mysql.connection-compatible interface for PostgreSQL."""

    def init_app(self, app):
        global _pool, _db_url
        db_url = app.config.get('DATABASE_URL')
        if not db_url:
            raise ValueError(
                "DATABASE_URL is not set. "
                "Add it to your .env file with your Supabase connection string."
            )

        # Ensure sslmode=require for Supabase connections
        if 'supabase' in db_url and 'sslmode' not in db_url:
            separator = '&' if '?' in db_url else '?'
            db_url = f"{db_url}{separator}sslmode=require"

        _db_url = db_url

        try:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=db_url,
            )
            logger.info("Database connection pool created successfully.")
        except psycopg2.OperationalError as e:
            logger.error(f"Failed to create DB pool on startup: {e}")
            logger.error(
                "The app will start but DB connections will be retried on first request. "
                "Check your DATABASE_URL and ensure the Supabase pooler URL is used "
                "(port 6543, not 5432)."
            )
            _pool = None

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
                    if _pool is not None:
                        _pool.putconn(conn)
                except Exception:
                    pass

    def _ensure_pool(self):
        """Lazy-create the pool if startup connection failed."""
        global _pool
        if _pool is None and _db_url:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=_db_url,
            )
            logger.info("Database connection pool created (lazy init).")

    @property
    def connection(self):
        """Per-request connection stored in Flask g."""
        if 'db_conn' not in g:
            self._ensure_pool()
            conn = _pool.getconn()
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            g.db_conn = conn
        return g.db_conn


db = Database()
