import streamlit as st
import sqlite3
import pandas as pd

if 'connection' not in st.session_state:
    st.session_state.connection = sqlite3.connect('teknik_servis.db')

def init_db():
    conn = st.session_state.connection
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS onarimlar (
            id INTEGER PRIMARY KEY,
            tarih TEXT,
            aciklama TEXT,
            durum TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arizalar (
            id INTEGER PRIMARY KEY,
            tarih TEXT,
            aciklama TEXT,
            durum TEXT
        )
    ''')
    conn.commit()

st.title("Teknik Servis Plugin'i")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        ciro = st.metric(label="Ciro", value="$0")
    with col2:
        bekleyen_onarimlar = st.metric(label="Bekleyen Onarımlar", value=0)
    with col2:
        ariza_kayitlari = st.metric(label="Arıza Kayıtları", value=0)

init_db()

# Ekranı kartlara boğmamak için st.tabs kullan
with st.container():
    tab1, tab2, tab3 = st.tabs(["Onarımlar", "Arızalar", "Stok Durumu"])
    
    with tab1:
        onarimlar_df = pd.read_sql_query("SELECT * FROM onarimlar", st.session_state.connection)
        if not onarimlar_df.empty:
            st.data_editor(onarimlar_df, enable_row_selection=True, hide_index=True)
        else:
            st.write("Henüz bir onarıma kaydettiniz.")

    with tab2:
        arizalar_df = pd.read_sql_query("SELECT * FROM arizalar", st.session_state.connection)
        if not arizalar_df.empty:
            st.data_editor(arizalar_df, enable_row_selection=True, hide_index=True)
        else:
            st.write("Henüz bir arızaya kaydettiniz.")

    with tab3:
        # Stok durumu için Akıllı Filtreleme mantığı
        filter_options = ["Bilgisayar", "Akıllı Ev", "Güvenlik"]
        selected_filters = st.sidebar.multiselect("Filtreler", filter_options)
        
        if selected_filters:
            query = f"SELECT * FROM stok WHERE category IN ({','.join(['?']*len(selected_filters))})"
            st_data = pd.read_sql_query(query, st.session_state.connection, params=selected_filters)
        else:
            st_data = pd.read_sql_query("SELECT * FROM stok", st.session_state.connection)
        
        if not st_data.empty:
            with st.expander("Stok Durumu"):
                st.data_editor(st_data, enable_row_selection=True, hide_index=True)