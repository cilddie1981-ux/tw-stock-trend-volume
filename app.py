import io
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# =========================================================
# 台股趨勢指標 3.0
# 免費公開資料優先：TWSE / TPEx / Yahoo Finance
# =========================================================

st.set_page_config(
    page_title="台股趨勢指標 3.0",
    page_icon="📈",
    layout="wide",
)

st.title("📈 台股趨勢指標 3.0")
st.caption(
    "技術分析＋量價＋上市櫃掃描＋基本面估值。"
    "行情與財報可能延遲或缺漏，估值結果不保證準確，"
    "下單前請核對券商報價及公司最新財報。"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
}

TWSE_LIST_URL = (
    "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
)
TPEX_LIST_URL = (
    "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"
)

ALIASES = {
    "台積電": "2330.TW",
    "鴻海": "2317.TW",
    "聯發科": "2454.TW",
    "台達電": "2308.TW",
    "大亞": "1609.TW",
    "台亞": "2340.TW",
    "迎廣": "6117.TW",
    "台玻": "1802.TW",
    "聯穎": "3550.TW",
    "華邦電": "2344.TW",
    "南亞科": "2408.TW",
    "群創": "3481.TW",
    "友達": "2409.TW",
    "長榮": "2603.TW",
    "陽明": "2609.TW",
    "萬海": "2615.TW",
    "中鋼": "2002.TW",
    "國泰金": "2882.TW",
    "富邦金": "2881.TW",
    "元大金": "2885.TW",
    "中信金": "2891.TW",
    "玉山金": "2884.TW",
    "華航": "2610.TW",
    "長榮航": "2618.TW",
    "技嘉": "2376.TW",
    "微星": "2377.TW",
    "廣達": "2382.TW",
    "緯創": "3231.TW",
    "英業達": "2356.TW",
    "奇鋐": "3017.TW",
    "雙鴻": "3324.TW",
    "台光電": "2383.TW",
    "金像電": "2368.TW",
    "健策": "3653.TW",
    "世芯-KY": "3661.TW",
    "創意": "3443.TW",
    "力積電": "6770.TW",
    "世界": "5347.TWO",
    "中美晶": "5483.TWO",
    "台半": "5425.TWO",
    "欣興": "3037.TW",
    "南電": "8046.TW",
    "景碩": "3189.TW",
    "聯電": "2303.TW",
    "日月光投控": "3711.TW",
    "瑞昱": "2379.TW",
    "聯詠": "3034.TW",
    "大立光": "3008.TW",
    "台泥": "1101.TW",
    "亞泥": "1102.TW",
    "統一": "1216.TW",
    "遠東新": "1402.TW",
    "中華電": "2412.TW",
    "台灣大": "3045.TW",
    "遠傳": "4904.TW",
    "寶成": "9904.TW",
    "大成鋼": "2027.TW",
    "和碩": "4938.TW",
    "宏碁": "2353.TW",
    "華碩": "2357.TW",
    "緯穎": "6669.TW",
    "台燿": "6274.TW",
    "材料-KY": "4763.TW",
    "台塑": "1301.TW",
    "南亞": "1303.TW",
    "台化": "1326.TW",
    "原相": "3227.TWO",
    "創惟": "6104.TWO",
    "群聯": "8299.TWO",
    "譜瑞-KY": "4966.TW",
}


# =========================================================
# 共用工具
# =========================================================

def safe_float(value):
    try:
        x = float(value)
        return x if np.isfinite(x) else np.nan
    except (TypeError, ValueError):
        return np.nan


def fmt_num(value, digits=2):
    x = safe_float(value)
    if not np.isfinite(x):
        return "資料不足"
    return f"{x:,.{digits}f}"


def yahoo_symbol(code, market):
    code = str(code).strip()
    market = str(market).upper()

    if market == "上櫃":
        return f"{code}.TWO"

    return f"{code}.TW"


def resolve_symbol(query):
    q = str(query).strip()

    if not q:
        return ""

    if q in ALIASES:
        return ALIASES[q]

    upper = q.upper()

    if upper.endswith(".TW") or upper.endswith(".TWO"):
        return upper

    if upper.isdigit():
        return upper + ".TW"

    try:
        search = yf.Search(q, max_results=10)
        quotes = getattr(search, "quotes", []) or []

        for item in quotes:
            symbol = str(item.get("symbol", "")).upper()
            if symbol.endswith((".TW", ".TWO")):
                return symbol
    except Exception:
        pass

    return q


def fetch_json(url, timeout=20):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


# =========================================================
# 上市櫃股票名單
# =========================================================

