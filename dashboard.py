import os
import streamlit as st
import pandas as pd
import psycopg2
import json
from datetime import date
import requests
from dotenv import load_dotenv

st.set_page_config(page_title="Кав'ярня Адмін", layout="wide")
st.title("☕️ Панель керування та Аналітика")

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

@st.cache_resource
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- БЛОК 1: АНАЛІТИКА (Pandas) ---
st.header("📊 Фінансові показники")

try:
    conn = get_db_connection()
    df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
except Exception as e:
    st.error(f"Помилка підключення до бази: {e}")
    df_orders = pd.DataFrame()

if not df_orders.empty:
    df_orders['timestamp'] = pd.to_datetime(df_orders['timestamp'])
    df_orders['date'] = df_orders['timestamp'].dt.date

    # Рахуємо метрики
    total_revenue = df_orders['total'].sum()
    total_orders = len(df_orders)
    avg_check = total_revenue / total_orders if total_orders > 0 else 0

    # Ліквідність (Готівка/Виручка за сьогодні)
    today = date.today()
    liquidity_today = df_orders[df_orders['date'] == today]['total'].sum()

    # Виводимо 4 картки в один ряд
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Загальна виручка", f"{total_revenue:.2f} €")
    col2.metric("Ліквідність (Сьогодні)", f"{liquidity_today:.2f} €", "Готівка в касі")
    col3.metric("Всього замовлень", total_orders)
    col4.metric("Середній чек", f"{avg_check:.2f} €")

    st.markdown("<br>", unsafe_allow_html=True)  # Відступ

    # Розділяємо екран на 2 колонки для графіків
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📈 Графік виручки по днях")
        revenue_by_day = df_orders.groupby('date')['total'].sum().reset_index()
        revenue_by_day['date'] = pd.to_datetime(revenue_by_day['date'])
        revenue_by_day.set_index('date', inplace=True)
        st.line_chart(revenue_by_day)

    with chart_col2:
        st.subheader("🥧 Популярність напоїв (шт)")
        # Збираємо всі продані товари з JSON
        all_items = []
        for items_json in df_orders['items']:
            try:
                items_list = json.loads(items_json)
                for item in items_list:
                    all_items.append({"name": item['name'], "quantity": item['quantity']})
            except:
                pass

        if all_items:
            df_items = pd.DataFrame(all_items)
            items_grouped = df_items.groupby('name')['quantity'].sum().reset_index()
            items_grouped.set_index('name', inplace=True)
            st.bar_chart(items_grouped)
        else:
            st.info("Немає даних про товари")

else:
    st.info("Замовлень ще немає.")

# --- БЛОК 2: ДИНАМІЧНЕ МЕНЮ ---
st.markdown("---")
st.header("📋 Керування наявністю в Меню")

conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, name, available FROM products")
products = cursor.fetchall()

st.write("Зніміть галочку, якщо товар закінчився. Зміни миттєво відобразяться у користувачів.")

with st.form("menu_management"):
    updated_statuses = {}
    for p_id, p_name, p_avail in products:
        updated_statuses[p_id] = st.checkbox(p_name, value=bool(p_avail), key=f"check_{p_id}")

    save_btn = st.form_submit_button("Зберегти зміни в меню")

    if save_btn:
        for p_id, is_available in updated_statuses.items():
            status_val = 1 if is_available else 0
            cursor.execute("UPDATE products SET available = %s WHERE id = %s", (status_val, p_id))
        conn.commit()
        st.success("Меню успішно оновлено!")
        st.rerun()

# --- БЛОК 3: АКТИВНІ ЗАМОВЛЕННЯ ---
st.markdown("---")
st.header("🛎 Активні замовлення (Кухня)")

col_title, col_btn = st.columns([3, 2])
with col_btn:
    if st.button("🚀 Видати всі поточні замовлення"):
        cursor.execute("SELECT id, user_id FROM orders WHERE status = 'pending' OR status IS NULL")
        all_pending = cursor.fetchall()

        for o_id, u_id in all_pending:
            if u_id:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                    "chat_id": u_id, "text": f"✅ Твоє замовлення готове! Підходь забирати ☕️"
                })

        cursor.execute("UPDATE orders SET status = 'completed' WHERE status = 'pending' OR status IS NULL")
        conn.commit()
        st.rerun()

try:
    cursor.execute(
        "SELECT id, items, total, user_id FROM orders WHERE status = 'pending' OR status IS NULL ORDER BY id ASC")
    active_orders = cursor.fetchall()
except Exception as e:
    st.warning(f"⚠️ Помилка завантаження замовлень: {e}")
    active_orders = []

if not active_orders:
    st.success("🎉 Усі замовлення видані! Черги немає.")
else:
    for order_id, items_json, total, user_id in active_orders:
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(f"**Замовлення #{order_id}** на суму {total} €")

        with col3:
            if st.button("✅ Видати", key=f"ready_{order_id}"):
                if user_id:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                        "chat_id": user_id, "text": f"✅ Твоє замовлення готове! Підходь забирати ☕️"
                    })

                cursor.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
                conn.commit()
                st.rerun()

cursor.close()