import io
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="台股趨勢指標 3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 台股趨勢指標 3.0")
st.caption("趨勢指標＋量價分析｜公開資料參考工具，非投資建議")

# ------------------------------
# 基本設定與股票名稱別名
# ------------------------------
ALIASES = {
    "台積電": "2330.TW", "台積電2330": "2330.TW", "2330": "2330.TW",
    "大亞": "1609.TW", "1609": "1609.TW",
    "台亞": "2340.TW", "2340": "2340.TW",
    "迎廣": "6117.TW", "6117": "6117.TW",
    "台玻": "1802.TW", "1802": "1802.TW",
    "聯穎": "3550.TW", "3550": "3550.TW",
}

TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"


def as_float(value, default=np.nan):
    try:
        if value is None:
            return default
        out = float(value)
        return out if np.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def fmt_price(value):
    value = as_float(value)
    return "—" if not np.isfinite(value) else f"{value:,.2f}"


def safe_div(a, b):
    a, b = as_float(a), as_float(b)
    if not np.isfinite(a) or not np.isfinite(b) or b == 0:
        return np.nan
    return a / b


def resolve_symbol(user_input):
    raw = str(user_input or "").strip()
    if not raw:
        return ""
    key = raw.replace(" ", "").upper()
    if key in ALIASES:
        return ALIASES[key]
    if key.endswith(".TW") or key.endswith(".TWO"):
        return key
    digits = "".join(ch for ch in key if ch.isdigit())
    if len(digits) == 4 and digits == key:
        return digits + ".TW"
    # 允許直接輸入公司名稱；依上市櫃公開清單比對。
    try:
        market_df, _ = load_market_list()
        if not market_df.empty:
            matched = market_df[market_df["名稱"].astype(str).str.strip() == raw.strip()]
            if not matched.empty:
                return str(matched.iloc[0]["代號"])
    except Exception:
        pass
    return raw


def lookup_stock_name(symbol):
    """優先從公開上市櫃清單取得公司名稱，查不到則使用內建別名。"""
    normalized = resolve_symbol(symbol)
    try:
        market_df, _ = load_market_list()
        if not market_df.empty:
            matched = market_df[market_df["代號"].astype(str).str.upper() == normalized.upper()]
            if not matched.empty:
                return str(matched.iloc[0]["名稱"])
            code = normalized.split(".")[0]
            matched = market_df[market_df["股票代號"].astype(str) == code]
            if not matched.empty:
                return str(matched.iloc[0]["名稱"])
    except Exception:
        pass
    reverse_aliases = {
        "2330.TW": "台積電", "1609.TW": "大亞", "2340.TW": "台亞",
        "6117.TW": "迎廣", "1802.TW": "台玻", "3550.TW": "聯穎",
    }
    return reverse_aliases.get(normalized.upper(), "名稱資料暫缺")


@st.cache_data(ttl=3600, show_spinner=False)
def load_market_list():
    """讀取上市、上櫃公司基本清單；API 暫時失敗時回傳明確錯誤。"""
    records = []
    errors = []
    headers = {"User-Agent": "Mozilla/5.0"}
    sources = [
        ("上市", TWSE_URL),
        ("上櫃", TPEX_URL),
    ]
    for market, url in sources:
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                payload = payload.get("data", [])
            if not isinstance(payload, list):
                continue
            for item in payload:
                if not isinstance(item, dict):
                    continue
                code = name = ""
                for key in ("公司代號", "有價證券代號", "證券代號", "股票代號", "代號"):
                    if item.get(key):
                        code = str(item[key]).strip()
                        break
                for key in ("公司簡稱", "有價證券名稱", "證券名稱", "公司名稱", "名稱"):
                    if item.get(key):
                        name = str(item[key]).strip()
                        break
                if code.isdigit() and len(code) == 4 and name:
                    records.append({
                        "代號": code + (".TW" if market == "上市" else ".TWO"),
                        "股票代號": code,
                        "名稱": name,
                        "市場": market,
                    })
        except Exception as exc:
            errors.append(f"{market}清單讀取失敗：{exc}")
    if not records:
        return pd.DataFrame(columns=["代號", "股票代號", "名稱", "市場"]), "；".join(errors) or "公開 API 未回傳可用資料"
    frame = pd.DataFrame(records).drop_duplicates(subset=["代號"]).sort_values("股票代號")
    return frame.reset_index(drop=True), "；".join(errors)