@st.cache_data(ttl=86400, show_spinner=False)
def load_market_list():
    """
    取得上市、上櫃名單。

    由於公開 API 欄位可能調整，程式會先辨識欄位，
    如果來源失敗或欄位格式不符，回傳錯誤而非假名單。
    """
    frames = []
    errors = []

    sources = [
        ("上市", TWSE_LIST_URL),
        ("上櫃", TPEX_LIST_URL),
    ]

    code_candidates = [
        "公司代號",
        "股票代號",
        "有價證券代號",
        "SecuritiesCompanyCode",
        "公司代碼",
    ]

    name_candidates = [
        "公司簡稱",
        "公司名稱",
        "有價證券名稱",
        "CompanyName",
        "公司簡稱名稱",
    ]

    for market, url in sources:
        try:
            data = fetch_json(url)

            if not isinstance(data, list) or not data:
                raise ValueError("API 未回傳有效的清單")

            raw = pd.DataFrame(data)

            code_col = next(
                (c for c in code_candidates if c in raw.columns),
                None,
            )

            name_col = next(
                (c for c in name_candidates if c in raw.columns),
                None,
            )

            if code_col is None or name_col is None:
                raise ValueError(
                    "無法辨識股票代號或名稱欄位；"
                    f"目前欄位：{list(raw.columns)[:12]}"
                )

            part = pd.DataFrame({
                "代號": raw[code_col].astype(str).str.strip(),
                "名稱": raw[name_col].astype(str).str.strip(),
                "市場": market,
            })

            part = part[
                part["代號"].str.fullmatch(r"\d{4,6}", na=False)
            ]

            part = part[
                ~part["名稱"].str.contains(
                    "認購|認售|權證|牛證|熊證",
                    regex=True,
                    na=False,
                )
            ]

            part["Yahoo代號"] = part.apply(
                lambda row: yahoo_symbol(
                    row["代號"],
                    row["市場"],
                ),
                axis=1,
            )

            frames.append(part)

        except Exception as exc:
            errors.append(
                f"{market}清單取得失敗："
                f"{type(exc).__name__}: {str(exc)[:180]}"
            )

    if not frames:
        return pd.DataFrame(), errors

    result = pd.concat(frames, ignore_index=True)
    result = result.drop_duplicates(
        subset=["代號", "市場"]
    )

    return result.sort_values(
        ["市場", "代號"]
    ).reset_index(drop=True), errors


# =========================================================
# 行情下載與技術指標
# =========================================================

