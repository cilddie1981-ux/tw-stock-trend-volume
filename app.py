import math
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="台股趨勢指標＋量價分析", page_icon="📈", layout="wide")

st.title("📈 台股趨勢指標＋量價分析")
st.caption("依序判斷股價位置 → 趨勢 → 量價 → 動能 → 風險；分析結果僅供研究參考，不構成投資建議。")

with st.sidebar:
    st.header("分析設定")
    ticker_input = st.text_input("台股代號或 Yahoo Finance 代碼", value="2330", help="例如：2330、台積電、2330.TW、6488.TWO。建議輸入股票代號。")
    period = st.selectbox("歷史資料區間", ["6mo", "1y", "2y", "5y"], index=1)
    st.caption("上市股票通常使用 .TW；上櫃股票通常使用 .TWO。程式會先嘗試自動辨識。")
    run = st.button("開始分析", type="primary", use_container_width=True)

ALIASES = {
    "台積電": "2330.TW", "鴻海": "2317.TW", "聯發科": "2454.TW",
    "台達電": "2308.TW", "大亞": "1609.TW", "台亞": "2340.TW",
    "迎廣": "6117.TW", "台玻": "1802.TW", "聯穎": "3550.TW",
}

def resolve_ticker(raw, selected_period):
    raw = raw.strip()
    if not raw:
        raise ValueError("請輸入台股代號或名稱。")
    if raw in ALIASES:
        return ALIASES[raw]
    if raw.upper().endswith((".TW", ".TWO")):
        return raw.upper()
    if raw.isdigit():
        # Try .TW first, then .TWO.
        for suffix in (".TW", ".TWO"):
            candidate = raw + suffix
            hist = yf.Ticker(candidate).history(period=selected_period, auto_adjust=False)
            if not hist.empty:
                return candidate
        raise ValueError(f"找不到代號 {raw} 的歷史資料，請確認代號或直接輸入 .TW / .TWO。")
    raise ValueError("無法辨識名稱。請輸入台股代號（例如 2330），或 Yahoo Finance 代碼（例如 2330.TW）。")