@st.cache_data(ttl=900, show_spinner=False)
def download_history(symbol, period="1y"):
    """下載 Yahoo Finance 日線歷史行情。資料可能延遲或暫時缺漏。"""
    try:
        df = yf.download(
            symbol,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=25,
            multi_level_index=False,
        )
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        needed = {}
        for col in ("Close", "High", "Low", "Volume"):
            if col in df.columns:
                needed[col] = df[col]
        out = pd.DataFrame(needed).copy()
        out.index = pd.to_datetime(out.index)
        out = out[~out.index.duplicated(keep="last")].sort_index()
        for col in ("Close", "High", "Low", "Volume"):
            if col not in out.columns:
                out[col] = np.nan
        out = out[["Close", "High", "Low", "Volume"]].apply(pd.to_numeric, errors="coerce")
        out = out.dropna(subset=["Close"])
        return out
    except Exception:
        return pd.DataFrame()


def calculate_indicators(df):
    df = df.copy()
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    volume = df["Volume"].astype(float)

    for n in (5, 10, 20, 60):
        df[f"MA{n}"] = close.rolling(n, min_periods=n).mean()

    # KD：9 日 RSV，K/D 以常見 1/3 平滑方式遞迴計算，初值 50。
    low9 = low.rolling(9, min_periods=9).min()
    high9 = high.rolling(9, min_periods=9).max()
    span = high9 - low9
    rsv = ((close - low9) / span.replace(0, np.nan) * 100).clip(0, 100)
    rsv = rsv.fillna(50)
    k_values, d_values = [], []
    k_prev = d_prev = 50.0
    for value in rsv.to_numpy():
        k_prev = (2 / 3) * k_prev + (1 / 3) * float(value)
        d_prev = (2 / 3) * d_prev + (1 / 3) * k_prev
        k_values.append(k_prev)
        d_values.append(d_prev)
    df["K"] = k_values
    df["D"] = d_values

    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    df["DIF"] = ema12 - ema26
    df["MACD"] = df["DIF"].ewm(span=9, adjust=False, min_periods=9).mean()
    df["MACD_HIST"] = df["DIF"] - df["MACD"]

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14, min_periods=14).mean()
    avg_loss = loss.rolling(14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50)
    df["RSI"] = rsi

    df["VOL_MA5"] = volume.rolling(5, min_periods=5).mean()
    df["VOL_MA10"] = volume.rolling(10, min_periods=10).mean()
    df["BIAS20"] = (close / df["MA20"] - 1) * 100

    previous_close = close.shift(1)
    true_range = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs(),
    ], axis=1).max(axis=1)
    df["ATR14"] = true_range.rolling(14, min_periods=14).mean()
    return df


def _round_price(value):
    value = as_float(value)
    if not np.isfinite(value):
        return np.nan
    # 台股股價以小數點兩位作分析參考；實際跳動單位依交易所規則。
    return round(value, 2)


