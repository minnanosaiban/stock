# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt

# --- ページ設定 ---
st.set_page_config(
    page_title="業種別騰落率比較",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

# --- ページタイトル ---
st.title("セクター別分析")

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
    },
    "通信": {
        "9432.T": "9432 NTT",
        "9433.T": "9433 KDDI",
        "9434.T": "9434 ソフトバンク",
        "9435.T": "9435 光通信",
    },
    "電気製品": {
        "6503.T": "6503 三菱電機",
        "6758.T": "6758 ソニーG",
        "6752.T": "6752 パナソニックHD",
        "6701.T": "6701 NEC",
        "6702.T": "6702 富士通",
    },
    "自動車": {
        "7201.T": "7201 日産自動車",
        "7202.T": "7202 いすゞ自動車",
        "7203.T": "7203 トヨタ自動車",
        "7267.T": "7267 ホンダ",
        "7269.T": "7269 スズキ",
        "7270.T": "7270 SUBARU",
    },
    "銀行": {
        "5838.T": "5838 楽天銀行",
        "7182.T": "7182 ゆうちょ銀行",
        "8306.T": "8306 三菱UFJ FG",
        "8316.T": "8316 三井住友 FG",
        "8411.T": "8411 みずほ FG",
        "8309.T": "8309 三井住友トラストHD",
        "8410.T": "8410 セブン銀行",
    },
    "化学": {
        "3402.T": "3402 東レ",
        "3407.T": "3407 旭化成",
        "4004.T": "4004 昭和電工",
        "4005.T": "4005 住友化学",
        "4063.T": "4063 信越化学工業",
        "4188.T": "4188 三菱ケミカルG",
        "4208.T": "4208 ＵＢＥ",
        "5201.T": "5201 ＡＧＣ",
    },
    "医薬品": {
        "4502.T": "4502 武田薬品工業",
        "4503.T": "4503 アステラス製薬",
        "4519.T": "4519 中外製薬",
        "4543.T": "4543 テルモ",
        "4568.T": "4568 第一三共",
    },
    "流通": {
        "3382.T": "3382 セブン&アイ",
        "3391.T": "3391 ツルハＨＤ",
        "7453.T": "7453 良品計画",
        "8267.T": "8267 イオン",
        "9843.T": "9843 ニトリ",
    },
    "住宅": {
        "1928.T": "1928 積水ハウス",
        "1925.T": "1925 大和ハウス工業",
        "1926.T": "1926 ライト工業",
        "1963.T": "1963 日揮HD",
    },
    "建設": {
        "1802.T": "1802 大林組",
        "1803.T": "1803 清水建設",
        "1801.T": "1801 大成建設",
        "1812.T": "1812 鹿島建設",
        "1821.T": "1821 三井住友建設",
    },
}

# 騰落率平均比較チャートで使用する固定期間
COMPARISON_PERIODS = {
    "1か月": "1mo",
    "1年": "1y",
    "3年": "3y",
    "5年": "5y",
}

# --- 表示期間マップ ---
period_map = {
    "5日": "5d",
    "1か月": "1mo",
    "3か月": "3mo",
    "6か月": "6mo",
    "1年": "1y",
    "3年": "3y",
    "5年": "5y",
    "10年": "10y",
    "20年": "20y",
}

# -----------------------------------------------------------------------
## セクターと銘柄の選択
# -----------------------------------------------------------------------
col_sector, col_tickers = st.columns([1, 4])

with col_sector:
    sector = st.selectbox("セクター", list(SECTORS.keys()))

STOCKS = SECTORS[sector]
DEFAULT_STOCKS = list(STOCKS.keys())

# セクター変更時にデフォルト復帰
if "tickers_input" not in st.session_state or st.session_state.get("last_sector") != sector:
    st.session_state.tickers_input = DEFAULT_STOCKS
    st.session_state.last_sector = sector

with col_tickers:
    tickers = st.multiselect(
        "銘柄",
        options=list(STOCKS.keys()),
        format_func=lambda x: STOCKS[x],
        default=st.session_state.tickers_input,
        placeholder="例: ENEOS",
    )

st.session_state.tickers_input = tickers
tickers = [t.upper() for t in tickers]

