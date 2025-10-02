# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# --- ページ設定（ブラウザタブ） ---
st.set_page_config(
    page_title="業種別騰落率比較",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

# --- ページタイトル ---
st.title("騰落率　業種別比較")
st.markdown("プルダウンで業種を選んでください。")

# --- セクター辞書 ---
SECTORS = {
    "エネルギー": {
        "1605.T": "1605 INPEX",
        "1662.T": "1662 JAPEX",
        "5020.T": "5020 ENEOS",
        "5019.T": "5019 出光興産",
        "5021.T": "5021 コスモエネルギー",
    },
    "商社": {
        "8001.T": "8001 伊藤忠商事",
        "8002.T": "8002 丸紅",
        "8015.T": "8015 豊田通商",
        "8031.T": "8031 三井物産",
        "8053.T": "8053 住友商事",
        "8058.T": "8058 三菱商事",
    }
}

# --- 表示期間マップ ---
period_map = {
    "1か月": "1mo",
    "3か月": "3mo",
    "6か月": "6mo",
    "1年": "1y",
    "5年": "5y",
    "10年": "10y",
    "20年": "20y",
}

# --- 横並びに配置 ---
col1, col2, col3 = st.columns([1, 4, 1])

with col1:
    sector = st.selectbox("セクター", list(SECTORS.keys()))

STOCKS = SECTORS[sector]
DEFAULT_STOCKS = list(STOCKS.keys())

if "tickers_input" not in st.session_state or st.session_state.get("last_sector") != sector:
    st.session_state.tickers_input = DEFAULT_STOCKS
    st.session_state.last_sector = sector

with col2:
    tickers = st.multiselect(
        "銘柄",
        options=list(STOCKS.keys()),
        format_func=lambda x: STOCKS[x],
        default=st.session_state.tickers_input,
        placeholder="例: ENEOS",
    )

with col3:
    horizon = st.radio(
        "表示期間",
        options=list(period_map.keys()),
        index=list(period_map.keys()).index("6か月"),
    )

# 選択状態を保持
st.session_state.tickers_input = tickers
tickers = [t.upper() for t in tickers]

if not tickers:
    st.warning("比較する銘柄を選択してください")
    st.stop()

# --- データ取得 ---
@st.cache_data(show_spinner=False)
def load_data(tickers, period):
    tickers_obj = yf.Tickers(tickers)
    data = tickers_obj.history(period=period)
    if data is None:
        raise RuntimeError("YFinance returned no data.")
    data = data["Close"].ffill().dropna(how="all", axis=1)
    return data

try:
    data = load_data(tickers, period_map[horizon])
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの制限が発生しました。時間をおいて再試行してください。")
    load_data.clear_cache()
    st.stop()

empty_columns = data.columns[data.isna().all()].tolist()
if empty_columns:
    st.error(f"データを取得できなかった銘柄: {', '.join(empty_columns)}")
    st.stop()

# --- 騰落率 (%) に変換 ---
returns = (data / data.iloc[0] - 1) * 100
returns = returns.rename(columns=STOCKS)

# --- 騰落率チャート ---
st.subheader("騰落率、Return (%)")
st.altair_chart(
    alt.Chart(
        returns.reset_index().melt(id_vars=["Date"], var_name="Stock", value_name="Return (%)")
    )
    .mark_line()
    .encode(
        alt.X("Date:T", axis=alt.Axis(title=None)),
        alt.Y("Return (%):Q", axis=alt.Axis(title=None)),
        alt.Color(
            "Stock:N",
            legend=alt.Legend(title=None) 
        ),
    )
    .properties(height=400),
    use_container_width=True
)

# --- 個別銘柄 vs 他社平均 ---
st.subheader("銘柄 vs 他社平均")
if len(returns.columns) <= 1:
    st.warning("2銘柄以上を選択してください")
    st.stop()

NUM_COLS = 4
cols = st.columns(NUM_COLS)

for i, company in enumerate(returns.columns):
    peers = returns.drop(columns=[company])
    peer_avg = peers.mean(axis=1)

    # 個別銘柄 vs 平均
    plot_data = pd.DataFrame(
        {"Date": returns.index, company: returns[company], "Peer average": peer_avg}
    ).melt(id_vars=["Date"], var_name="Series", value_name="Return (%)")

    chart = (
        alt.Chart(plot_data)
        .mark_line()
        .encode(
            alt.X("Date:T", axis=alt.Axis(title=None)),         
            alt.Y("Return (%):Q", axis=alt.Axis(title=None)),  
            alt.Color(
                "Series:N",
                scale=alt.Scale(domain=[company, "Peer average"], range=["red", "gray"]),
                legend=None
            ),
            alt.Tooltip(["Date", "Series", "Return (%)"]),
        )
        .properties(title=f"{company} vs 他社平均", height=300)
    )

    cell = cols[(i * 2) % NUM_COLS].container()
    cell.write("")
    cell.altair_chart(chart, use_container_width=True)

    # 差分チャート
    plot_data = pd.DataFrame({"Date": returns.index, "Delta": returns[company] - peer_avg})
    chart = (
        alt.Chart(plot_data)
        .mark_area(color="lightblue")
        .encode(
            alt.X("Date:T", axis=alt.Axis(title=None)),
            alt.Y("Delta:Q", axis=alt.Axis(title=None)),
        )
        .properties(title=f"{company} と他社との差", height=300)
    )

    cell = cols[(i * 2 + 1) % NUM_COLS].container()
    cell.write("")
    cell.altair_chart(chart, use_container_width=True)

# --- 株価チャート ---
st.subheader("株価推移")
NUM_COLS_PRICE = 2
price_cols = st.columns(NUM_COLS_PRICE)
for i, ticker in enumerate(data.columns):
    company_name = STOCKS.get(ticker, ticker)
    plot_data = pd.DataFrame({"Date": data.index, "Price": data[ticker]})
    chart = (
        alt.Chart(plot_data)
        .mark_line(color="#1f77b4")
        .encode(
            alt.X("Date:T"),
            alt.Y("Price:Q").scale(zero=False),
            alt.Tooltip(["Date","Price"]),
        )
        .properties(title=f"{company_name} 株価推移", height=250)
    )
    cell = price_cols[i % NUM_COLS_PRICE].container()
    cell.altair_chart(chart, use_container_width=True)

# --- Raw data 表示 ---
st.subheader("Raw data")
st.dataframe(returns)

# --- requirements.txt ---
# streamlit
# yfinance
# pandas
# altair
