import streamlit as st
import pandas as pd
import sqlite3
import json

st.set_page_config(page_title="Кав'ярня Адмін", layout="wide")
st.title("☕️ Панель керування та Аналітика")


def get_db_connection():
    return sqlite3.connect('coffee_shop.db')


# --- БЛОК 1: АНАЛИТИКА (Pandas) ---
st.header("📊 Фінансові показники")

conn = get_db_connection()
df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
conn.close()

if not df_orders.empty:
    df_orders['timestamp'] = pd.to_datetime(df_orders['timestamp'])
    df_orders['date'] = df_orders['timestamp'].dt.date

    total_revenue = df_orders['total'].sum()
    total_orders = len(df_orders)
    avg_check = total_revenue / total_orders

    col1, col2, col3 = st.columns(3)
    col1.metric("Загальна виручка", f"{total_revenue:.2f} €")
    col2.metric("Всього замовлень", total_orders)
    col3.metric("Середній чек", f"{avg_check:.2f} €")

    st.subheader("📈 Графік виручки по днях")
    revenue_by_day = df_orders.groupby('date')['total'].sum().reset_index()
    revenue_by_day['date'] = pd.to_datetime(revenue_by_day['date'])
    revenue_by_day.set_index('date', inplace=True)
    st.line_chart(revenue_by_day)
else:
    st.info("Замовлень ще немає.")

# --- БЛОК 2: ДИНАМИЧЕСКОЕ МЕНЮ ---
st.markdown("---")
st.header("📋 Керування наявністю в Меню")

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, name, available FROM products")
products = cursor.fetchall()
conn.close()

st.write("Зніміть галочку, якщо товар закінчився. Зміни миттєво відобразяться у користувачів.")

with st.form("menu_management"):
    updated_statuses = {}
    for p_id, p_name, p_avail in products:
        updated_statuses[p_id] = st.checkbox(p_name, value=bool(p_avail), key=f"check_{p_id}")

    save_btn = st.form_submit_button("Зберегти зміни в меню")

    if save_btn:
        conn = get_db_connection()
        cursor = conn.cursor()
        for p_id, is_available in updated_statuses.items():
            status_val = 1 if is_available else 0
            cursor.execute("UPDATE products SET available = ? WHERE id = ?", (status_val, p_id))
        conn.commit()
        conn.close()
        st.success("Меню успішно оновлено!")
        st.rerun()