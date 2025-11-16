from pathlib import Path
import re

import pandas as pd
import streamlit as st

from config import EXCEL_PATH


def parse_period_to_order(s: str | None) -> int | None:
    """
    決算期文字列からソート用の数値キーを作る。

    例:
      '24/1Q'   -> 20241
      '2024Q3'  -> 20243
      '2025/4Q' -> 20254
    """
    if s is None:
        return None

    text = str(s)
    match = re.search(r"(\d{2,4}).*?([1-4])Q", text)
    if not match:
        return None

    year = int(match.group(1))
    if year < 100:
        year += 2000

    quarter = int(match.group(2))
    return year * 10 + quarter


@st.cache_data(show_spinner=False)
def load_data(excel_path: Path = EXCEL_PATH):
    """Excel の銘柄一覧・業績を読み込む。"""
    xls = pd.ExcelFile(excel_path)
    df_list = pd.read_excel(xls, "銘柄一覧")
    df_q = pd.read_excel(xls, "業績")

    if "証券コード" in df_list.columns:
        df_list["証券コード"] = df_list["証券コード"].astype(str)
    if "証券コード" in df_q.columns:
        df_q["証券コード"] = df_q["証券コード"].astype(str)

    for col in ["決算期末日", "決算発表日"]:
        if col in df_q.columns:
            df_q[col] = pd.to_datetime(df_q[col], errors="coerce")

    # 決算期のソートキーを事前に計算しておく
    if "決算期" in df_q.columns:
        df_q["期順"] = df_q["決算期"].apply(parse_period_to_order)

    if all(col in df_q.columns for col in ["証券コード", "決算期末日"]):
        df_q = df_q.sort_values(["証券コード", "決算期末日"])

    return df_list, df_q
