import sqlite3
import json
from datetime import datetime, timedelta
import random

DB_NAME = 'coffee_shop.db'


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            desc TEXT,
            price REAL NOT NULL,
            available INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            items TEXT,
            total REAL,
            timestamp DATETIME
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        base_products = [
            ('cappuccino', 'Капучино', 'Класичний з густою пінкою', 3.50, 1),
            ('latte', 'Лате', "Багато молока та м'який смак", 4.00, 1),
            ('espresso', 'Еспресо', 'Міцний заряд бадьорості', 2.50, 1)
        ]
        cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", base_products)

    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        for i in range(50):
            random_days = random.randint(0, 10)
            random_hours = random.randint(0, 23)
            order_time = now - timedelta(days=random_days, hours=random_hours)

            prod = random.choice([('Капучино', 3.50), ('Лате', 4.00), ('Еспресо', 2.50)])
            qty = random.randint(1, 2)
            items_json = json.dumps([{"name": prod[0], "quantity": qty, "price": prod[1], "sum": prod[1] * qty}])

            cursor.execute(
                "INSERT INTO orders (user_id, username, items, total, timestamp) VALUES (?, ?, ?, ?, ?)",
                (951795337, 'test_user', items_json, prod[1] * qty, order_time)
            )

    conn.commit()
    conn.close()


def get_active_products():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, desc, price FROM products WHERE available = 1")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "desc": r[2], "price": r[3]} for r in rows]


def save_order(user_id, username, items, total):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, username, items, total, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, json.dumps(items, ensure_ascii=False), total, datetime.now())
    )
    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()