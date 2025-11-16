import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from config import SESSION_KEY_PAGE, SESSION_KEY_SELECTED_CODE
from data_loader import parse_period_to_order


def render_g1(df_q):
    st.title("業績グラフ")

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
    df_sel["年度"] = (df_sel["期順"] // 10).astype(int)
    # 前年同四半期比較と通期進捗率を計算（分母欠損や0はNaNのまま）
    if {"売上高（四半期）", "営業利益（四半期）", "EPS（四半期）"}.issubset(df_sel.columns):
        df_tmp = df_sel.copy()
        df_tmp["四半期番号"] = df_tmp["期順"] % 10

        def yoy(current, prev):
            if pd.isna(prev) or prev == 0:
                return pd.NA
            return (current - prev) / prev * 100

        for src_col, dst_col in [
            ("売上高（四半期）", "売上高前年比(%)"),
            ("営業利益（四半期）", "営業利益前年比(%)"),
            ("EPS（四半期）", "EPS前年比(%)"),
        ]:
            if src_col not in df_tmp.columns:
                continue
            prev = (
                df_tmp
                .set_index(["年度", "四半期番号"])[src_col]
                .reindex([(y - 1, q) for y, q in df_tmp[["年度", "四半期番号"]].to_records(index=False)])
                .to_numpy()
            )
            df_tmp[dst_col] = [
                yoy(cur, prv) if pd.notna(cur) else pd.NA
                for cur, prv in zip(df_tmp[src_col].to_numpy(), prev)
            ]

        # 進捗率: 当年度の通期予想があれば累積実績で計算
        for val_col, cum_col, target_col in [
            ("売上高（四半期）", "売上累計", "売上進捗率(%)"),
            ("営業利益（四半期）", "営利累計", "営業利益進捗率(%)"),
        ]:
            if val_col not in df_tmp.columns:
                continue
            df_tmp[cum_col] = df_tmp.groupby("年度")[val_col].cumsum()
            total_col = "通期売上予想（実績）" if "売上" in val_col else "通期営業利益予想"
            if total_col in df_tmp.columns:
                total = df_tmp[total_col].to_numpy()
                df_tmp[target_col] = [
                    (cum / tgt * 100) if pd.notna(cum) and pd.notna(tgt) and tgt != 0 else pd.NA
                    for cum, tgt in zip(df_tmp[cum_col].to_numpy(), total)
                ]
        df_sel = df_tmp.drop(columns=["四半期番号", "売上累計", "営利累計"], errors="ignore")

    if df_sel.empty:
        st.warning(f"銘柄 {code} のデータがありません。")
        if st.button("↩ ダッシュボードに戻る"):
            st.session_state[SESSION_KEY_PAGE] = "dashboard"
        return

    name = df_sel["銘柄名"].iloc[0] if "銘柄名" in df_sel.columns else ""

    if st.button("↩ ダッシュボードに戻る"):
        st.session_state[SESSION_KEY_PAGE] = "dashboard"
        return

    st.subheader(f"{code} {name} の業績推移")

    with st.expander("業績データをテーブル表示", expanded=False):
        cols = [
            "決算期",
            "売上高（四半期）",
            "営業利益（四半期）",
            "EPS（四半期）",
            "決算評価（◎○△×）",
            "メモ",
            "売上高前年比(%)",
            "営業利益前年比(%)",
            "EPS前年比(%)",
            "売上進捗率(%)",
            "営業利益進捗率(%)",
        ]
        cols = [c for c in cols if c in df_sel.columns]
        df_display = df_sel.sort_values("期順", ascending=False)[cols].copy()
        percent_cols = [
            "売上高前年比(%)",
            "営業利益前年比(%)",
            "EPS前年比(%)",
            "売上進捗率(%)",
            "営業利益進捗率(%)",
        ]
        for c in percent_cols:
            if c in df_display.columns:
                df_display[c] = pd.to_numeric(df_display[c], errors="coerce").round(1)
        st.dataframe(df_display, hide_index=True)

    st.markdown("### 業績グラフ")

    col_interval, col_period = st.columns(2)
    with col_interval:
        interval_label = st.radio(
            "表示区間",
            ["四半期", "年度"],
            horizontal=True,
        )
    with col_period:
        period_label = st.radio(
            "表示期間",
            ["1年", "3年", "5年"],
            index=1,
            horizontal=True,
        )
        display_years = int(period_label.replace("年", ""))

    quarterly_metric_map = {
        "売上高（四半期）": "売上高（四半期）",
        "営業利益（四半期）": "営業利益（四半期）",
        "EPS（四半期）": "EPS（四半期）",
    }
    annual_metric_map = {
        "売上高（通期）": "通期売上予想（実績）",
        "営業利益（通期）": "通期営業利益予想",
        "EPS（通期）": "通期EPS予想",
    }
    metric_map = annual_metric_map if interval_label == "年度" else quarterly_metric_map

    available_metrics = [label for label, col in metric_map.items() if col in df_sel.columns]
    if not available_metrics:
        st.error("表示できる数値データがありません。")
        return

    default_selection = available_metrics[:2] if len(available_metrics) >= 2 else available_metrics

    st.write("表示する指標を選択（トグルで複数可）")
    toggle_cols = st.columns(min(4, len(available_metrics)) or 1)
    selected_metrics: list[str] = []
    for idx, label in enumerate(available_metrics):
        col = toggle_cols[idx % len(toggle_cols)]
        with col:
            on_by_default = label in default_selection
            if st.toggle(label, value=on_by_default, key=f"metric_toggle_{label}"):
                selected_metrics.append(label)

    if not selected_metrics:
        st.info("表示する指標を選んでください。")
        return

    selected_cols = [metric_map[label] for label in selected_metrics]
    for col in selected_cols:
        df_sel[col] = pd.to_numeric(df_sel[col], errors="coerce")

    df_plot = df_sel.dropna(subset=selected_cols, how="all").copy()
    if interval_label == "年度":
        # 年度表示時は通期の値を利用し、同一年度の最新四半期行を採用
        df_plot = df_plot.sort_values(["年度", "期順"]).groupby("年度").tail(1)
        x_col = "年度"
    else:
        x_col = "決算期" if "決算期" in df_plot.columns else "期順"

    if not df_plot.empty:
        if interval_label == "年度":
            last_year = int(df_plot["年度"].max())
            start_year = last_year - display_years + 1
            df_plot = df_plot[df_plot["年度"] >= start_year]
        else:
            # 四半期表示時は最新期順から年数分×4四半期を表示
            last_order = int(df_plot["期順"].max())
            start_order = last_order - display_years * 4 + 1
            df_plot = df_plot[df_plot["期順"] >= start_order]
        df_plot = df_plot.sort_values("期順")

    if df_plot.empty:
        st.warning("選択した表示期間と区間にデータはありません。")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    memo_values = None
    if "メモ" in df_plot.columns:
        memo_values = df_plot["メモ"].fillna("").replace("", pd.NA).to_numpy()

    for idx, label in enumerate(selected_metrics):
        col = metric_map[label]
        hovertext = None
        if memo_values is not None:
            xs = df_plot[x_col].to_numpy()
            ys = df_plot[col].to_numpy()
            hovertext = []
            for x_val, y_val, m in zip(xs, ys, memo_values):
                base = f"{x_col}={x_val}<br>{label}={y_val}"
                if pd.notna(m):
                    base += f"<br>メモ={m}"
                hovertext.append(base)

        fig.add_trace(
            go.Scatter(
                x=df_plot[x_col],
                y=df_plot[col],
                mode="lines+markers",
                name=label,
                text=hovertext,
                hovertemplate="%{text}<extra></extra>" if hovertext is not None else None,
            ),
            secondary_y=idx > 0,
        )

    primary_title = selected_metrics[0]
    secondary_title = selected_metrics[1] if len(selected_metrics) > 1 else None
    fig.update_layout(
        title=f"{code} {name} - 指標推移",
        xaxis_title="決算期" if interval_label == "四半期" else "年度",
        legend_title="指標",
    )
    fig.update_yaxes(title_text=primary_title, secondary_y=False)
    if secondary_title:
        fig.update_yaxes(title_text=secondary_title, secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)