def analyze(symbol, period="1y"):
    requested_symbol = resolve_symbol(symbol)
    candidates = [requested_symbol]
    if requested_symbol.endswith(".TW"):
        candidates.append(requested_symbol[:-3] + ".TWO")
    elif requested_symbol.endswith(".TWO"):
        candidates.append(requested_symbol[:-4] + ".TW")
    candidates = list(dict.fromkeys(candidates))

    raw = pd.DataFrame()
    used_symbol = requested_symbol
    for candidate in candidates:
        attempt = download_history(candidate, period)
        if not attempt.empty and len(attempt) >= 60:
            raw, used_symbol = attempt, candidate
            break
        if not attempt.empty and raw.empty:
            raw, used_symbol = attempt, candidate

    if raw.empty:
        return {"error": f"無法取得 {requested_symbol} 的歷史行情。請確認代號、網路或 Yahoo Finance 資料狀態。"}
    if len(raw) < 60:
        return {"error": f"{used_symbol} 僅取得 {len(raw)} 筆日線資料，少於 60 筆，無法完整判斷中長期均線。"}

    df = calculate_indicators(raw)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = as_float(last["Close"])
    ma5, ma10, ma20, ma60 = [as_float(last[f"MA{x}"]) for x in (5, 10, 20, 60)]
    k, d = as_float(last["K"]), as_float(last["D"])
    prev_k, prev_d = as_float(prev["K"]), as_float(prev["D"])
    dif, macd, hist = [as_float(last[x]) for x in ("DIF", "MACD", "MACD_HIST")]
    prev_hist = as_float(prev["MACD_HIST"])
    rsi = as_float(last["RSI"])
    bias20 = as_float(last["BIAS20"])
    vol5, vol10 = as_float(last["VOL_MA5"]), as_float(last["VOL_MA10"])
    today_volume = as_float(last["Volume"])
    atr = as_float(last["ATR14"])

    # 先判斷位置，再判斷趨勢。
    if np.isfinite(ma20) and np.isfinite(ma60) and price < ma20 and ma20 < ma60:
        position = "低位／弱勢區"
    elif np.isfinite(bias20) and bias20 >= 10:
        position = "高位／乖離偏大"
    elif np.isfinite(ma20) and price > ma20 and np.isfinite(ma60) and price > ma60:
        position = "中段偏強"
    elif np.isfinite(ma20) and price <= ma20:
        position = "中低位整理"
    else:
        position = "中段"

    if all(np.isfinite(x) for x in (ma5, ma10, ma20, ma60)) and ma5 > ma10 > ma20 > ma60:
        trend = "強"
    elif np.isfinite(ma20) and np.isfinite(ma60) and price > ma20 > ma60:
        trend = "偏強"
    elif np.isfinite(ma20) and np.isfinite(ma60) and price < ma20 < ma60:
        trend = "弱"
    elif np.isfinite(ma20) and price >= ma20:
        trend = "中性偏多"
    else:
        trend = "偏弱"

    if k > d and prev_k <= prev_d:
        kd_signal = "黃金交叉"
    elif k < d and prev_k >= prev_d:
        kd_signal = "死亡交叉"
    elif k >= 80 and d >= 80:
        kd_signal = "高檔鈍化"
    elif k <= 20 and d <= 20:
        kd_signal = "低檔區"
    else:
        kd_signal = "中性"

    if hist > 0 and prev_hist <= 0:
        macd_signal = "柱體翻紅"
    elif hist < 0 and prev_hist >= 0:
        macd_signal = "柱體翻綠"
    elif hist > 0:
        macd_signal = "多方"
    elif hist < 0:
        macd_signal = "空方"
    else:
        macd_signal = "中性"

    if not np.isfinite(rsi):
        rsi_signal = "資料不足"
    elif rsi >= 80:
        rsi_signal = "過熱"
    elif rsi >= 60:
        rsi_signal = "強勢"
    elif rsi <= 30:
        rsi_signal = "超賣"
    elif rsi < 45:
        rsi_signal = "偏弱"
    else:
        rsi_signal = "中性"

    if np.isfinite(vol5) and np.isfinite(vol10):
        if vol5 > vol10 * 1.2:
            volume_signal = "近期量增"
        elif vol5 < vol10 * 0.8:
            volume_signal = "量縮整理"
        else:
            volume_signal = "量能持平"
    else:
        volume_signal = "量能資料不足"

    if np.isfinite(today_volume) and np.isfinite(vol10) and today_volume > vol10 * 2:
        volume_signal += "／當日爆量，留意長黑或上影線"

    # 以近 20 日低點、MA20 和近 20 日高點建立參考支撐壓力。
    recent = df.tail(20)
    low20 = as_float(recent["Low"].min())
    high20 = as_float(recent["High"].max())
    support_candidates = [x for x in (low20, ma20) if np.isfinite(x) and x > 0]
    support = max(support_candidates) if support_candidates else price * 0.95
    resistance = high20 if np.isfinite(high20) and high20 > 0 else price * 1.03
    atr_buffer = max(atr * 0.25 if np.isfinite(atr) else 0, price * 0.005)

    pullback_low = max(support * 0.995, price * 0.965)
    pullback_high = min(price, max(pullback_low, support * 1.015))
    breakout = resistance + atr_buffer
    false_break = resistance - atr_buffer
    stop_pullback = min(support - atr_buffer, pullback_low * 0.97)
    stop_breakout = min(resistance - atr_buffer, breakout * 0.97)

    # 以買點為基礎計算不同交易計畫目標，避免突破買點高於目標價。
    risk_pullback = max(pullback_low - stop_pullback, 0)
    pullback_t1 = pullback_low + risk_pullback * 1.5
    pullback_t2 = pullback_low + risk_pullback * 2.5
    risk_breakout = max(breakout - stop_breakout, 0)
    breakout_t1 = breakout + risk_breakout * 1.5
    breakout_t2 = breakout + risk_breakout * 2.5
    rr_pullback = safe_div(pullback_t1 - pullback_low, pullback_low - stop_pullback)
    rr_breakout = safe_div(breakout_t1 - breakout, breakout - stop_breakout)

    # 主表目標為現價附近的參考價，另提供依買點計算的兩套交易目標。
    ref_t1 = price + max(price - support, atr if np.isfinite(atr) else price * 0.03) * 0.618
    ref_t2 = price + max(price - support, atr if np.isfinite(atr) else price * 0.03)

    checks = []
    if pullback_low >= pullback_t1:
        checks.append("回檔目標價計算異常")
    if breakout >= breakout_t1:
        checks.append("突破目標價計算異常")
    if breakout <= price:
        checks.append("突破價未高於現價，需重新確認壓力")
    if resistance < price:
        checks.append("現價已高於近20日高點，壓力位可能需更新")
    if np.isfinite(bias20) and bias20 > 10:
        checks.append("20日乖離偏大，不宜盲目追價")
    if not checks:
        checks.append("價格結構檢查通過（仍需人工確認）")

    # 保守訊號：需趨勢、動能、量價與位置共同支持。
    positive_points = 0
    positive_points += trend in ("強", "偏強", "中性偏多")
    positive_points += hist > 0
    positive_points += np.isfinite(rsi) and 50 <= rsi < 75
    positive_points += np.isfinite(vol5) and np.isfinite(vol10) and vol5 >= vol10 * 0.9
    positive_points += kd_signal == "黃金交叉" or (k > d and k < 80)
    negative_points = 0
    negative_points += trend == "弱"
    negative_points += hist < 0
    negative_points += kd_signal == "死亡交叉"
    negative_points += np.isfinite(rsi) and rsi >= 80
    negative_points += np.isfinite(bias20) and bias20 > 10
    if position.startswith("高位") or negative_points >= 3:
        signal = "🔴 撤／避免追價" if negative_points >= 3 else "🟡 等回檔"
    elif positive_points >= 4 and negative_points <= 1 and position != "低位／弱勢區":
        signal = "🟢 偏多觀察，等買點確認"
    else:
        signal = "🟡 等待確認"

    result = {
        "代號": used_symbol,
        "名稱": lookup_stock_name(used_symbol),
        "現價": price,
        "資料日期": pd.Timestamp(df.index[-1]).strftime("%Y-%m-%d"),
        "資料筆數": len(df),
        "趨勢": trend,
        "位置": position,
        "MA5": ma5, "MA10": ma10, "MA20": ma20, "MA60": ma60,
        "KD": kd_signal, "K值": k, "D值": d,
        "MACD": macd_signal, "DIF": dif, "MACD線": macd, "MACD柱體": hist,
        "RSI": rsi_signal, "RSI數值": rsi,
        "量價": volume_signal, "5日均量": vol5, "10日均量": vol10,
        "當日成交量": today_volume, "20日乖離率(%)": bias20, "ATR14": atr,
        "近20日支撐": support, "近20日壓力": resistance,
        "精準買點": f"{_round_price(pullback_low)}～{_round_price(pullback_high)}",
        "回檔買點下緣": _round_price(pullback_low),
        "回檔買點上緣": _round_price(pullback_high),
        "突破買點": _round_price(breakout),
        "回檔停損": _round_price(stop_pullback),
        "突破停損": _round_price(stop_breakout),
        "停損": _round_price(stop_pullback),
        "第一目標": _round_price(ref_t1),
        "第二目標": _round_price(ref_t2),
        "回檔第一目標": _round_price(pullback_t1),
        "回檔第二目標": _round_price(pullback_t2),
        "突破第一目標": _round_price(breakout_t1),
        "突破第二目標": _round_price(breakout_t2),
        "假突破價": _round_price(false_break),
        "回檔風險報酬比": round(rr_pullback, 2) if np.isfinite(rr_pullback) else np.nan,
        "突破風險報酬比": round(rr_breakout, 2) if np.isfinite(rr_breakout) else np.nan,
        "價格計算檢查": "；".join(checks),
        "目前訊號": signal,
        "_df": df,
    }
    return result


