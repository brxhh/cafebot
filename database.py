import os
import json
from datetime import datetime
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            "desc" TEXT,
            price REAL NOT NULL,
            available INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            username TEXT,
            items TEXT,
            total REAL,
            timestamp TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        base_products = [
            ('cappuccino', 'Капучино', 'Класичний з густою пінкою', 3.50, 1),
            ('latte', 'Лате', "Багато молока та м'який смак", 4.00, 1),
            ('espresso', 'Еспресо', 'Міцний заряд бадьорості', 2.50, 1)
        ]
        cursor.executemany(
            'INSERT INTO products (id, name, "desc", price, available) VALUES (%s, %s, %s, %s, %s)',
            base_products
        )

    conn.commit()
    cursor.close()
    conn.close()


def get_active_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, "desc", price FROM products WHERE available = 1')
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [{"id": r[0], "name": r[1], "desc": r[2], "price": r[3]} for r in rows]


def save_order(user_id, username, items, total):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, username, items, total, timestamp, status) VALUES (%s, %s, %s, %s, %s, 'pending')",
        (user_id, username, json.dumps(items, ensure_ascii=False), total, datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    init_db()