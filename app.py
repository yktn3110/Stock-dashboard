import streamlit as st

from config import DEFAULT_PAGE, EXCEL_PATH, SESSION_KEY_PAGE
from data_loader import load_data, update_latest_announcement
from views.dashboard import render_dashboard
from views.g1 import render_g1

st.set_page_config(layout="wide")

def main():
    if not EXCEL_PATH.exists():
        st.error(f"Excel ファイルが見つかりません: {EXCEL_PATH}")
        return

    if "did_update_latest_announcement" not in st.session_state:
        updated, message = update_latest_announcement(EXCEL_PATH)
        st.session_state["did_update_latest_announcement"] = True
        if message:
            if updated:
                st.info(message)
            else:
                st.warning(message)

    df_list, df_q = load_data(EXCEL_PATH)

    if SESSION_KEY_PAGE not in st.session_state:
        st.session_state[SESSION_KEY_PAGE] = DEFAULT_PAGE

    page = st.session_state[SESSION_KEY_PAGE]

    if page == "dashboard":
        render_dashboard(df_list)
    elif page == "g1":
        render_g1(df_q)
    else:
        st.session_state[SESSION_KEY_PAGE] = DEFAULT_PAGE
        render_dashboard(df_list)


if __name__ == "__main__":
    main()