def fetch_fundamentals(symbol):
    """擷取可用財務欄位；不以 0 假裝缺漏資料，也標示粗估限制。"""
    symbol = resolve_symbol(symbol)
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.get_info() or {}
    except Exception as exc:
        return {"代號": symbol, "資料狀態": f"財務資料讀取失敗：{exc}"}

    trailing_eps = as_float(info.get("trailingEps"))
    forward_eps = as_float(info.get("forwardEps"))
    trailing_pe = as_float(info.get("trailingPE"))
    forward_pe = as_float(info.get("forwardPE"))
    book_value = as_float(info.get("bookValue"))
    current_price = as_float(info.get("currentPrice"))
    if not np.isfinite(current_price):
        current_price = as_float(info.get("regularMarketPrice"))
    revenue_growth = as_float(info.get("revenueGrowth"))
    earnings_growth = as_float(info.get("earningsGrowth"))
    profit_margin = as_float(info.get("profitMargins"))
    roe = as_float(info.get("returnOnEquity"))
    debt_equity = as_float(info.get("debtToEquity"))
    dividend_yield = as_float(info.get("dividendYield"))

    # 估值採用一致期間的 EPS/PER 配對；若 PER 不合理則不產生本益比估值。
    if np.isfinite(forward_eps) and forward_eps > 0 and np.isfinite(forward_pe) and 0 < forward_pe < 100:
        eps_used, pe_used, eps_source = forward_eps, forward_pe, "預估 EPS＋預估本益比"
    elif np.isfinite(trailing_eps) and trailing_eps > 0 and np.isfinite(trailing_pe) and 0 < trailing_pe < 100:
        eps_used, pe_used, eps_source = trailing_eps, trailing_pe, "近四季 EPS＋歷史本益比"
    else:
        eps_used, pe_used, eps_source = np.nan, np.nan, "缺乏有效且一致的 EPS／本益比"

    # 這是以目前市場本益比作敏感度推估，不等同分析師目標價或官方合理價。
    fair_low = eps_used * pe_used * 0.8 if np.isfinite(eps_used) and np.isfinite(pe_used) else np.nan
    fair_mid = eps_used * pe_used if np.isfinite(eps_used) and np.isfinite(pe_used) else np.nan
    fair_high = eps_used * pe_used * 1.2 if np.isfinite(eps_used) and np.isfinite(pe_used) else np.nan

    return {
        "代號": symbol,
        "現價(財務來源)": current_price,
        "近四季EPS": trailing_eps,
        "預估EPS": forward_eps,
        "歷史本益比": trailing_pe,
        "預估本益比": forward_pe,
        "每股淨值": book_value,
        "營收成長率": revenue_growth,
        "盈餘成長率": earnings_growth,
        "淨利率": profit_margin,
        "ROE": roe,
        "負債權益比": debt_equity,
        "股利殖利率": dividend_yield,
        "估值EPS來源": eps_source,
        "估值參考低檔": fair_low,
        "估值參考中位": fair_mid,
        "估值參考高檔": fair_high,
        "資料狀態": "財務欄位為 Yahoo Finance 可取得資料；可能缺漏或延遲",
        "估值限制": "本益比敏感度粗估，非獨立基本面評價；不適用於虧損或 EPS／PER 缺漏公司",
    }


