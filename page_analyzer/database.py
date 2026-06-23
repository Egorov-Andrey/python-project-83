import datetime
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection_db():
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не установлен")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Successfully connected to database")
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise


@contextmanager
def db_connection():
    conn = get_connection_db()
    try:
        yield conn
    finally:
        conn.close()


def get_url_by_id(conn, id):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT id, name, created_at FROM urls WHERE id = %s",
                        (id,))
        return cursor.fetchone()


def find_url_by_name(conn, normalized_url):
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM urls WHERE name=%s",
                    (normalized_url, ))
        url_id = cursor.fetchone()[0]
        return url_id if url_id else None


def add_url(conn, normalized_url):
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO urls (name, created_at) VALUES (%s, %s)"
                            " RETURNING id",
                            (normalized_url, datetime.datetime.now()))
            conn.commit()   
            return cursor.fetchone()[0], True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        exiting_id = find_url_by_name(conn, normalized_url)
        return exiting_id, False


def get_all_urls_with_check_last(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT" 
        " urls.id, name, urls.created_at, url_checks.status_code FROM urls" 
        " LEFT JOIN url_checks ON urls.id = url_checks.url_id "
        "WHERE url_checks.created_at = (" 
        "SELECT MAX(created_at) FROM url_checks WHERE url_id = urls.id)" 
        "OR url_checks.created_at IS NULL ORDER BY urls.created_at DESC")
        return cursor.fetchall()


def get_checks_by_url_id(conn, url_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """SELECT id, status_code, h1, title, description, created_at 
               FROM url_checks 
               WHERE url_id = %s 
               ORDER BY created_at DESC""",
            (url_id,)
        )
        return cursor.fetchall()


def add_check(conn, url_id, status_code, h1, title, description):

    if not url_id:
        raise ValueError("Invalid url_id")
    
    with conn.cursor() as cursor:
        cursor.execute(
            """INSERT INTO url_checks 
               (url_id, status_code, h1, title, description, created_at) 
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (int(url_id), status_code, h1, title, description,
             datetime.datetime.now())
        )
        conn.commit()
    