if not tickers:
    st.warning("比較する銘柄を選択してください")
    st.stop()

# -----------------------------------------------------------------------
## YFinanceデータの計算 (関数定義)
# -----------------------------------------------------------------------

# --- Financeデータの取得 ---
@st.cache_data(show_spinner=False)
def load_data(tickers, period):
    tickers_obj = yf.Tickers(tickers)
    data = tickers_obj.history(period=period)
    if data is None:
        raise RuntimeError("YFinance returned no data.")
    # 複数カラムがある場合は"Close"を選択、1銘柄の場合はそのまま
    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]
    data = data.ffill().dropna(how="all", axis=1)
    return data

# FutureWarningを解消するため、auto_adjust=Falseを明示的に指定
@st.cache_data(show_spinner=False)
def load_nikkei(period):
    data = yf.download("^N225", period=period, auto_adjust=False)["Close"].ffill()
    return data.squeeze()

# --- 固定期間のデータ取得と騰落率計算 ---
@st.cache_data(show_spinner=False)
def load_comparison_returns(tickers):
    comparison_returns = {}
    nikkei_comparison_returns = {}
    for label, period in COMPARISON_PERIODS.items():
        try:
            # 銘柄データ
            data = load_data(tickers, period)
            returns = (data / data.iloc[0] - 1) * 100
            # カラム名をティッカーから会社名に変換
            returns.columns = [STOCKS.get(t, t) for t in returns.columns]
            comparison_returns[label] = returns
            # 日経平均データ
            nikkei_data = load_nikkei(period)
            nikkei_returns = (nikkei_data / nikkei_data.iloc[0] - 1) * 100
            nikkei_comparison_returns[label] = nikkei_returns
        except Exception as e:
            # 警告を少し控えめにする
            # st.warning(f"期間 {label} のデータ取得中にエラー: {e}") 
            continue
    return comparison_returns, nikkei_comparison_returns

# -----------------------------------------------------------------------
## 騰落率推移チャート
# -----------------------------------------------------------------------
st.subheader("騰落率推移チャート %")
st.markdown(
    """
    <div style="font-size:14px; margin-top:-10px;">
        <span style="color:#9BB7D0; font-weight:bold;">■ 日経平均</span>　
        <span style="color:#D3D3D3; font-weight:bold;">■ セクター他社平均</span>
    </div>
    """,
    unsafe_allow_html=True
)

if len(tickers) <= 1:
    st.warning("2銘柄以上を選択してください")

# 固定期間の騰落率データを取得
comparison_returns_data, nikkei_comparison_returns_data = load_comparison_returns(tickers)

