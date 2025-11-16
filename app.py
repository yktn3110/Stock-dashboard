import streamlit as st

from config import DEFAULT_PAGE, EXCEL_PATH, SESSION_KEY_PAGE
from data_loader import load_data
from pages.dashboard import render_dashboard
from pages.g1 import render_g1


def main():
    if not EXCEL_PATH.exists():
        st.error(f"Excel ファイルが見つかりません: {EXCEL_PATH}")
        return

    df_list, df_q = load_data(EXCEL_PATH)

    if SESSION_KEY_PAGE not in st.session_state:
        st.session_state[SESSION_KEY_PAGE] = DEFAULT_PAGE

    page = st.session_state[SESSION_KEY_PAGE]

    if page == "dashboard":
        render_dashboard(df_list, df_q)
    elif page == "g1":
        render_g1(df_q)
    else:
        st.session_state[SESSION_KEY_PAGE] = DEFAULT_PAGE
        render_dashboard(df_list, df_q)


if __name__ == "__main__":
    main()