def add_indicators(df):
    df = df.copy()
    df.columns = [str(c).title() for c in df.columns]
    required = {"Close", "High", "Low", "Volume"}
    if not required.issubset(df.columns):
        raise ValueError("資料來源缺少必要欄位。")
    for n in (5, 10, 20, 60):
        df[f"MA{n}"] = df["Close"].rolling(n).mean()
    low9 = df["Low"].rolling(9).min()
    high9 = df["High"].rolling(9).max()
    rsv = (df["Close"] - low9) / (high9 - low9).replace(0, np.nan) * 100
    df["K"] = rsv.ewm(alpha=1/3, adjust=False).mean()
    df["D"] = df["K"].ewm(alpha=1/3, adjust=False).mean()
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = ema12 - ema26
    df["MACD"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["DIF"] - df["MACD"]
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["VOL_MA5"] = df["Volume"].rolling(5).mean()
    df["VOL_MA10"] = df["Volume"].rolling(10).mean()
    df["BIAS20"] = (df["Close"] / df["MA20"] - 1) * 100
    return df

def money(x):
    return "—" if pd.isna(x) or not np.isfinite(x) else f"{x:,.2f}"

def analyze(df):
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = float(last["Close"])
    ma5, ma10, ma20, ma60 = [last.get(f"MA{n}", np.nan) for n in (5, 10, 20, 60)]
    valid_mas = all(pd.notna(x) for x in (ma5, ma10, ma20))
    bullish_stack = valid_mas and ma5 > ma10 > ma20 and (pd.isna(ma60) or ma20 > ma60)
    bearish_stack = valid_mas and ma5 < ma10 < ma20 and (pd.isna(ma60) or ma20 < ma60)

    if pd.notna(ma20) and pd.notna(ma60) and price > ma20 > ma60:
        trend = "強"
    elif bullish_stack or (pd.notna(ma20) and price > ma20):
        trend = "偏強"
    elif bearish_stack or (pd.notna(ma20) and price < ma20 and pd.notna(ma60) and price < ma60):
        trend = "弱"
    elif pd.notna(ma20) and price < ma20:
        trend = "偏弱"
    else:
        trend = "中性"

    if pd.notna(ma60) and price < ma60 and (pd.isna(ma20) or price < ma20):
        position = "低位／弱勢區（仍需確認底部）"
    elif pd.notna(ma20) and price > ma20 and pd.notna(ma60) and price > ma60:
        position = "中段偏強"
    elif pd.notna(last.get("BIAS20")) and last["BIAS20"] >= 10:
        position = "高位／乖離偏大"
    else:
        position = "中段整理"

    k, d = last.get("K", np.nan), last.get("D", np.nan)
    pk, pd_ = prev.get("K", np.nan), prev.get("D", np.nan)
    if pd.notna(k) and pd.notna(d) and pd.notna(pk) and pd.notna(pd_):
        if pk <= pd_ and k > d:
            kd = "黃金交叉"
        elif pk >= pd_ and k < d:
            kd = "死亡交叉"
        elif k >= 80 and d >= 80:
            kd = "高檔鈍化"
        elif k <= 20 and d <= 20:
            kd = "低檔區"
        else:
            kd = "中性"
    else:
        kd = "資料不足"

    hist, prev_hist = last.get("MACD_Hist", np.nan), prev.get("MACD_Hist", np.nan)
    if pd.notna(hist) and pd.notna(prev_hist):
        macd = "翻紅／多方動能增強" if hist > 0 and prev_hist <= 0 else ("翻綠／空方動能增強" if hist < 0 and prev_hist >= 0 else ("多方" if hist > 0 else "空方"))
    else:
        macd = "資料不足"

    rsi = last.get("RSI", np.nan)
    rsi_label = "強勢" if pd.notna(rsi) and rsi >= 60 else ("偏弱" if pd.notna(rsi) and rsi < 40 else ("中性" if pd.notna(rsi) else "資料不足"))
    if pd.notna(rsi) and rsi >= 75:
        rsi_label += "（過熱）"
    elif pd.notna(rsi) and rsi <= 25:
        rsi_label += "（超賣）"

    vol5, vol10, vol = last.get("VOL_MA5", np.nan), last.get("VOL_MA10", np.nan), last.get("Volume", np.nan)
    if pd.notna(vol5) and pd.notna(vol10) and pd.notna(vol):
        if vol > vol10 * 1.8:
            volume_label = "爆量，需搭配K線判斷是否出貨"
        elif vol > vol10 * 1.2 and price > float(prev["Close"]):
            volume_label = "價漲量增"
        elif vol5 < vol10:
            volume_label = "量縮整理"
        else:
            volume_label = "量能中性"
    else:
        volume_label = "資料不足"

    bias = last.get("BIAS20", np.nan)
    if pd.notna(bias) and bias >= 10:
        bias_label = "乖離過大，避免追價"
    elif pd.notna(bias) and bias <= -10:
        bias_label = "負乖離偏大，先確認止跌"
    else:
        bias_label = "乖離尚可"

    # Approximate levels from recent 20-day range; these are technical estimates, not predictions.
    recent = df.tail(20)
    support = float(recent["Low"].min())
    resistance = float(recent["High"].max())
    ma20v = float(ma20) if pd.notna(ma20) else price
    buy_low = max(support, min(ma20v, price) * 0.985)
    buy_high = max(buy_low, min(ma20v, price) * 1.005)
    breakout = resistance * 1.005
    stop = min(support * 0.98, buy_low * 0.95)
    risk = max(price - stop, price * 0.03)
    target1 = price + risk
    target2 = price + risk * 2
    false_break = resistance * 0.97

    positive = sum([
        trend in ("強", "偏強"),
        kd == "黃金交叉" or (pd.notna(k) and pd.notna(d) and k > d and k < 80),
        pd.notna(hist) and hist > 0,
        pd.notna(rsi) and 50 <= rsi < 75,
        "價漲量增" in volume_label,
        pd.notna(bias) and bias < 8,
    ])
    if "爆量" in volume_label or "避免追價" in bias_label or trend == "弱":
        signal = "🟡 等待／控管風險"
    elif positive >= 4 and price > support and (pd.isna(ma20) or price >= ma20):
        signal = "🟢 偏多觀察，等回檔或確認突破"
    else:
        signal = "🟡 等待訊號確認"

    return {
        "price": price, "trend": trend, "position": position, "kd": kd, "macd": macd,
        "rsi_label": rsi_label, "rsi": rsi, "volume": volume_label, "bias_label": bias_label,
        "bias": bias, "support": support, "resistance": resistance, "buy_low": buy_low,
        "buy_high": buy_high, "breakout": breakout, "stop": stop, "target1": target1,
        "target2": target2, "false_break": false_break, "signal": signal,
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        "vol": vol, "vol5": vol5, "vol10": vol10, "hist": hist
    }

if run or "analysis_df" not in st.session_state:
    try:
        with st.spinner("正在取得台股歷史行情並計算技術指標…"):
            ticker = resolve_ticker(ticker_input, period)
            raw = yf.Ticker(ticker).history(period=period, auto_adjust=False)
            if raw.empty:
                raise ValueError("資料來源沒有回傳行情，請更換代號或稍後再試。")
            df = add_indicators(raw).dropna(subset=["Close"])
            if len(df) < 25:
                raise ValueError("有效歷史資料不足，至少需要約 25 個交易日。")
            st.session_state["analysis_df"] = df
            st.session_state["analysis_ticker"] = ticker
            st.session_state["analysis_input"] = ticker_input
    except Exception as e:
        st.error(f"分析失敗：{e}")
        st.stop()

df = st.session_state["analysis_df"]
ticker = st.session_state["analysis_ticker"]
result = analyze(df)
last_date = df.index[-1]
if getattr(last_date, "tzinfo", None) is not None:
    last_date = last_date.tz_convert("Asia/Taipei").tz_localize(None)

st.info(f"股票代碼：**{ticker}**　｜　行情最後日期：**{last_date:%Y-%m-%d}**　｜　價格基準：收盤價（可能有資料延遲）")

c1, c2, c3, c4 = st.columns(4)
c1.metric("最新收盤價", f"{result['price']:.2f}")
c2.metric("趨勢判斷", result["trend"])
c3.metric("股價位置", result["position"])
c4.metric("目前訊號", result["signal"])

st.subheader("🎯 技術指標與交易規劃")
rows = [
    ("現價", money(result["price"])),
    ("趨勢", result["trend"]),
    ("位置", result["position"]),
    ("5MA / 10MA / 20MA / 60MA", " / ".join(money(result[k]) for k in ("ma5","ma10","ma20","ma60"))),
    ("KD", f"{result['kd']}（K={money(df.iloc[-1].get('K'))}，D={money(df.iloc[-1].get('D'))}）"),
    ("MACD", result["macd"]),
    ("RSI", f"{result['rsi_label']}（{money(result['rsi'])}）"),
    ("量價", result["volume"]),
    ("5日均量 / 10日均量", f"{money(result['vol5'])} / {money(result['vol10'])}"),
    ("20日乖離率", f"{money(result['bias'])}%（{result['bias_label']}）"),
    ("近20日支撐參考", money(result["support"])),
    ("近20日壓力參考", money(result["resistance"])),
    ("精準買點（估算）", f"{money(result['buy_low'])}～{money(result['buy_high'])}"),
    ("突破觀察價（估算）", money(result["breakout"])),
    ("停損參考（估算）", money(result["stop"])),
    ("第一目標（風險倍數估算）", money(result["target1"])),
    ("第二目標（風險倍數估算）", money(result["target2"])),
    ("假突破警戒參考", money(result["false_break"])),
    ("目前訊號", result["signal"]),
]
summary = pd.DataFrame(rows, columns=["項目", "訊號／參考值"])
st.dataframe(summary, hide_index=True, use_container_width=True)

st.subheader("📊 股價、均線與成交量")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="K線"))
for n in (5, 10, 20, 60):
    fig.add_trace(go.Scatter(x=df.index, y=df[f"MA{n}"], mode="lines", name=f"{n}MA"))