@st.cache_data(ttl=900, show_spinner=False)
def download_history(symbol, period="1y"):
    df = yf.download(
        symbol,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
        timeout=25,
        group_by="column",
        multi_level_index=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    needed = ["Close", "High", "Low", "Volume"]

    if not set(needed).issubset(df.columns):
        return pd.DataFrame()

    df = df[needed].copy()

    for col in needed:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.dropna(subset=["Close"])

    return df


def calculate_indicators(df):
    df = df.copy()

    c = df["Close"]
    h = df["High"]
    l = df["Low"]
    v = df["Volume"]

    for n in [5, 10, 20, 60]:
        df[f"MA{n}"] = c.rolling(n).mean()

    low9 = l.rolling(9).min()
    high9 = h.rolling(9).max()
    spread = (high9 - low9).replace(0, np.nan)

    rsv = (c - low9) / spread * 100

    df["K"] = rsv.ewm(
        alpha=1 / 3,
        adjust=False,
    ).mean()

    df["D"] = df["K"].ewm(
        alpha=1 / 3,
        adjust=False,
    ).mean()

    ema12 = c.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = c.ewm(
        span=26,
        adjust=False,
    ).mean()

    df["DIF"] = ema12 - ema26

    df["Signal"] = df["DIF"].ewm(
        span=9,
        adjust=False,
    ).mean()

    df["Hist"] = df["DIF"] - df["Signal"]

    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()

    rs = gain / loss.replace(0, np.nan)

    df["RSI"] = 100 - 100 / (1 + rs)

    df.loc[
        (loss == 0) & (gain > 0),
        "RSI",
    ] = 100

    df["Vol5"] = v.rolling(5).mean()
    df["Vol10"] = v.rolling(10).mean()

    df["Bias20"] = (
        c / df["MA20"] - 1
    ) * 100

    return df


def analyze(symbol, period="1y"):
    try:
        candidates = [symbol]

        if symbol.endswith(".TW"):
            candidates.append(
                symbol[:-3] + ".TWO"
            )
        elif symbol.endswith(".TWO"):
            candidates.append(
                symbol[:-4] + ".TW"
            )

        df = pd.DataFrame()
        actual_symbol = symbol
        errors = []

        for candidate in dict.fromkeys(candidates):
            try:
                trial = download_history(
                    candidate,
                    period,
                )

                if not trial.empty:
                    df = trial
                    actual_symbol = candidate
                    break

                errors.append(f"{candidate}: 無行情資料")

            except Exception as exc:
                errors.append(
                    f"{candidate}: {str(exc)[:100]}"
                )

        if df.empty:
            return None, (
                f"無法取得 {symbol} 行情。"
                + "；".join(errors[:3])
            )

        if len(df) < 60:
            return None, (
                f"{actual_symbol} 只有 {len(df)} 個交易日，"
                "不足以完整計算 60 日均線。"
            )

        df = calculate_indicators(df)

        x = df.iloc[-1]
        prev = df.iloc[-2]

        price = safe_float(x["Close"])
        ma5 = safe_float(x["MA5"])
        ma10 = safe_float(x["MA10"])
        ma20 = safe_float(x["MA20"])
        ma60 = safe_float(x["MA60"])

        k = safe_float(x["K"])
        d = safe_float(x["D"])
        hist = safe_float(x["Hist"])
        prev_hist = safe_float(prev["Hist"])
        rsi = safe_float(x["RSI"])
        vol5 = safe_float(x["Vol5"])
        vol10 = safe_float(x["Vol10"])
        bias20 = safe_float(x["Bias20"])

        if (
            np.isfinite(price)
            and np.isfinite(ma5)
            and np.isfinite(ma10)
            and np.isfinite(ma20)
            and np.isfinite(ma60)
            and price > ma5 > ma10 > ma20 > ma60
        ):
            trend = "強"
        elif price > ma20 and ma20 > ma60:
            trend = "偏強"
        elif price < ma20 and ma20 < ma60:
            trend = "弱"
        elif price < ma20:
            trend = "偏弱"
        else:
            trend = "中性"

        if price < ma20 and price < ma60:
            location = "低位/弱勢區"
        elif np.isfinite(bias20) and bias20 >= 12:
            location = "高位/乖離偏大"
        elif np.isfinite(ma20) and price >= ma20 * 1.12:
            location = "高位/乖離偏大"
        else:
            location = "中段"

        prev_k = safe_float(prev["K"])
        prev_d = safe_float(prev["D"])

        if (
            np.isfinite(k)
            and np.isfinite(d)
            and np.isfinite(prev_k)
            and np.isfinite(prev_d)
            and k > d
            and prev_k <= prev_d
        ):
            kd = "黃金交叉"
        elif (
            np.isfinite(k)
            and np.isfinite(d)
            and np.isfinite(prev_k)
            and np.isfinite(prev_d)
            and k < d
            and prev_k >= prev_d
        ):
            kd = "死亡交叉"
        elif np.isfinite(k) and k >= 80:
            kd = "高檔鈍化"
        elif np.isfinite(k) and k <= 20:
            kd = "低檔區"
        else:
            kd = "中性"

        if np.isfinite(hist) and np.isfinite(prev_hist):
            if hist > 0 and prev_hist <= 0:
                macd = "柱體翻紅"
            elif hist < 0 and prev_hist >= 0:
                macd = "柱體翻綠"
            elif hist > 0:
                macd = "多方"
            else:
                macd = "空方"
        else:
            macd = "資料不足"

        if not np.isfinite(rsi):
            rsi_text = "資料不足"
        elif rsi >= 70:
            rsi_text = f"{rsi:.1f}（超買）"
        elif rsi >= 60:
            rsi_text = f"{rsi:.1f}（強勢）"
        elif rsi < 30:
            rsi_text = f"{rsi:.1f}（超賣）"
        elif rsi < 40:
            rsi_text = f"{rsi:.1f}（偏弱）"
        else:
            rsi_text = f"{rsi:.1f}（中性）"

        today_vol = safe_float(x["Volume"])
        prev_close = safe_float(prev["Close"])

        if vol5 > vol10:
            volume_text = "5日均量高於10日均量"
        else:
            volume_text = "5日均量低於或等於10日均量"

        if (
            np.isfinite(today_vol)
            and np.isfinite(vol10)
            and today_vol > vol10 * 1.8
            and price < prev_close
        ):
            volume_text += "；爆量收低，留意賣壓"
        elif (
            np.isfinite(today_vol)
            and np.isfinite(vol10)
            and today_vol > vol10 * 1.5
            and price > prev_close
        ):
            volume_text += "；放量上漲"
        elif (
            np.isfinite(today_vol)
            and np.isfinite(vol10)
            and today_vol < vol10 * 0.6
        ):
            volume_text += "；成交量明顯萎縮"

        low20 = safe_float(df["Low"].tail(20).min())
        high20 = safe_float(df["High"].tail(20).max())

        support = (
            min(low20, ma20)
            if np.isfinite(ma20)
            else low20
        )

        resistance = high20

        stop = support * 0.97

        buy_low = max(
            support,
            price * 0.97,
        )

        buy_high = min(
            price,
            max(support * 1.02, buy_low),
        )

        breakout = resistance * 1.005
        false_break = resistance * 0.98

        target1 = price + (price - support) * 0.618
        target2 = price + (price - support)

        if (
            trend in ["強", "偏強"]
            and location == "中段"
            and np.isfinite(hist)
            and hist > 0
            and np.isfinite(vol5)
            and np.isfinite(vol10)
            and vol5 >= vol10
        ):
            signal = "🟢 偏多觀察"
        elif location.startswith("高位"):
            signal = "🟡 不追高"
        elif trend in ["弱", "偏弱"]:
            signal = "🔴 趨勢偏弱"
        else:
            signal = "🟡 等待確認"

        out = {
            "代號": actual_symbol,
            "資料日期": pd.Timestamp(df.index[-1]).strftime(
                "%Y-%m-%d"
            ),
            "現價": round(price, 2),
            "趨勢": trend,
            "位置": location,
            "5MA": round(ma5, 2) if np.isfinite(ma5) else np.nan,
            "10MA": round(ma10, 2) if np.isfinite(ma10) else np.nan,
            "20MA": round(ma20, 2) if np.isfinite(ma20) else np.nan,
            "60MA": round(ma60, 2) if np.isfinite(ma60) else np.nan,
            "KD": kd,
            "K值": round(k, 1) if np.isfinite(k) else np.nan,
            "D值": round(d, 1) if np.isfinite(d) else np.nan,
            "MACD": macd,
            "RSI": rsi_text,
            "量價": volume_text,
            "5日均量": int(vol5) if np.isfinite(vol5) else np.nan,
            "10日均量": int(vol10) if np.isfinite(vol10) else np.nan,
            "20日乖離率(%)": round(bias20, 2) if np.isfinite(bias20) else np.nan,
            "精準買點參考": f"{buy_low:.2f}～{buy_high:.2f}",
            "突破買點參考": round(breakout, 2),
            "停損參考": round(stop, 2),
            "第一目標參考": round(target1, 2),
            "第二目標參考": round(target2, 2),
            "假突破觀察價": round(false_break, 2),
            "近20日低點": round(low20, 2),
            "近20日高點": round(high20, 2),
            "目前訊號": signal,
        }

        out["_df"] = df
        return out, None

    except Exception as exc:
        return None, (
            f"{type(exc).__name__}: {str(exc)[:250]}"
        )


# =========================================================
# 基本面：Yahoo Finance 財務資料
# =========================================================

@st.cache_data(ttl=21600, show_spinner=False)
def fetch_fundamentals(symbol):
    """
    Yahoo Finance 的財務欄位不保證每檔完整。
    這裡只回傳實際取得的數值，不自行填補。
    """
    try:
        ticker = yf.Ticker(symbol)

        info = ticker.get_info() or {}

        eps = safe_float(info.get("trailingEps"))
        forward_eps = safe_float(info.get("forwardEps"))
        trailing_pe = safe_float(info.get("trailingPE"))
        forward_pe = safe_float(info.get("forwardPE"))
        book_value = safe_float(info.get("bookValue"))
        price = safe_float(info.get("currentPrice"))

        revenue_growth = safe_float(
            info.get("revenueGrowth")
        )

        profit_margin = safe_float(
            info.get("profitMargins")
        )

        operating_margin = safe_float(
            info.get("operatingMargins")
        )

        roe = safe_float(
            info.get("returnOnEquity")
        )

        debt_to_equity = safe_float(
            info.get("debtToEquity")
        )

        dividend_yield = safe_float(
            info.get("dividendYield")
        )

        # Yahoo Finance 財報表有時不提供相同欄位。
        # 只有實際可讀取到的資料才計算 TTM EPS。
        ttm_eps = np.nan

        try:
            income = ticker.quarterly_income_stmt

            if isinstance(income, pd.DataFrame) and not income.empty:
                eps_row = next(
                    (
                        name
                        for name in [
                            "Diluted EPS",
                            "Basic EPS",
                        ]
                        if name in income.index
                    ),
                    None,
                )

                if eps_row:
                    eps_values = pd.to_numeric(
                        income.loc[eps_row],
                        errors="coerce",
                    ).dropna()

                    if len(eps_values) >= 4:
                        ttm_eps = float(
                            eps_values.iloc[:4].sum()
                        )
        except Exception:
            pass

        if not np.isfinite(ttm_eps):
            ttm_eps = eps

        # 估值 EPS 優先採用預估 EPS；
        # 沒有預估值時使用可取得的 TTM EPS。
        valuation_eps = (
            forward_eps
            if np.isfinite(forward_eps) and forward_eps > 0
            else ttm_eps
        )

        # 使用已公開的歷史 PER 作為參考倍數。
        # 若無有效 PER，不硬套固定倍數。
        pe_reference = (
            forward_pe
            if np.isfinite(forward_pe) and forward_pe > 0
            else trailing_pe
        )

        if (
            np.isfinite(valuation_eps)
            and valuation_eps > 0
            and np.isfinite(pe_reference)
            and pe_reference > 0
        ):
            # 估值情境為分析假設，不是官方目標價。
            conservative_pe = pe_reference * 0.8
            base_pe = pe_reference
            optimistic_pe = pe_reference * 1.2

            conservative_price = (
                valuation_eps * conservative_pe
            )

            base_price = (
                valuation_eps * base_pe
            )

            optimistic_price = (
                valuation_eps * optimistic_pe
            )

            valuation_note = (
                "以可取得 EPS × 市場歷史/預估 PER 參考值；"
                "上下情境為假設，非保證價格。"
            )
        else:
            conservative_price = np.nan
            base_price = np.nan
            optimistic_price = np.nan

            valuation_note = (
                "EPS 或有效 PER 不足，無法可靠估算本益比合理價。"
            )

        return {
            "現價(財務來源)": price,
            "TTM EPS": ttm_eps,
            "預估 EPS": forward_eps,
            "參考 PER": pe_reference,
            "PBR": (
                price / book_value
                if np.isfinite(price)
                and np.isfinite(book_value)
                and book_value > 0
                else np.nan
            ),
            "營收成長率": revenue_growth,
            "獲利率": profit_margin,
            "營業利益率": operating_margin,
            "ROE": roe,
            "負債權益比": debt_to_equity,
            "殖利率": dividend_yield,
            "保守合理價": conservative_price,
            "中性合理價": base_price,
            "樂觀合理價": optimistic_price,
            "估值說明": valuation_note,
            "資料狀態": (
                "部分欄位已取得"
                if np.isfinite(ttm_eps)
                or np.isfinite(forward_eps)
                else "EPS 資料不足"
            ),
        }

    except Exception as exc:
        return {
            "資料狀態": (
                f"取得失敗：{type(exc).__name__}"
            ),
            "估值說明": str(exc)[:160],
        }


def fundamental_row(symbol):
    return fetch_fundamentals(symbol)


# =========================================================
# 排名評分
# =========================================================

def technical_score(result):
    score = 0

    score += {
        "強": 3,
        "偏強": 2,
        "中性": 1,
        "偏弱": 0,
        "弱": -1,
    }.get(result.get("趨勢"), 0)

    macd = str(result.get("MACD", ""))

    if "多方" in macd or "翻紅" in macd:
        score += 2
    elif "空方" in macd or "翻綠" in macd:
        score -= 1

    kd = str(result.get("KD", ""))

    if "黃金交叉" in kd:
        score += 1
    elif "死亡交叉" in kd:
        score -= 1

    rsi_text = str(result.get("RSI", ""))

    try:
        rsi = float(rsi_text.split("（")[0])

        if 50 <= rsi <= 70:
            score += 1
        elif rsi > 75 or rsi < 40:
            score -= 1
    except (ValueError, AttributeError):
        pass

    if "高於10日均量" in str(result.get("量價", "")):
        score += 1

    if "高位" in str(result.get("位置", "")):
        score -= 2

    return score


def clean_result(result):
    return {
        key: value
        for key, value in result.items()
        if not key.startswith("_")
    }


# =========================================================
# 顯示個股分析
# =========================================================

def show_analysis(result):
    st.subheader(f"📊 {result['代號']} 技術分析")

    st.warning(
        f"行情日期：{result['資料日期']}；"
        f"最近收盤價：{result['現價']}。"
        "這不是即時成交價。"
    )

    left, right = st.columns(2)

    keys = [
        "現價", "趨勢", "位置",
        "5MA", "10MA", "20MA", "60MA",
        "KD", "K值", "D值",
        "MACD", "RSI", "量價",
        "5日均量", "10日均量",
        "20日乖離率(%)",
        "精準買點參考", "突破買點參考",
        "停損參考", "第一目標參考",
        "第二目標參考", "假突破觀察價",
        "目前訊號",
    ]

    for i, key in enumerate(keys):
        with (left if i % 2 == 0 else right):
            st.write(f"**{key}：** {result.get(key, '—')}")

    st.markdown("### 📅 不同持有週期")

    st.write(
        "**短線：**觀察 5MA、10MA、量價及近 20 日支撐。"
    )
    st.write(
        "**波段：**觀察 20MA、60MA、突破有效性與回測。"
    )
    st.write(
        "**長期：**需搭配財報、產業、現金流與估值，"
        "不能只依均線判斷。"
    )

    if st.button(
        "取得基本面與合理價",
        key=f"fund_{result['代號']}",
    ):
        with st.spinner("正在取得基本面資料……"):
            fundamentals = fundamental_row(result["代號"])

        st.subheader("💰 基本面估值")

        for key, value in fundamentals.items():
            if key == "估值說明":
                st.info(value)
            elif isinstance(value, (int, float, np.number)):
                st.write(f"**{key}：** {fmt_num(value)}")
            else:
                st.write(f"**{key}：** {value}")

        if (
            np.isfinite(
                safe_float(fundamentals.get("中性合理價"))
            )
            and result["現價"] > 0
        ):
            fair = float(fundamentals["中性合理價"])
            upside = (fair / result["現價"] - 1) * 100

            st.metric(
                "中性估值相對最近收盤價",
                f"{upside:+.1f}%",
                help=(
                    "依可取得 EPS 及 PER 估算，"
                    "不是預期報酬或保證價格。"
                ),
            )

    with st.expander("查看價格與均線圖"):
        df = result["_df"].tail(120)

        chart = df[
            ["Close", "MA5", "MA10", "MA20", "MA60"]
        ].rename(
            columns={
                "Close": "收盤價",
                "MA5": "5MA",
                "MA10": "10MA",
                "MA20": "20MA",
                "MA60": "60MA",
            }
        )

        st.line_chart(chart)

        st.dataframe(
            df[
                [
                    "Close", "Volume",
                    "MA5", "MA10", "MA20", "MA60",
                    "K", "D", "DIF", "Signal", "Hist", "RSI",
                ]
            ].tail(15).round(2),
            use_container_width=True,
        )


# =========================================================
# 全市場掃描
# =========================================================

def scan_market(market_df, period, limit=None):
    """
    分批逐檔掃描。
    免費行情來源可能限流，因此採取保守節奏。
    """
    work = market_df.copy()

    if limit is not None:
        work = work.head(int(limit))

    total = len(work)

    if total == 0:
        return pd.DataFrame(), []

    progress = st.progress(0)
    status = st.empty()

    rows = []
    errors = []

    for i, (_, stock) in enumerate(work.iterrows(), start=1):
        code = str(stock["代號"])
        name = str(stock["名稱"])
        symbol = str(stock["Yahoo代號"])

        status.write(
            f"掃描中：{i}/{total} — {code} {name}"
        )

        result, err = analyze(symbol, period)

        if result:
            row = clean_result(result)
            row["股票名稱"] = name
            row["市場"] = stock["市場"]
            row["評分"] = technical_score(result)
            rows.append(row)
        else:
            errors.append(
                f"{code} {name} ({symbol})：{err}"
            )

        progress.progress(i / total)

        # 降低免費行情來源被限流的機率。
        # 已有快取時不一定需要等待。
        time.sleep(0.03)

    status.write(
        f"掃描完成：成功 {len(rows)} 檔，失敗 {len(errors)} 檔。"
    )

    return pd.DataFrame(rows), errors


# =========================================================
# 側邊欄
# =========================================================

st.sidebar.title("功能選單")

mode = st.sidebar.radio(
    "選擇功能",
    [
        "個股分析",
        "上市櫃全市場掃描",
        "技術強勢股排行榜",
        "基本面合理價掃描",
        "技術＋基本面交集",
        "自選股清單",
    ],
)

st.sidebar.caption(
    "行情來源：Yahoo Finance；"
    "股票名單：TWSE / TPEx 公開 API。"
)


# =========================================================
# 頁面一：個股分析
# =========================================================

if mode == "個股分析":
    query = st.text_input(
        "輸入股票代號或名稱",
        placeholder="例如：2330、台積電、1609、大亞",
    )

    period = st.selectbox(
        "歷史行情期間",
        ["6mo", "1y", "2y"],
        index=1,
    )

    if st.button("開始分析", type="primary") and query.strip():
        symbol = resolve_symbol(query)

        with st.spinner(f"正在取得 {symbol} 行情……"):
            result, err = analyze(symbol, period)

        if err:
            st.error(err)
        else:
            show_analysis(result)


# =========================================================
# 頁面二：上市櫃全市場掃描
# =========================================================

elif mode == "上市櫃全市場掃描":
    st.subheader("🔎 上市櫃全市場掃描")

    st.write(
        "先取得上市、上櫃股票清單，再逐檔掃描歷史行情。"
        "完整掃描可能需要較長時間；免費資料來源也可能限流。"
    )

    if st.button("更新股票清單"):
        load_market_list.clear()

    market_df, list_errors = load_market_list()

    if list_errors:
        with st.expander("股票清單來源訊息"):
            st.text("\n".join(list_errors))

    if market_df.empty:
        st.error(
            "無法取得有效的上市櫃股票名單。"
            "可能是公開 API 欄位變更或來源暫時無法連線。"
        )
    else:
        st.success(
            f"目前取得 {len(market_df)} 檔股票名單。"
        )

        market_filter = st.multiselect(
            "選擇市場",
            ["上市", "上櫃"],
            default=["上市", "上櫃"],
        )

        filtered = market_df[
            market_df["市場"].isin(market_filter)
        ].copy()

        st.write(
            f"符合市場條件：{len(filtered)} 檔"
        )

        scan_limit = st.selectbox(
            "本次掃描數量",
            [
                50,
                100,
                300,
                500,
                "全部",
            ],
            index=0,
            help=(
                "建議先掃描 50～100 檔測試。"
                "全部掃描可能花費很長時間。"
            ),
        )

        period = st.selectbox(
            "行情期間",
            ["6mo", "1y", "2y"],
            index=0,
            key="market_period",
        )

        if st.button("開始全市場掃描", type="primary"):
            limit = (
                None
                if scan_limit == "全部"
                else int(scan_limit)
            )

            with st.spinner("正在掃描，請勿關閉頁面……"):
                table, errors = scan_market(
                    filtered,
                    period,
                    limit,
                )

            if not table.empty:
                st.session_state["market_scan"] = table
                st.session_state["market_errors"] = errors
            else:
                st.warning("本次沒有取得成功的行情資料。")
                st.session_state["market_scan"] = pd.DataFrame()
                st.session_state["market_errors"] = errors

        table = st.session_state.get(
            "market_scan",
            pd.DataFrame(),
        )

        if not table.empty:
            st.subheader("掃描結果")

            st.dataframe(
                table.sort_values(
                    "評分",
                    ascending=False,
                ),
                use_container_width=True,
            )

            st.download_button(
                "下載全市場掃描 CSV",
                table.to_csv(
                    index=False,
                    encoding="utf-8-sig",
                ).encode("utf-8-sig"),
                file_name=(
                    f"tw_market_scan_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv",
            )

        errors = st.session_state.get(
            "market_errors",
            [],
        )

        if errors:
            with st.expander(
                f"行情失敗紀錄：{len(errors)} 檔"
            ):
                st.text("\n".join(errors[:500]))


# =========================================================
# 頁面三：技術強勢股排行榜
# =========================================================

elif mode == "技術強勢股排行榜":
    st.subheader("🏆 技術強勢股排行榜")

    st.write(
        "此頁從上市櫃清單中掃描指定數量股票，"
        "依均線趨勢、MACD、KD、RSI 及量能排序。"
    )

    market_df, list_errors = load_market_list()

    if market_df.empty:
        st.error("無法取得上市櫃清單。")
    else:
        limit = st.selectbox(
            "掃描數量",
            [50, 100, 300, 500, "全部"],
            index=0,
            key="rank_limit",
        )

        markets = st.multiselect(
            "市場",
            ["上市", "上櫃"],
            default=["上市", "上櫃"],
            key="rank_market",
        )

        filtered = market_df[
            market_df["市場"].isin(markets)
        ]

        if st.button("開始排名", type="primary"):
            table, errors = scan_market(
                filtered,
                "6mo",
                None if limit == "全部" else int(limit),
            )

            st.session_state["rank_table"] = table
            st.session_state["rank_errors"] = errors

        table = st.session_state.get(
            "rank_table",
            pd.DataFrame(),
        )

        if not table.empty:
            table = table.sort_values(
                ["評分", "20日乖離率(%)"],
                ascending=[False, True],
                na_position="last",
            )

            st.dataframe(
                table,
                use_container_width=True,
            )

            st.download_button(
                "下載排行榜 CSV",
                table.to_csv(
                    index=False,
                    encoding="utf-8-sig",
                ).encode("utf-8-sig"),
                file_name=(
                    f"tw_strength_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv",
            )

        errors = st.session_state.get("rank_errors", [])

        if errors:
            with st.expander(f"失敗紀錄：{len(errors)} 檔"):
                st.text("\n".join(errors[:500]))


# =========================================================
# 頁面四：基本面合理價掃描
# =========================================================

elif mode == "基本面合理價掃描":
    st.subheader("💰 基本面合理價掃描")

    st.warning(
        "財報與估值欄位依 Yahoo Finance 實際回傳為準。"
        "這裡的合理價是模型估算，不是官方目標價。"
    )

    market_df, list_errors = load_market_list()

    if market_df.empty:
        st.error("無法取得上市櫃股票名單。")
    else:
        markets = st.multiselect(
            "選擇市場",
            ["上市", "上櫃"],
            default=["上市", "上櫃"],
            key="fair_market",
        )

        candidates = market_df[
            market_df["市場"].isin(markets)
        ].copy()

        limit = st.selectbox(
            "基本面分析數量",
            [10, 20, 50, 100, 300],
            index=1,
            help="基本面查詢比技術掃描耗時，建議先從 20 檔測試。",
        )

        st.caption(
            "此功能依目前股票清單順序查詢指定數量，"
            "不是已經對全市場所有股票完成估值。"
        )

        if st.button("開始基本面估值", type="primary"):
            work = candidates.head(int(limit))
            rows = []
            errors = []

            progress = st.progress(0)
            status = st.empty()

            for i, (_, stock) in enumerate(
                work.iterrows(),
                start=1,
            ):
                symbol = stock["Yahoo代號"]

                status.write(
                    f"查詢財報：{i}/{len(work)} "
                    f"{stock['代號']} {stock['名稱']}"
                )

                data = fundamental_row(symbol)

                row = {
                    "代號": stock["代號"],
                    "名稱": stock["名稱"],
                    "市場": stock["市場"],
                    "Yahoo代號": symbol,
                }

                row.update(data)

                if "取得失敗" in str(data.get("資料狀態", "")):
                    errors.append(
                        f"{symbol}：{data.get('資料狀態')}"
                    )

                rows.append(row)

                progress.progress(
                    i / max(1, len(work))
                )

            table = pd.DataFrame(rows)

            if "中性合理價" in table.columns:
                table["中性估值折溢價(%)"] = (
                    table["中性合理價"]
                    / table["現價(財務來源)"]
                    - 1
                ) * 100

            st.session_state["fundamental_table"] = table
            st.session_state["fundamental_errors"] = errors

        table = st.session_state.get(
            "fundamental_table",
            pd.DataFrame(),
        )

        if not table.empty:
            st.dataframe(
                table,
                use_container_width=True,
            )

            st.download_button(
                "下載基本面估值 CSV",
                table.to_csv(
                    index=False,
                    encoding="utf-8-sig",
                ).encode("utf-8-sig"),
                file_name=(
                    f"tw_fundamental_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv",
            )

        errors = st.session_state.get(
            "fundamental_errors",
            [],
        )

        if errors:
            with st.expander(
                f"財務資料失敗：{len(errors)} 檔"
            ):
                st.text("\n".join(errors[:500]))


# =========================================================
# 頁面五：技術＋基本面交集
# =========================================================

elif mode == "技術＋基本面交集":
    st.subheader("🎯 技術面＋基本面交集")

    st.write(
        "先掃描技術面，再對技術評分較高的股票進行估值。"
        "此流程減少對免費財務來源的請求。"
    )

    market_df, list_errors = load_market_list()

    if market_df.empty:
        st.error("無法取得上市櫃清單。")
    else:
        scan_limit = st.selectbox(
            "技術掃描數量",
            [50, 100, 200, 300],
            index=0,
            key="combo_scan_limit",
        )

        top_n = st.selectbox(
            "進一步分析前幾名",
            [5, 10, 20, 30],
            index=1,
            key="combo_top_n",
        )

        if st.button("執行交集分析", type="primary"):
            technical, errors = scan_market(
                market_df,
                "6mo",
                int(scan_limit),
            )

            if technical.empty:
                st.warning("沒有取得可用技術行情。")
            else:
                technical = technical.sort_values(
                    "評分",
                    ascending=False,
                ).head(int(top_n))

                rows = []

                for i, (_, item) in enumerate(
                    technical.iterrows(),
                    start=1,
                ):
                    symbol = item["代號"]

                    status = st.empty()
                    status.write(
                        f"分析基本面：{i}/{len(technical)} "
                        f"{symbol}"
                    )

                    fundamentals = fundamental_row(symbol)

                    row = item.to_dict()
                    row.update(fundamentals)
                    rows.append(row)

                result_df = pd.DataFrame(rows)

                if (
                    "中性合理價" in result_df.columns
                    and "現價" in result_df.columns
                ):
                    result_df["估值空間(%)"] = (
                        result_df["中性合理價"]
                        / result_df["現價"]
                        - 1
                    ) * 100

                st.session_state["combo_table"] = result_df
                st.session_state["combo_errors"] = errors

        result_df = st.session_state.get(
            "combo_table",
            pd.DataFrame(),
        )

        if not result_df.empty:
            st.dataframe(
                result_df,
                use_container_width=True,
            )

            if "估值空間(%)" in result_df.columns:
                valid = result_df[
                    pd.to_numeric(
                        result_df["估值空間(%)"],
                        errors="coerce",
                    ) > 0
                ]

                st.subheader(
                    "符合中性估值高於最近收盤價的股票"
                )

                st.dataframe(
                    valid,
                    use_container_width=True,
                )

            st.download_button(
                "下載技術＋基本面結果 CSV",
                result_df.to_csv(
                    index=False,
                    encoding="utf-8-sig",
                ).encode("utf-8-sig"),
                file_name=(
                    f"tw_technical_fundamental_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv",
            )


# =========================================================
# 頁面六：自選股清單
# =========================================================

else:
    st.subheader("⭐ 自選股清單")

    text_in = st.text_area(
        "每行輸入一檔股票",
        value="2330\n台積電\n1609\n大亞\n6117\n迎廣",
    )

    period = st.selectbox(
        "歷史資料期間",
        ["6mo", "1y", "2y"],
        index=1,
        key="watch_period",
    )

    if st.button("分析自選股", type="primary"):
        queries = list(
            dict.fromkeys(
                line.strip()
                for line in text_in.splitlines()
                if line.strip()
            )
        )

        rows = []
        errors = []

        progress = st.progress(0)

        for i, query in enumerate(queries, start=1):
            symbol = resolve_symbol(query)

            result, err = analyze(
                symbol,
                period,
            )

            if result:
                rows.append(clean_result(result))
            else:
                errors.append(
                    f"{query} ({symbol})：{err}"
                )

            progress.progress(
                i / max(1, len(queries))
            )

        if rows:
            table = pd.DataFrame(rows)

            st.dataframe(
                table,
                use_container_width=True,
            )

            st.download_button(
                "下載自選股 CSV",
                table.to_csv(
                    index=False,
                    encoding="utf-8-sig",
                ).encode("utf-8-sig"),
                file_name=(
                    f"tw_watchlist_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv",
            )

        if errors:
            with st.expander(
                f"分析失敗：{len(errors)} 檔"
            ):
                st.text("\n".join(errors))
