# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from sqlite3 import connect

if 'db' not in st.session_state:
    st.session_state['db'] = None
if 'stock_data' not in st.session_state:
    st.session_state['stock_data'] = None

def init_db():
    db_path = "tech_service.db"
    if st.session_state['db'] is None:
        st.session_state['db'] = connect(db_path, isolation_level=None)
        with st.session_state['db']:
            cursor = st.session_state['db'].cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock (
                    id INTEGER PRIMARY KEY,
                    code TEXT,
                    name TEXT,
                    category TEXT,
                    quantity INTEGER,
                    unit TEXT,
                    purchase_price REAL,
                    sale_price REAL,
                    location TEXT,
                    min_stock INTEGER
                )
            ''')

@st.cache_resource
def load_data():
    db = st.session_state['db']
    return pd.read_sql_query("SELECT * FROM stock", db)

def get_menu_items():
    return [
        {
            "id": "dashboard",
            "title": "Ana Ekran",
            "icon": "🏠",
        },
        {
            "id": "service_board",
            "title": "Servis Panosu",
            "icon": "📋",
        },
        {
            "id": "stock",
            "title": "Stok Yönetimi",
            "icon": "📦",
        },
        {
            "id": "customers",
            "title": "Müşteriler",
            "icon": "👥",
        },
        {
            "id": "technician",
            "title": "Teknisyen Paneli",
            "icon": "👨‍🔧",
        },
    ]

def show_dashboard():
    st.metric(label="Bekleyen Onarımlar", value=5, delta="-2")
    st.metric(label="Arıza Kayıtları", value=30, delta="+10")
    st.metric(label="Ciro", value="$5000", delta="+5%")

def show_stock():
    if 'stock_data' not in st.session_state:
        st.session_state['stock_data'] = load_data()
    st.data_editor(st.session_state['stock_data'], use_container_width=True)

def show_service_board():
    # Service board implementation goes here
    pass

def show_customers():
    # Customers page implementation goes here
    pass

def show_technician_panel():
    # Technician panel implementation goes here
    pass

def main():
    init_db()
    
    st.set_page_config(page_title="Teknik Servis", layout="wide")
    menu = get_menu_items()
    selected_item = st.sidebar.selectbox("Menu", menu, format_func=lambda x: x["title"])
    
    if selected_item == "Ana Ekran":
        show_dashboard()
    elif selected_item == "Servis Panosu":
        show_service_board()
    elif selected_item == "Stok Yönetimi":
        show_stock()
    elif selected_item == "Müşteriler":
        show_customers()
    elif selected_item == "Teknisyen Paneli":
        show_technician_panel()

if __name__ == "__main__":
    main()