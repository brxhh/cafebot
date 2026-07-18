import os
import warnings
import streamlit as st
import pandas as pd
import psycopg2
import json
from datetime import date
import requests
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh
import time
warnings.filterwarnings('ignore', category=UserWarning)

st.set_page_config(page_title="Кав'ярня Адмін", layout="wide")
st.title("☕️ Панель керування та Аналітика")
st_autorefresh(interval=5000, limit=None, key="admin_autorefresh")

load_dotenv()
CORRECT_PASSWORD = os.getenv("CORRECT_PASSWORD")
TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_ID = 951795337


# --- 1. НАДЕЖНАЯ СИСТЕМА ЛОГИНА (БЕЗ COOKIES) ---
def check_password():
    url_time = st.query_params.get("t")

    if url_time:
        try:
            if (time.time() - float(url_time)) < 28800:  # 8 часов
                st.session_state["authenticated"] = True
                return True
            else:
                st.query_params.clear()
        except:
            pass

    if st.session_state.get("authenticated"):
        return True

    st.markdown("### 🔒 Вхід")
    password = st.text_input("Введіть пароль:", type="password")

    if password == CORRECT_PASSWORD:
        st.session_state["authenticated"] = True
        st.query_params["t"] = str(time.time())
        st.rerun()
    elif password:
        st.error("❌ Неправильний пароль!")

    return False


if not check_password():
    st.stop()


# --- 2. БЕЗОПАСНОЕ ПОДКЛЮЧЕНИЕ К БД (С КЭШЕМ) ---
@st.cache_resource(ttl=600)
def init_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=5)


try:
    conn = init_connection()
    if conn.closed != 0:
        st.cache_resource.clear()
        conn = init_connection()
    conn.autocommit = True
    cursor = conn.cursor()
except Exception as e:
    st.error(f"⚠️ Помилка підключення до бази даних: {e}")
    st.stop()

# --- 3. АНАЛИТИКА ТА ЗВІТ ---
st.header("📊 Фінансові показники")

df_orders = pd.read_sql_query("SELECT * FROM orders WHERE status = 'completed'", conn)