def technical_score(item):
    score = 0
    trend = str(item.get("趨勢", ""))
    if trend == "強":
        score += 3
    elif trend == "偏強":
        score += 2
    elif trend == "中性偏多":
        score += 1
    if str(item.get("MACD", "")) in ("多方", "柱體翻紅"):
        score += 2
    if str(item.get("KD", "")) in ("黃金交叉", "高檔鈍化"):
        score += 1
    if str(item.get("RSI", "")) == "強勢":
        score += 1
    if "量增" in str(item.get("量價", "")):
        score += 1
    if "死亡交叉" in str(item.get("KD", "")):
        score -= 2
    if str(item.get("MACD", "")) in ("空方", "柱體翻綠"):
        score -= 2
    if str(item.get("RSI", "")) == "過熱":
        score -= 1
    if as_float(item.get("20日乖離率(%)"), 0) > 10:
        score -= 2
    return score


def clean_result(item):
    return {key: value for key, value in item.items() if not key.startswith("_")}


def show_analysis(result):
    if not result or result.get("error"):
        st.error((result or {}).get("error", "分析失敗"))
        return

    st.subheader(f"分析結果：{result['代號']}｜{result['名稱']}")
    st.caption(f"行情資料日期：{result['資料日期']}｜共 {result['資料筆數']} 筆日線資料。行情來源為 Yahoo Finance，非保證即時。")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價", fmt_price(result["現價"]))
    c2.metric("趨勢", result["趨勢"])
    c3.metric("位置", result["位置"])
    c4.metric("目前訊號", result["目前訊號"])

    main_rows = [
        ("KD", f"{result['KD']}（K {result['K值']:.1f}／D {result['D值']:.1f}）"),
        ("MACD", f"{result['MACD']}（DIF {fmt_price(result['DIF'])}／柱體 {fmt_price(result['MACD柱體'])}）"),
        ("RSI", f"{result['RSI']}（{result['RSI數值']:.1f}）" if np.isfinite(as_float(result["RSI數值"])) else result["RSI"]),
        ("量價", result["量價"]),
        ("5日均量", f"{result['5日均量']:,.0f}" if np.isfinite(as_float(result["5日均量"])) else "—"),
        ("10日均量", f"{result['10日均量']:,.0f}" if np.isfinite(as_float(result["10日均量"])) else "—"),
        ("20日乖離率", f"{result['20日乖離率(%)']:.2f}%" if np.isfinite(as_float(result["20日乖離率(%)"])) else "—"),
        ("ATR14", fmt_price(result["ATR14"])),
        ("MA5／10／20／60", "／".join(fmt_price(result[k]) for k in ("MA5", "MA10", "MA20", "MA60"))),
        ("近20日支撐／壓力", f"{fmt_price(result['近20日支撐'])}／{fmt_price(result['近20日壓力'])}"),
    ]
    st.dataframe(pd.DataFrame(main_rows, columns=["項目", "訊號"]), hide_index=True, use_container_width=True)

    st.markdown("### 🎯 交易價格參考")
    trade_rows = [
        ("精準買點（回檔）", result["精準買點"]),
        ("突破買點", fmt_price(result["突破買點"])),
        ("回檔停損", fmt_price(result["回檔停損"])),
        ("突破停損", fmt_price(result["突破停損"])),
        ("第一目標（現價參考）", fmt_price(result["第一目標"])),
        ("第二目標（現價參考）", fmt_price(result["第二目標"])),
        ("回檔第一／第二目標", f"{fmt_price(result['回檔第一目標'])}／{fmt_price(result['回檔第二目標'])}"),
        ("突破第一／第二目標", f"{fmt_price(result['突破第一目標'])}／{fmt_price(result['突破第二目標'])}"),
        ("假突破觀察價", fmt_price(result["假突破價"])),
        ("回檔風險報酬比", f"{result['回檔風險報酬比']:.2f}" if np.isfinite(as_float(result["回檔風險報酬比"])) else "—"),
        ("突破風險報酬比", f"{result['突破風險報酬比']:.2f}" if np.isfinite(as_float(result["突破風險報酬比"])) else "—"),
        ("價格計算檢查", result["價格計算檢查"]),
    ]
    st.dataframe(pd.DataFrame(trade_rows, columns=["項目", "參考值"]), hide_index=True, use_container_width=True)
    st.warning("以上買點、停損與目標價均為依歷史價格推算的技術參考，不是保證成交價。下單前請確認最新行情、跳動單位、流動性與自身風險承受度。")

    df = result["_df"]
    st.markdown("### 📉 價格與均線")
    chart_df = df[["Close", "MA5", "MA10", "MA20", "MA60"]].tail(120).rename(
        columns={"Close": "收盤價", "MA5": "MA5", "MA10": "MA10", "MA20": "MA20", "MA60": "MA60"}
    )
    st.line_chart(chart_df, use_container_width=True)
    st.markdown("### 成交量")
    st.bar_chart(df[["Volume"]].tail(60).rename(columns={"Volume": "成交量"}), use_container_width=True)


