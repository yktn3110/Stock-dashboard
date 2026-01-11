import streamlit as st

from config import SESSION_KEY_PAGE, SESSION_KEY_SELECTED_CODE


def render_dashboard(df_list, df_q):
    st.title("銘柄ダッシュボード")

    df_view = df_list.copy()

    st.subheader("銘柄一覧")
    st.dataframe(df_view)

    st.markdown("### 詳細を見たい銘柄を選択")

    if "証券コード" not in df_view.columns or df_view.empty:
        st.info("条件に合う銘柄がありません。フィルタを調整してください。")
        return

    codes = df_view["証券コード"].unique()
    selected_code = st.selectbox("証券コード", codes)

    row = df_list[df_list["証券コード"] == selected_code].iloc[0]
    name = row.get("銘柄名", "")

    st.write(f"選択中: **{selected_code} {name}**")

    cols = st.columns(3)
    with cols[0]:
        st.metric("現在株価", row.get("現在株価", "N/A"))
    with cols[1]:
        st.metric("PER", row.get("PER", "N/A"))
    with cols[2]:
        st.metric("PBR", row.get("PBR", "N/A"))

    if st.button("業績を見る"):
        st.session_state[SESSION_KEY_PAGE] = "g1"
        st.session_state[SESSION_KEY_SELECTED_CODE] = selected_code