if not df_orders.empty:
    df_orders['timestamp'] = pd.to_datetime(df_orders['timestamp'])
    df_orders['date'] = df_orders['timestamp'].dt.date

    total_revenue = df_orders['total'].sum()
    total_orders = len(df_orders)
    avg_check = total_revenue / total_orders if total_orders > 0 else 0

    today = date.today()
    liquidity_today = df_orders[df_orders['date'] == today]['total'].sum()

    col_btn, _ = st.columns([2, 3])
    with col_btn:
        if st.button("📈 Закрити зміну (Відправити звіт)"):
            report = (
                f"📊 <b>ЗВІТ ЗА {today.strftime('%d.%m.%Y')}</b>\n\n"
                f"💵 Виручка за день: <b>{liquidity_today:.2f} €</b>\n"
                f"📦 Кількість замовлень: <b>{len(df_orders[df_orders['date'] == today])}</b>\n"
                f"💳 Середній чек: <b>{avg_check:.2f} €</b>"
            )
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                "chat_id": ADMIN_ID, "text": report, "parse_mode": "HTML"
            })
            st.success("✅ Звіт відправлено в Telegram!")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Виручка (За весь час)", f"{total_revenue:.2f} €")
    col2.metric("Виручка (Сьогодні)", f"{liquidity_today:.2f} €", "Готівка в касі")
    col3.metric("Замовлень", total_orders)
    col4.metric("Середній чек", f"{avg_check:.2f} €")

    st.markdown("<br>", unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📈 Графік виручки по днях")
        revenue_by_day = df_orders.groupby('date')['total'].sum().reset_index()
        revenue_by_day['date'] = revenue_by_day['date'].astype(str)
        st.bar_chart(revenue_by_day, x='date', y='total')

    with chart_col2:
        st.subheader("🥧 Популярність напоїв (шт)")
        all_items = []
        for items_json in df_orders['items']:
            try:
                for item in json.loads(items_json):
                    all_items.append({"name": item['name'], "quantity": item['quantity']})
            except:
                pass

        if all_items:
            df_items = pd.DataFrame(all_items)
            items_grouped = df_items.groupby('name')['quantity'].sum().reset_index()
            items_grouped.set_index('name', inplace=True)
            st.bar_chart(items_grouped)
else:
    st.info("Ще немає виконаних замовлень.")

# --- 4. ДИНАМІЧНЕ МЕНЮ ---
st.markdown("---")
with st.expander("📋 Керування наявністю в Меню"):
    cursor.execute("SELECT id, name, available FROM products ORDER BY name")
    products = cursor.fetchall()

    with st.form("menu_management"):
        updated_statuses = {}
        for p_id, p_name, p_avail in products:
            updated_statuses[p_id] = st.checkbox(p_name, value=bool(p_avail), key=f"check_{p_id}")

        if st.form_submit_button("Зберегти зміни в меню"):
            for p_id, is_available in updated_statuses.items():
                cursor.execute("UPDATE products SET available = %s WHERE id = %s", (1 if is_available else 0, p_id))
            st.success("Меню успішно оновлено!")
            st.rerun()

    st.markdown("---")

    col_add, col_del = st.columns(2)

    with col_add:
        with st.popover("➕ Додати позицію", use_container_width=True):
            with st.form("add_new_product_form"):
                st.write("Введіть дані нового напою:")
                new_id = st.text_input("ID (англ, без пробілів)*")
                new_name = st.text_input("Назва для меню*")
                new_desc = st.text_input("Опис")
                new_price = st.number_input("Ціна (€)*", min_value=0.1, step=0.5, format="%.2f")

                if st.form_submit_button("Додати в базу", type="primary", use_container_width=True):
                    if new_id and new_name and new_price > 0:
                        try:
                            cursor.execute(
                                'INSERT INTO products (id, name, "desc", price, available) VALUES (%s, %s, %s, %s, 1)',
                                (new_id.strip().lower(), new_name.strip(), new_desc.strip(), new_price)
                            )
                            st.rerun()
                        except psycopg2.IntegrityError:
                            conn.rollback()
                            st.error("Помилка: Напій з таким ID вже існує!")
                    else:
                        st.warning("Заповніть обов'язкові поля (*)")

    with col_del:
        with st.popover("🗑 Видалити позицію", use_container_width=True):
            with st.form("delete_product_form"):
                st.write("Оберіть напій для видалення:")

                prod_dict = {f"{p_name} ({p_id})": p_id for p_id, p_name, _ in products}

                if not prod_dict:
                    st.info("Меню порожнє.")
                    selected_to_delete = None
                else:
                    selected_to_delete = st.selectbox("Напій", options=list(prod_dict.keys()),
                                                      label_visibility="collapsed")

                if st.form_submit_button("🗑 Видалити назавжди", use_container_width=True):
                    if selected_to_delete:
                        del_id = prod_dict[selected_to_delete]
                        cursor.execute("DELETE FROM products WHERE id = %s", (del_id,))
                        st.rerun()
# --- 5. АКТИВНІ ЗАМОВЛЕННЯ ---
st.markdown("---")
st.header("🛎 Активні замовлення")

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
            st.subheader(f"Замовлення #{order_id} — {total:.2f} €")
            try:
                items_text = "".join([f"▪️ {i['name']} — **{i['quantity']} шт.**\n" for i in json.loads(items_json)])
                st.markdown(items_text)
            except:
                st.caption("Помилка читання складу")

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Видати", key=f"ready_{order_id}", use_container_width=True):
                if user_id:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                        "chat_id": user_id, "text": f"✅ Твоє замовлення готове! Підходь забирати ☕️"
                    })
                cursor.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
                st.rerun()

        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.popover("❌ Скасувати", use_container_width=True):
                cancel_reason = st.text_input("Вкажіть причину (необов'язково):", key=f"reason_{order_id}",
                                              placeholder="Наприклад: немає молока")
                if st.button("Підтвердити відміну", key=f"confirm_{order_id}", type="primary",
                             use_container_width=True):
                    reason_text = f"\n💬 Причина: {cancel_reason}" if cancel_reason.strip() else ""
                    if user_id:
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={
                            "chat_id": user_id,
                            "text": f"❌ Ваше замовлення було скасовано.{reason_text}\nЗверніться до баристи."
                        })
                    cursor.execute("UPDATE orders SET status = 'cancelled' WHERE id = %s", (order_id,))
                    st.rerun()
        st.markdown("---")

# --- 6. АРХИВ (СЕГОДНЯ) ---
with st.expander("📂 Видані за сьогодні"):
    cursor.execute(
        "SELECT id, items, total FROM orders WHERE status = 'completed' AND DATE(timestamp) = CURRENT_DATE ORDER BY id DESC")
    completed_today = cursor.fetchall()

    if not completed_today:
        st.info("Сьогодні ще немає виданих замовлень.")
    else:
        for order_id, items_json, total in completed_today:
            st.markdown(f"**#{order_id}** — {total:.2f} €")