# len(tickers) <= 1 の場合はここでチャート描画をスキップ
if len(tickers) > 1 and comparison_returns_data:
    # --- 期間ごとの全体のY軸範囲を計算 (目盛統一のため) ---
    period_domains = {}

    for period_label, period_data in comparison_returns_data.items():
        if not period_data.empty:
            
            # 1. 全銘柄の最小・最大
            min_return = period_data.min().min()
            max_return = period_data.max().max()
            
            # 2. ピア平均の最小・最大（すべての銘柄をドロップして平均を計算）
            all_peers_min = float('inf')
            all_peers_max = float('-inf')
            
            # 比較対象の銘柄が複数ある場合にのみピア平均を考慮
            if len(period_data.columns) > 1:
                for current_company in period_data.columns:
                    # 自分の銘柄を除いた平均 (ピア平均) を計算
                    peers = period_data.drop(columns=[current_company], errors='ignore')
                    if not peers.empty:
                        peer_avg = peers.mean(axis=1)
                        all_peers_min = min(all_peers_min, peer_avg.min())
                        all_peers_max = max(all_peers_max, peer_avg.max())

            # 3. 日経平均の最小・最大
            nikkei_data = nikkei_comparison_returns_data.get(period_label)
            nikkei_min = nikkei_data.min() if nikkei_data is not None and not nikkei_data.empty else float('inf')
            nikkei_max = nikkei_data.max() if nikkei_data is not None and not nikkei_data.empty else float('-inf')

            # 4. 全体の最小・最大を決定
            current_min = min(min_return, all_peers_min if all_peers_min != float('inf') else min_return, nikkei_min)
            current_max = max(max_return, all_peers_max if all_peers_max != float('-inf') else max_return, nikkei_max)

            # 5. グラフの見栄えを良くするため、少し余裕を持たせる（5%）
            padding = (current_max - current_min) * 0.05
            current_min -= padding
            current_max += padding

            # 6. 0ラインをまたぐ場合は0を含めるように調整
            if current_min > 0: current_min = 0
            if current_max < 0: current_max = 0
            
            period_domains[period_label] = [current_min, current_max]
        else:
            # データがない場合のデフォルト
            period_domains[period_label] = [-10, 10] 

    # 会社ごとの比較チャートを描画
    for company_ticker in tickers:
        company_name = STOCKS.get(company_ticker, company_ticker)
        
        st.markdown(f"### {company_name}") # 会社名の見出し

        NUM_COLS = len(COMPARISON_PERIODS) # 4つ（1か月, 1年, 3年, 5年）
        cols = st.columns(NUM_COLS)

        # 固定期間ごとにチャートを描画
        for i, (period_label, period_data) in enumerate(comparison_returns_data.items()):
            
            # 選択された銘柄がその期間のデータに存在するか確認
            if company_name not in period_data.columns:
                # データがない場合はスキップ
                cell = cols[i % NUM_COLS].container()
                cell.markdown(f"**{period_label}**\n\n_データなし_")
                continue
                
            # 銘柄データと日経平均データ
            company_returns = period_data[company_name]
            nikkei_returns_data = nikkei_comparison_returns_data[period_label]
            
            # ピア平均（比較対象の銘柄の平均）を計算
            peers = period_data.drop(columns=[company_name], errors='ignore') 
            peer_avg = peers.mean(axis=1)

            # 期間ごとの全体のY軸範囲を取得 (統一された目盛)
            all_min_comp, all_max_comp = period_domains.get(period_label, [None, None])

            # プロット用データの整形
            nikkei_df = nikkei_returns_data.to_frame(name="Nikkei 225").reindex(company_returns.index, fill_value=None)
            
            plot_data = pd.DataFrame({
                company_name: company_returns,
                "Peer average": peer_avg,
                "Nikkei 225": nikkei_df["Nikkei 225"].values
            }, index=company_returns.index).reset_index().rename(columns={'index': 'Date'})
            
            plot_data_melted = plot_data.melt(id_vars=["Date"], var_name="Series", value_name="Return (%)")


            # --- チャートの描画ロジック ---
            base = alt.Chart(plot_data_melted).encode(
                x=alt.X("Date:T", axis=alt.Axis(title=None)),
                y=alt.Y(
                    "Return (%):Q",
                    axis=alt.Axis(title=None),
                    scale=alt.Scale(domain=[all_min_comp, all_max_comp]) 
                ),
                tooltip=["Date", "Series", alt.Tooltip("Return (%):Q", format=".2f")]
            )

            other_lines = base.transform_filter(
                alt.datum.Series != company_name
            ).mark_line().encode(
                color=alt.Color(
                    "Series:N",
                    scale=alt.Scale(
                        domain=["Nikkei 225", "Peer average"],
                        range=["#9BB7D0", "#D3D3D3"]
                    ),
                    legend=None
                )
            )

            company_line = base.transform_filter(
                alt.datum.Series == company_name
            ).mark_line(color="#C70025")

            chart = (other_lines + company_line).properties(title=f"{period_label}", height=300)

            # cols[i]にチャートを描画
            cell = cols[i % NUM_COLS].container()
            cell.altair_chart(chart, use_container_width=True)

# --- 騰落率チャートと株価推移チャートの期間選択を独立させるため、セクションを分割 ---

# -----------------------------------------------------------------------
## 騰落率チャート (独立した期間選択)
# -----------------------------------------------------------------------
st.subheader("騰落率チャート %") 

# 騰落率チャート専用のラジオボタン
horizon_return = st.radio(
    "騰落率チャート期間", 
    options=list(period_map.keys()),
    index=list(period_map.keys()).index("5年"),
    horizontal=True,
    key="return_period", # 独立したキーを設定
    label_visibility="collapsed"
)

