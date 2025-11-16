import streamlit as st
import pandas as pd

EXCEL_PATH = "data/portfolio.xlsx"

@st.cache_data
def load_data():
    xls = pd.ExcelFile(EXCEL_PATH)
    df_list = pd.read_excel(xls, "銘柄一覧")
    df_q = pd.read_excel(xls, "四半期業績")
    return df_list, df_q

df_list, df_q = load_data()

st.title("銘柄ダッシュボード（試作）")
st.subheader("銘柄一覧")
st.dataframe(df_list)