def scan_market(market_df, limit, scan_label):
    if market_df.empty:
        st.error("目前沒有可用的上市櫃清單。")
        return pd.DataFrame()
    scan_df = market_df.head(limit).copy()
    st.info(f"{scan_label}：本次最多掃描 {len(scan_df)} 檔；行情服務可能限流，掃描結果不保證涵蓋全市場。")
    progress = st.progress(0)
    status = st.empty()
    rows = []
    failures = 0
    for idx, row in enumerate(scan_df.itertuples(index=False), start=1):
        symbol = getattr(row, "代號")
        try:
            result = analyze(symbol, "6mo")
            if not result.get("error"):
                cleaned = clean_result(result)
                cleaned["名稱"] = getattr(row, "名稱")
                cleaned["技術分數"] = technical_score(result)
                rows.append(cleaned)
            else:
                failures += 1
        except Exception:
            failures += 1
        progress.progress(idx / len(scan_df))
        status.text(f"掃描中：{idx}/{len(scan_df)}｜成功 {len(rows)} 檔｜失敗 {failures} 檔")
        time.sleep(0.03)
    status.text(f"掃描完成：成功 {len(rows)} 檔，失敗或資料不足 {failures} 檔。")
    progress.empty()
    out = pd.DataFrame(rows)
    return out