fig.update_layout(height=560, xaxis_rangeslider_visible=False, legend_orientation="h", legend_y=1.02, margin=dict(l=20,r=20,t=30,b=20))
st.plotly_chart(fig, use_container_width=True)

volfig = go.Figure()
volfig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="成交量"))
volfig.add_trace(go.Scatter(x=df.index, y=df["VOL_MA5"], mode="lines", name="5日均量"))
volfig.add_trace(go.Scatter(x=df.index, y=df["VOL_MA10"], mode="lines", name="10日均量"))
volfig.update_layout(height=300, legend_orientation="h", margin=dict(l=20,r=20,t=30,b=20))
st.plotly_chart(volfig, use_container_width=True)

st.subheader("🧭 短線／波段／長期觀察")
a, b, c = st.columns(3)
with a:
    st.markdown("**短線（數日～數週）**")
    st.write(f"回檔觀察區：{money(result['buy_low'])}～{money(result['buy_high'])}")
    st.write(f"短線風險線：{money(result['stop'])}")
    st.write("若跌破支撐且量增，降低部位或重新評估。")
with b:
    st.markdown("**波段（數週～數月）**")
    st.write(f"突破觀察：收盤站上 {money(result['breakout'])}，且成交量配合。")
    st.write(f"近20日壓力：{money(result['resistance'])}")
    st.write("突破後需觀察回測是否守住，避免只看盤中穿價。")
with c:
    st.markdown("**長期（數月至數年）**")
    st.write(f"60MA：{money(result['ma60'])}")
    st.write("本工具不直接把技術壓力當作基本面合理價。")
    st.write("長期合理價需另評估營收、獲利、現金流、產業前景與估值。")

st.warning("重要限制：本工具使用 Yahoo Finance 歷史行情估算技術指標；精準買點、目標價、停損與假突破價是規則化參考，不保證成交或獲利。未提供可靠的即時報價、法人籌碼、財報估值與除權息調整驗證。交易前請自行確認資料、流動性與風險。")
with st.expander("查看最近 30 個交易日資料"):
    st.dataframe(df.tail(30).sort_index(ascending=False), use_container_width=True)
