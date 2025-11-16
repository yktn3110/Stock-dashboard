import pandas as pd
import plotly.express as px
import streamlit as st

from config import SESSION_KEY_PAGE, SESSION_KEY_SELECTED_CODE
from data_loader import parse_period_to_order


def render_g1(df_q):
    st.title("G1: 四半期業績ビュー")

    code = st.session_state.get(SESSION_KEY_SELECTED_CODE)
    if code is None:
        st.warning("銘柄が選択されていません。ダッシュボードから銘柄を選んでください。")
        if st.button("↩ ダッシュボードに戻る"):
            st.session_state[SESSION_KEY_PAGE] = "dashboard"
        return

    df_sel = df_q[df_q["証券コード"] == code].copy()

    # ロード時に期順を付与しているが、念のため未計算ならここで付与
    if "期順" not in df_sel.columns:
        df_sel["期順"] = df_sel["決算期"].apply(parse_period_to_order)

    df_sel = df_sel[df_sel["期順"].notna()].sort_values("期順")

    if df_sel.empty:
        st.warning(f"銘柄 {code} の四半期データがありません。")
        if st.button("↩ ダッシュボードに戻る"):
            st.session_state[SESSION_KEY_PAGE] = "dashboard"
        return

    name = df_sel["銘柄名"].iloc[0] if "銘柄名" in df_sel.columns else ""

    if st.button("↩ ダッシュボードに戻る"):
        st.session_state[SESSION_KEY_PAGE] = "dashboard"
        return

    st.subheader(f"{code} {name} の四半期業績")

    with st.expander("四半期データをテーブル表示", expanded=False):
        cols = [
            "決算期",
            "決算期末日",
            "売上高（四半期）",
            "営業利益（四半期）",
            "EPS（四半期）",
            "決算評価（◎○△×）",
            "メモ",
        ]
        cols = [c for c in cols if c in df_sel.columns]
        st.dataframe(df_sel[cols])

    st.markdown("### 四半期業績グラフ (G1)")

    metric_map = {
        "売上高（四半期）": "売上高（四半期）",
        "営業利益（四半期）": "営業利益（四半期）",
        "EPS（四半期）": "EPS（四半期）",
    }

    available_metrics = [label for label, col in metric_map.items() if col in df_sel.columns]
    if not available_metrics:
        st.error("表示できる数値データがありません。")
        return

    metric_label = st.radio(
        "表示する指標を選択",
        available_metrics,
        index=min(1, len(available_metrics) - 1),
        horizontal=True,
    )
    metric_col = metric_map[metric_label]

    x_col = "決算期末日" if "決算期末日" in df_sel.columns and df_sel["決算期末日"].notna().any() else "決算期"
    df_sel[metric_col] = pd.to_numeric(df_sel[metric_col], errors="coerce")

    fig = px.line(
        df_sel,
        x=x_col,
        y=metric_col,
        markers=True,
        title=f"{code} {name} - {metric_label} の推移",
    )
    fig.update_layout(xaxis_title="決算期", yaxis_title=metric_label)

    st.plotly_chart(fig, use_container_width=True)