def dataframe_csv_download(df, filename="tw_stock_scan.csv"):
    csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("⬇️ 下載 CSV", data=csv, file_name=filename, mime="text/csv")


def render_fundamental(symbol):
    with st.spinner("讀取財務資料中…"):
        item = fetch_fundamentals(symbol)
    if "估值參考中位" not in item:
        st.error(item.get("資料狀態", "無法取得財務資料"))
        return item
    st.markdown("### 基本面與估值參考")
    c1, c2, c3 = st.columns(3)
    c1.metric("近四季 EPS", fmt_price(item["近四季EPS"]))
    c2.metric("預估 EPS", fmt_price(item["預估EPS"]))
    c3.metric("每股淨值", fmt_price(item["每股淨值"]))
    valuation = pd.DataFrame([
        ("估值 EPS 來源", item["估值EPS來源"]),
        ("估值參考低檔", fmt_price(item["估值參考低檔"])),
        ("估值參考中位", fmt_price(item["估值參考中位"])),
        ("估值參考高檔", fmt_price(item["估值參考高檔"])),
        ("歷史本益比", fmt_price(item["歷史本益比"])),
        ("預估本益比", fmt_price(item["預估本益比"])),
        ("營收成長率", f"{item['營收成長率']:.1%}" if np.isfinite(as_float(item["營收成長率"])) else "—"),
        ("盈餘成長率", f"{item['盈餘成長率']:.1%}" if np.isfinite(as_float(item["盈餘成長率"])) else "—"),
        ("淨利率", f"{item['淨利率']:.1%}" if np.isfinite(as_float(item["淨利率"])) else "—"),
        ("ROE", f"{item['ROE']:.1%}" if np.isfinite(as_float(item["ROE"])) else "—"),
        ("負債權益比", fmt_price(item["負債權益比"])),
        ("股利殖利率", f"{item['股利殖利率']:.1%}" if np.isfinite(as_float(item["股利殖利率"])) else "—"),
        ("資料狀態", item["資料狀態"]),
        ("估值限制", item["估值限制"]),
    ], columns=["項目", "數值／說明"])
    st.dataframe(valuation, hide_index=True, use_container_width=True)
    st.caption("合理價是以可取得 EPS 與本益比作敏感度參考，並非獨立評價或投資建議。")
    return item


# ------------------------------
# 側邊欄
# ------------------------------
with st.sidebar:
    st.header("功能選單")
    page = st.radio(
        "選擇功能",
        [
            "個股分析",
            "上市櫃全市場掃描",
            "技術強勢股排行榜",
            "自選股清單",
        ],
    )
    st.divider()
    st.caption("行情：Yahoo Finance；公司清單：TWSE／TPEx 公開 API。資料可延遲、缺漏或暫時無法取得。")


# ------------------------------
# 1. 個股分析
# ------------------------------
if page == "個股分析":
    st.subheader("🔎 個股趨勢＋量價分析")
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("輸入台股代號或名稱", value="2330", placeholder="例如：2330、台積電、1609、大亞")
    with col2:
        period_label = st.selectbox("歷史資料範圍", ["6 個月", "1 年", "2 年", "5 年"], index=1)
    period_map = {"6 個月": "6mo", "1 年": "1y", "2 年": "2y", "5 年": "5y"}

    # 固定顯示目前選取的股票，往下捲動頁面時仍能看見代號＋名稱。
    selected_symbol = resolve_symbol(query)
    selected_name = lookup_stock_name(selected_symbol) if selected_symbol else "請輸入股票"
    display_code = selected_symbol.split(".")[0] if selected_symbol else "—"
    sticky_stock_banner = (
        '<div style="position:sticky;top:0;z-index:9999;background:var(--background-color,#ffffff);'
        'border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:10px 14px;margin:8px 0 14px 0;'
        'box-shadow:0 2px 8px rgba(0,0,0,.08);">'
        '<div style="font-size:12px;opacity:.75;">目前分析標的</div>'
        f'<div style="font-size:22px;font-weight:750;line-height:1.4;">{display_code}｜{selected_name}</div>'
        '</div>'
    )
    st.markdown(sticky_stock_banner, unsafe_allow_html=True)

    if st.button("開始分析", type="primary", use_container_width=True):
        with st.spinner("下載行情並計算技術指標…"):
            result = analyze(query, period_map[period_label])
        show_analysis(result)
        if not result.get("error"):
            st.markdown("### 💰 合理價參考")
            fund = render_fundamental(result["代號"])
            fair_low = as_float(fund.get("估值參考低檔")) if isinstance(fund, dict) else np.nan
            fair_mid = as_float(fund.get("估值參考中位")) if isinstance(fund, dict) else np.nan
            fair_high = as_float(fund.get("估值參考高檔")) if isinstance(fund, dict) else np.nan
            if np.isfinite(fair_low) and np.isfinite(fair_mid) and np.isfinite(fair_high):
                st.info(
                    f"合理價參考區間：{fmt_price(fair_low)}～{fmt_price(fair_high)}；"
                    f"中位參考 {fmt_price(fair_mid)}。此估值依可取得的 EPS／本益比作敏感度推估，"
                    "不是保證價格，也不是獨立研究報告。"
                )
            else:
                st.warning("目前財務資料不足，無法可靠估算合理價；不以 0 元或任意數值代替。")