# -----------------------------------------------------------------------
## YFinanceデータの計算 (騰落率用)
# -----------------------------------------------------------------------
try:
    # 選択された期間のデータをロード
    data_return = load_data(tickers, period_map[horizon_return])
    nikkei_data_return = load_nikkei(period_map[horizon_return])
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの制限が発生しました。時間をおいて再試行してください。")
    load_data.clear_cache()
    load_nikkei.clear_cache()
    st.stop()
except Exception as e:
    st.error(f"データ取得中にエラーが発生しました: {e}")
    st.stop()

# データ欠損チェック (騰落率用)
empty_columns_return = data_return.columns[data_return.isna().all()].tolist()
if empty_columns_return:
    st.error(f"騰落率チャート用データを取得できなかった銘柄: {', '.join(empty_columns_return)}")
    st.stop()

# --- 騰落率計算 ---
returns = (data_return / data_return.iloc[0] - 1) * 100
returns = returns.rename(columns=STOCKS)
nikkei_returns = (nikkei_data_return / nikkei_data_return.iloc[0] - 1) * 100

# --- 全体Y軸範囲を算出 (騰落率チャート用) ---
all_min_return = min(returns.min().min(), nikkei_returns.min())
all_max_return = max(returns.max().max(), nikkei_returns.max())

# -----------------------------------------------------------------------
## 騰落率チャートの描画
# -----------------------------------------------------------------------
st.altair_chart(
    alt.Chart(
        returns.reset_index().melt(id_vars=["Date"], var_name="Stock", value_name="Return (%)")
    )
    .mark_line()
    .encode(
        alt.X("Date:T", axis=alt.Axis(title=None)),
        alt.Y(
            "Return (%):Q",
            axis=alt.Axis(title=None),
            scale=alt.Scale(domain=[all_min_return, all_max_return])
        ),
        alt.Color("Stock:N", legend=alt.Legend(title=None)),
        tooltip=["Date", "Stock", alt.Tooltip("Return (%):Q", format=".2f")]
    )
    .properties(height=400),
    use_container_width=True
)


# -----------------------------------------------------------------------
## 株価推移チャート (独立した期間選択)
# -----------------------------------------------------------------------
st.subheader("株価推移チャート")

# 株価推移チャート専用のラジオボタン
horizon_price = st.radio(
    "株価推移チャート期間", 
    options=list(period_map.keys()),
    index=list(period_map.keys()).index("5年"),
    horizontal=True,
    key="price_period", # 独立したキーを設定
    label_visibility="collapsed"
)

# -----------------------------------------------------------------------
## YFinanceデータの計算 (株価用)
# -----------------------------------------------------------------------
try:
    # 選択された期間のデータをロード
    data_price = load_data(tickers, period_map[horizon_price])
    nikkei_data_price = load_nikkei(period_map[horizon_price])
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの制限が発生しました。時間をおいて再試行してください。")
    load_data.clear_cache()
    load_nikkei.clear_cache()
    st.stop()
except Exception as e:
    st.error(f"データ取得中にエラーが発生しました: {e}")
    st.stop()
    
# データ欠損チェック (株価用)
empty_columns_price = data_price.columns[data_price.isna().all()].tolist()
if empty_columns_price:
    st.error(f"株価推移チャート用データを取得できなかった銘柄: {', '.join(empty_columns_price)}")
    st.stop()

# -----------------------------------------------------------------------
## 株価推移チャートの描画
# -----------------------------------------------------------------------
data_with_nikkei = data_price.copy()
# 日経平均データをDataFrameに追加する際は、インデックス（日付）を揃える
data_with_nikkei["^N225"] = nikkei_data_price.reindex(data_with_nikkei.index, fill_value=None)

STOCKS_WITH_NIKKEI = STOCKS.copy()
STOCKS_WITH_NIKKEI["^N225"] = "日経平均"

# 描画順を日経平均を先頭にする
cols_ordered = ["^N225"] + [c for c in data_with_nikkei.columns if c != "^N225"]

NUM_COLS_PRICE = 2
price_cols = st.columns(NUM_COLS_PRICE)

