import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

EXCEL_PATH = Path("data/portfolio.xlsx")


def parse_period_to_order(s: str) -> int | None:
    """
    決算期文字列から「ソート用の数値キー」を作る。
    例:
      '24/1Q'   -> 20241
      '2024Q3'  -> 20243
      '2025/4Q' -> 20254
    """
    if s is None:
        return None
    s = str(s)

    m = re.search(r'(\d{2,4}).*?([1-4])Q', s)
    if not m:
        return None

    year = int(m.group(1))
    # 2桁なら 20xx とみなす（24 -> 2024）
    if year < 100:
        year += 2000

    q = int(m.group(2))
    return year * 10 + q



# ---------- データ読み込み ----------

@st.cache_data
def load_data():
    xls = pd.ExcelFile(EXCEL_PATH)
    df_list = pd.read_excel(xls, "銘柄一覧")
    df_q = pd.read_excel(xls, "四半期業績")

    # 型整理
    if "証券コード" in df_list.columns:
        df_list["証券コード"] = df_list["証券コード"].astype(str)
    if "証券コード" in df_q.columns:
        df_q["証券コード"] = df_q["証券コード"].astype(str)

    for col in ["決算期末日", "決算発表日"]:
        if col in df_q.columns:
            df_q[col] = pd.to_datetime(df_q[col], errors="coerce")

    if "決算期末日" in df_q.columns:
        df_q = df_q.sort_values(["証券コード", "決算期末日"])

    return df_list, df_q


# ---------- ダッシュボード画面 ----------

def render_dashboard(df_list, df_q):
    st.title("銘柄ダッシュボード")

    st.sidebar.header("フィルター")

    # セクター・投資判断でフィルタする例（列名は手元のExcelに合わせて修正）
    sector_sel = st.sidebar.multiselect(
        "セクター",
        sorted(df_list["セクター"].dropna().unique()) if "セクター" in df_list.columns else []
    )
    judge_sel = st.sidebar.multiselect(
        "投資判断",
        sorted(df_list["投資判断"].dropna().unique()) if "投資判断" in df_list.columns else []
    )

    df_view = df_list.copy()
    if sector_sel and "セクター" in df_view.columns:
        df_view = df_view[df_view["セクター"].isin(sector_sel)]
    if judge_sel and "投資判断" in df_view.columns:
        df_view = df_view[df_view["投資判断"].isin(judge_sel)]

    st.subheader("銘柄一覧")
    st.dataframe(df_view)

    # 銘柄選択
    st.markdown("### 詳細を見たい銘柄を選択")

    codes = df_view["証券コード"].unique()
    if len(codes) == 0:
        st.info("条件に合う銘柄がありません。フィルタを調整してください。")
        return

    selected_code = st.selectbox("証券コード", codes)

    row = df_list[df_list["証券コード"] == selected_code].iloc[0]
    name = row.get("銘柄名", "")

    st.write(f"選択中: **{selected_code} {name}**")

    # ここで簡単なサマリ（お好みで）
    cols = st.columns(3)
    with cols[0]:
        st.metric("現在株価", row.get("現在株価", "N/A"))
    with cols[1]:
        st.metric("PER", row.get("PER", "N/A"))
    with cols[2]:
        st.metric("PBR", row.get("PBR", "N/A"))

    # === G1 へ遷移するボタン ===
    if st.button("四半期業績を見る（G1）"):
        st.session_state["page"] = "g1"
        st.session_state["selected_code"] = selected_code


# ---------- G1 画面（四半期業績） ----------

def render_g1(df_q):
    st.title("G1: 四半期業績ビュー")

    # 遷移元で選ばれた銘柄コードを取得
    code = st.session_state.get("selected_code")
    if code is None:
        st.warning("銘柄が選択されていません。ダッシュボードから銘柄を選んでください。")
        if st.button("← ダッシュボードに戻る"):
            st.session_state["page"] = "dashboard"
        return

   
    df_sel = df_q[df_q["証券コード"] == code].copy()

    # 決算期からソートキー作成
    df_sel["期順"] = df_sel["決算期"].apply(parse_period_to_order)

    # ソートキーが取れた行だけ残す（変な文字列は除外）
    df_sel = df_sel[df_sel["期順"].notna()].sort_values("期順")

    # x 軸は常に「決算期」の文字列を使う
    x_col = "決算期" 

    if df_sel.empty:
        st.warning(f"銘柄 {code} の四半期データがありません。")
        if st.button("← ダッシュボードに戻る"):
            st.session_state["page"] = "dashboard"
        return

    name = df_sel["銘柄名"].iloc[0] if "銘柄名" in df_sel.columns else ""

    # 戻るボタン
    if st.button("← ダッシュボードに戻る"):
        st.session_state["page"] = "dashboard"
        return

    st.subheader(f"{code} {name} の四半期業績")

    # テーブル表示（確認用）
    with st.expander("四半期データ（テーブル表示）", expanded=False):
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

    # G1 グラフ
    st.markdown("### 四半期業績グラフ（G1）")

    metric_map = {
        "売上高（四半期）": "売上高（四半期）",
        "営業利益（四半期）": "営業利益（四半期）",
        "EPS（四半期）": "EPS（四半期）",
    }

    metric_label = st.radio(
        "表示する指標を選択",
        list(metric_map.keys()),
        index=1,
        horizontal=True,
    )
    metric_col = metric_map[metric_label]

    # X軸
    if "決算期末日" in df_sel.columns and df_sel["決算期末日"].notna().any():
        x_col = "決算期末日"
    else:
        x_col = "決算期"

    df_sel[metric_col] = pd.to_numeric(df_sel[metric_col], errors="coerce")

    fig = px.line(
    df_sel,
    x=x_col,           # ← 決算期（文字列）
    y=metric_col,
    markers=True,
    title=f"{code} {name} - {metric_label} の推移",
)
    fig.update_layout(xaxis_title="決算期", yaxis_title=metric_label)

    st.plotly_chart(fig, use_container_width=True)


# ---------- メイン ----------

def main():
    if not EXCEL_PATH.exists():
        st.error(f"Excel ファイルが見つかりません: {EXCEL_PATH}")
        return

    df_list, df_q = load_data()

    # ページ状態の初期化
    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"

    page = st.session_state["page"]

    if page == "dashboard":
        render_dashboard(df_list, df_q)
    elif page == "g1":
        render_g1(df_q)
    else:
        st.session_state["page"] = "dashboard"
        render_dashboard(df_list, df_q)


if __name__ == "__main__":
    main()
