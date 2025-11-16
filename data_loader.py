from pathlib import Path
import re

import pandas as pd
import streamlit as st
from openpyxl import load_workbook

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

    # IRリンク列がハイパーリンクの場合にターゲットURLを補完し、http(s)以外は無効化
    try:
        # ハイパーリンク取得には read_only=False が必要
        wb = load_workbook(excel_path, read_only=False, data_only=True)
        if "業績" in wb.sheetnames:
            ws = wb["業績"]
            header = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            if "IRリンク" in header:
                col_idx = header.index("IRリンク") + 1
                links: list[str | None] = []

                def normalize(link_val):
                    if not link_val:
                        return None
                    s = str(link_val).strip()
                    if s.startswith("#"):  # シート内リンクは除外
                        return None
                    if not s.lower().startswith(("http://", "https://")):
                        return None
                    return s

                for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                    cell = row[0]
                    link = None
                    if cell.hyperlink:
                        link = cell.hyperlink.target
                    elif cell.value:
                        link = cell.value
                    links.append(normalize(link))
                if len(links) == len(df_q):
                    df_q["IRリンク"] = links
    except Exception:
        pass

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