for i, ticker in enumerate(cols_ordered):
    company_name = STOCKS_WITH_NIKKEI.get(ticker, ticker)
    plot_data = pd.DataFrame({
        "Date": data_with_nikkei.index,
        "Price": data_with_nikkei[ticker]
    })
    chart = (
        alt.Chart(plot_data)
        .mark_line(color="#D3D3D3" if ticker != "^N225" else "#9BB7D0")
        .encode(
            alt.X("Date:T", axis=alt.Axis(title=None)),
            # 株価は銘柄ごとに目盛が異なって自然なので、ここでは統一しません
            alt.Y("Price:Q", axis=alt.Axis(title=None), scale=alt.Scale(zero=False)),
            alt.Tooltip(["Date", "Price"]),
        )
        .properties(
            title=f"{company_name} ({horizon_price})", # 選択期間をタイトルに表示
            height=250
        )
    )
    cell = price_cols[i % NUM_COLS_PRICE].container()
    cell.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------------------
## 株主視点の主要指標テーブル
# -----------------------------------------------------------------------
st.subheader("株主向けファンダメンタル指標")

# 最終更新日時を保持するセッションステート
if "shareholder_metrics_last_updated" not in st.session_state:
    st.session_state.shareholder_metrics_last_updated = "未取得"

@st.cache_data(show_spinner=False)
def load_shareholder_metrics(tickers):
    import datetime
    import yfinance as yf

    data = []
    
    for t in tickers:
        try:
            ticker_obj = yf.Ticker(t)
            info = ticker_obj.info
            
            if not info:
                 st.warning(f"{t} の財務データが空です（データなし）")
                 continue
                 
            market_cap_trillion = info.get("marketCap", 0) / 1e12 if info.get("marketCap") else None
            
            data.append({
                "銘柄": STOCKS.get(t, t),
                "PER（予想）": info.get("forwardPE"),
                "PBR": info.get("priceToBook"),
                "PSR": info.get("priceToSalesTrailing12Months"),
                "ROE（%）": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else None,
                "営業利益率（%）": info.get("operatingMargins", 0) * 100 if info.get("operatingMargins") else None,
                "純利益率（%）": info.get("profitMargins", 0) * 100 if info.get("profitMargins") else None,
                "売上成長率（%）": info.get("revenueGrowth", 0) * 100 if info.get("revenueGrowth") else None,
                "利益成長率（%）": info.get("earningsGrowth", 0) * 100 if info.get("earningsGrowth") else None,
                
                # ★ 修正箇所: 配当利回りから * 100 を削除
                "配当利回り（%）": info.get("dividendYield") if info.get("dividendYield") else None, 
                
                "配当性向（%）": info.get("payoutRatio", 0) * 100 if info.get("payoutRatio") else None,
                "負債比率（D/E）": info.get("debtToEquity"),
                "流動比率": info.get("currentRatio"),
                "時価総額（兆円）": market_cap_trillion,
            })
        except Exception as e:
            st.warning(f"{t} の財務データ取得中に例外が発生しました: {e}")
            
    df = pd.DataFrame(data)
    
    st.session_state.shareholder_metrics_last_updated = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    return df

shareholder_df = load_shareholder_metrics(tickers)

# ★ データ取得日時を表示する
st.caption(f"データ取得日時（キャッシュ最終更新）: **{st.session_state.shareholder_metrics_last_updated}**")

if shareholder_df.empty:
    st.warning("株主向け指標データを取得できませんでした。")
else:
    st.dataframe(
        shareholder_df.style.format({
            "PER（予想）": "{:.1f}",
            "PBR": "{:.2f}",
            "PSR": "{:.2f}",
            "ROE（%）": "{:.1f}",
            "営業利益率（%）": "{:.1f}",
            "純利益率（%）": "{:.1f}",
            "売上成長率（%）": "{:.1f}",
            "利益成長率（%）": "{:.1f}",
            
            # 配当利回り（%）は、*100を削除したため、適切にフォーマットされます
            "配当利回り（%）": "{:.2f}",
            
            "配当性向（%）": "{:,.0f}",
            "負債比率（D/E）": "{:.2f}",
            "流動比率": "{:.1f}",
            "時価総額（兆円）": "{:,.2f}",
        }, na_rep='-'),
        width='stretch',
    )