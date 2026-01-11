import streamlit as st

from config import SESSION_KEY_PAGE, SESSION_KEY_SELECTED_CODE
from data_loader import get_current_price, normalize_ticker


def render_dashboard(df_list, df_q):
    st.title("銘柄ダッシュボード")

    df_view = df_list.copy()

    st.subheader("銘柄一覧")
    table_selection = st.dataframe(
        df_view,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="list_table",
    )

    st.markdown("### 詳細を見たい銘柄を選択")

    if "証券コード" not in df_view.columns or df_view.empty:
        st.info("条件に合う銘柄がありません。フィルタを調整してください。")
        return

    if table_selection and table_selection.selection.rows:
        row_idx = table_selection.selection.rows[0]
        selected_code_from_table = df_view.iloc[row_idx]["証券コード"]
        st.session_state[SESSION_KEY_SELECTED_CODE] = selected_code_from_table

    codes = df_view["証券コード"].unique().tolist()
    if (
        SESSION_KEY_SELECTED_CODE not in st.session_state
        or st.session_state[SESSION_KEY_SELECTED_CODE] not in codes
    ):
        st.session_state[SESSION_KEY_SELECTED_CODE] = codes[0]

    selected_code = st.selectbox("証券コード", codes, key=SESSION_KEY_SELECTED_CODE)

    row = df_list[df_list["証券コード"] == selected_code].iloc[0]
    name = row.get("銘柄名", "")

    st.write(f"選択中: **{selected_code} {name}**")

    ticker = normalize_ticker(selected_code)
    with st.spinner("現在株価を取得中..."):
        current_price = get_current_price(ticker)

    cols = st.columns(3)
    with cols[0]:
        price_value = current_price if current_price is not None else row.get("現在株価", "N/A")
        st.metric("現在株価", price_value)
    with cols[1]:
        st.metric("PER", row.get("PER", "N/A"))
    with cols[2]:
        st.metric("PBR", row.get("PBR", "N/A"))

    if st.button("業績を見る"):
        st.session_state[SESSION_KEY_PAGE] = "g1"
        st.rerun()