# ------------------------------
# 2. 上市櫃全市場掃描
# ------------------------------
elif page == "上市櫃全市場掃描":
    st.subheader("🌐 上市櫃全市場技術掃描")
    market_df, market_error = load_market_list()
    if market_error:
        st.caption(market_error)
    st.write(f"股票清單筆數：{len(market_df)}")
    if not market_df.empty:
        market_choice = st.selectbox("市場", ["全部", "上市", "上櫃"])
        subset = market_df if market_choice == "全部" else market_df[market_df["市場"] == market_choice]
        limit = st.number_input("本次最多掃描檔數（測試建議 20～100）", min_value=1, max_value=3000, value=50, step=10)
        if st.button("開始掃描市場", type="primary"):
            with st.spinner("掃描需要時間，請勿關閉頁面…"):
                scan_df = scan_market(subset, int(limit), market_choice)
            if not scan_df.empty:
                st.dataframe(scan_df, use_container_width=True, hide_index=True)
                dataframe_csv_download(scan_df, "tw_stock_market_scan.csv")

# ------------------------------
# 3. 技術強勢股排行榜
# ------------------------------
elif page == "技術強勢股排行榜":
    st.subheader("🏆 技術強勢股排行榜")
    market_df, market_error = load_market_list()
    if market_error:
        st.caption(market_error)
    if not market_df.empty:
        limit = st.number_input("掃描檔數", min_value=1, max_value=3000, value=50, step=10, key="rank_limit")
        if st.button("建立強勢排行榜", type="primary"):
            with st.spinner("計算技術分數…"):
                ranked = scan_market(market_df, int(limit), "技術排行榜")
            if not ranked.empty:
                ranked = ranked.sort_values(["技術分數", "20日乖離率(%)"], ascending=[False, True])
                st.dataframe(ranked, use_container_width=True, hide_index=True)
                dataframe_csv_download(ranked, "tw_stock_technical_rank.csv")

# ------------------------------
# 6. 自選股清單
# ------------------------------
elif page == "自選股清單":
    st.subheader("⭐ 自選股清單")
    st.caption("輸入多檔代號或名稱，以逗號、空白或換行分隔。")
    default_watchlist = "2330, 1609, 2340, 6117, 1802"
    watch_text = st.text_area("自選股", value=default_watchlist, height=120)
    period_label = st.selectbox("資料範圍", ["6 個月", "1 年", "2 年"], index=1, key="watch_period")
    period_map = {"6 個月": "6mo", "1 年": "1y", "2 年": "2y"}
    if st.button("分析自選股", type="primary"):
        symbols = [x.strip() for x in watch_text.replace("\n", ",").replace(" ", ",").split(",") if x.strip()]
        rows = []
        progress = st.progress(0)
        status = st.empty()
        for idx, symbol in enumerate(symbols, start=1):
            result = analyze(symbol, period_map[period_label])
            if not result.get("error"):
                rows.append(clean_result(result))
            else:
                st.warning(f"{symbol}：{result['error']}")
            progress.progress(idx / max(len(symbols), 1))
            status.text(f"自選股分析：{idx}/{len(symbols)}")
        progress.empty()
        status.empty()
        if rows:
            out = pd.DataFrame(rows)
            st.dataframe(out, use_container_width=True, hide_index=True)
            dataframe_csv_download(out, "tw_stock_watchlist.csv")

st.divider()
st.caption(
    "風險提醒：本工具為技術與公開財務資料整理，不構成投資建議。歷史價格不保證未來表現；"
    "公開資料可能延遲、缺漏、限流或有調整，請以券商與交易所最新資料為準。"
)
