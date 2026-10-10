import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime


# =========================================================
# 頁面設定
# =========================================================

st.set_page_config(
    page_title="台股趨勢指標 2.3",
    page_icon="📈",
    layout="wide"
)

st.title("📈 台股趨勢指標＋量價分析 2.3")

st.caption(
    "技術分析為交易研究輔助，不保證獲利。"
    "資料可能延遲或缺漏；下單前請核對券商即時報價。"
)


# =========================================================
# 台股代號對照表
# =========================================================

ALIASES = {
    "台積電": "2330.TW", "2330": "2330.TW",
    "鴻海": "2317.TW", "2317": "2317.TW",
    "聯發科": "2454.TW", "2454": "2454.TW",
    "台達電": "2308.TW", "2308": "2308.TW",
    "大亞": "1609.TW", "1609": "1609.TW",
    "台亞": "2340.TW", "2340": "2340.TW",
    "迎廣": "6117.TW", "6117": "6117.TW",
    "台玻": "1802.TW", "1802": "1802.TW",
    "聯穎": "3550.TW", "3550": "3550.TW",
    "華邦電": "2344.TW", "2344": "2344.TW",
    "南亞科": "2408.TW", "2408": "2408.TW",
    "群創": "3481.TW", "3481": "3481.TW",
    "友達": "2409.TW", "2409": "2409.TW",
    "長榮": "2603.TW", "2603": "2603.TW",
    "陽明": "2609.TW", "2609": "2609.TW",
    "萬海": "2615.TW", "2615": "2615.TW",
    "中鋼": "2002.TW", "2002": "2002.TW",
    "國泰金": "2882.TW", "2882": "2882.TW",
    "富邦金": "2881.TW", "2881": "2881.TW",
    "元大金": "2885.TW", "2885": "2885.TW",
    "中信金": "2891.TW", "2891": "2891.TW",
    "玉山金": "2884.TW", "2884": "2884.TW",
    "華航": "2610.TW", "2610": "2610.TW",
    "長榮航": "2618.TW", "2618": "2618.TW",
    "技嘉": "2376.TW", "2376": "2376.TW",
    "微星": "2377.TW", "2377": "2377.TW",
    "廣達": "2382.TW", "2382": "2382.TW",
    "緯創": "3231.TW", "3231": "3231.TW",
    "英業達": "2356.TW", "2356": "2356.TW",
    "奇鋐": "3017.TW", "3017": "3017.TW",
    "雙鴻": "3324.TW", "3324": "3324.TW",
    "台光電": "2383.TW", "2383": "2383.TW",
    "金像電": "2368.TW", "2368": "2368.TW",
    "健策": "3653.TW", "3653": "3653.TW",
    "世芯-KY": "3661.TW", "3661": "3661.TW",
    "創意": "3443.TW", "3443": "3443.TW",
    "力積電": "6770.TW", "6770": "6770.TW",
    "世界": "5347.TWO", "5347": "5347.TWO",
    "中美晶": "5483.TWO", "5483": "5483.TWO",
    "台半": "5425.TWO", "5425": "5425.TWO",
    "欣興": "3037.TW", "3037": "3037.TW",
    "南電": "8046.TW", "8046": "8046.TW",
    "景碩": "3189.TW", "3189": "3189.TW",
    "聯電": "2303.TW", "2303": "2303.TW",
    "日月光投控": "3711.TW", "3711": "3711.TW",
    "瑞昱": "2379.TW", "2379": "2379.TW",
    "聯詠": "3034.TW", "3034": "3034.TW",
    "大立光": "3008.TW", "3008": "3008.TW",
    "台泥": "1101.TW", "1101": "1101.TW",
    "亞泥": "1102.TW", "1102": "1102.TW",
    "統一": "1216.TW", "1216": "1216.TW",
    "遠東新": "1402.TW", "1402": "1402.TW",
    "中華電": "2412.TW", "2412": "2412.TW",
    "台灣大": "3045.TW", "3045": "3045.TW",
    "遠傳": "4904.TW", "4904": "4904.TW",
    "寶成": "9904.TW", "9904": "9904.TW",
    "大成鋼": "2027.TW", "2027": "2027.TW",
    "和碩": "4938.TW", "4938": "4938.TW",
    "宏碁": "2353.TW", "2353": "2353.TW",
    "華碩": "2357.TW", "2357": "2357.TW",
    "緯穎": "6669.TW", "6669": "6669.TW",
    "台燿": "6274.TW", "6274": "6274.TW",
    "材料-KY": "4763.TW", "4763": "4763.TW",
    "台塑": "1301.TW", "1301": "1301.TW",
    "南亞": "1303.TW", "1303": "1303.TW",
    "台化": "1326.TW", "1326": "1326.TW",
    "原相": "3227.TWO", "3227": "3227.TWO",
    "創惟": "6104.TWO", "6104": "6104.TWO",
    "群聯": "8299.TWO", "8299": "8299.TWO",
    "譜瑞-KY": "4966.TW", "4966": "4966.TW",
}


# =========================================================
# 股票代號處理
# =========================================================

def symbol_candidates(q):
    q = str(q).strip()

    if not q:
        return []

    # 先使用內建代號表
    mapped = ALIASES.get(q)

    if mapped:
        code, suffix = mapped.rsplit(".", 1)
        other = ".TWO" if suffix == "TW" else ".TW"
        return [mapped, code + other]

    # 使用者輸入 Yahoo Finance 格式
    upper_q = q.upper()

    if upper_q.endswith(".TW"):
        code = upper_q[:-3]
        return [code + ".TW", code + ".TWO"]

    if upper_q.endswith(".TWO"):
        code = upper_q[:-4]
        return [code + ".TWO", code + ".TW"]

    # 純數字股票代號
    if upper_q.isdigit():
        return [upper_q + ".TW", upper_q + ".TWO"]

    # 嘗試 Yahoo Finance 搜尋中文或其他公司名稱
    candidates = []

    try:
        result = yf.Search(q, max_results=20)
        quotes = getattr(result, "quotes", []) or []

        for item in quotes:
            ticker = str(item.get("symbol", "")).upper()

            if ticker.endswith((".TW", ".TWO")):
                if ticker not in candidates:
                    candidates.append(ticker)

    except Exception:
        pass

    return candidates


def resolve_symbol(q):
    candidates = symbol_candidates(q)

    if candidates:
        return candidates[0]

    return str(q).strip()


# =========================================================
# 技術分析主程式
# =========================================================

def analyze(symbol, period="1y"):

    try:
        # 修正原本的語法錯誤
        candidates = symbol_candidates(symbol) or [symbol]

        df = None
        actual_symbol = symbol
        errors = []

        # 依序嘗試不同的股票代號
        for candidate in candidates:

            try:
                trial = yf.download(
                    candidate,
                    period=period,
                    interval="1d",
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    timeout=30,
                    group_by="column",
                    multi_level_index=False
                )

                if trial is not None and not trial.empty:
                    df = trial
                    actual_symbol = candidate
                    break

                errors.append(f"{candidate}: 空資料")

            except Exception as e:
                errors.append(
                    f"{candidate}: {str(e)[:120]}"
                )

        if df is None or df.empty:
            detail = "；".join(errors[:4])

            return None, (
                f"查無可用日線行情：{symbol}。"
                f"已嘗試：{', '.join(candidates)}。"
                f"錯誤細節：{detail or '來源沒有回傳資料'}。"
                "請確認代號或稍後再試。"
            )

        symbol = actual_symbol

        # 處理 Yahoo Finance 可能回傳的多層欄位
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        required = {"Close", "High", "Low", "Volume"}

        if not required.issubset(df.columns):
            return None, "行情欄位不完整，無法計算技術指標。"

        df = df.dropna(subset=["Close"]).copy()

        if len(df) < 60:
            return None, (
                f"{symbol} 歷史資料只有 {len(df)} 個交易日，"
                "不足以完整計算 60 日均線。"
            )

        c = df["Close"].astype(float)
        h = df["High"].astype(float)
        l = df["Low"].astype(float)
        v = df["Volume"].astype(float)

        # -------------------------------------------------
        # 均線
        # -------------------------------------------------

        for n in [5, 10, 20, 60]:
            df[f"MA{n}"] = c.rolling(n).mean()

        # -------------------------------------------------
        # KD
        # -------------------------------------------------

        low_n = l.rolling(9).min()
        high_n = h.rolling(9).max()

        rsv = (
            (c - low_n)
            / (high_n - low_n).replace(0, np.nan)
            * 100
        )

        df["K"] = rsv.ewm(
            alpha=1 / 3,
            adjust=False
        ).mean()

        df["D"] = df["K"].ewm(
            alpha=1 / 3,
            adjust=False
        ).mean()

        # -------------------------------------------------
        # MACD
        # -------------------------------------------------

        ema12 = c.ewm(span=12, adjust=False).mean()
        ema26 = c.ewm(span=26, adjust=False).mean()

        df["DIF"] = ema12 - ema26

        df["Signal"] = df["DIF"].ewm(
            span=9,
            adjust=False
        ).mean()

        df["Hist"] = df["DIF"] - df["Signal"]

        # -------------------------------------------------
        # RSI
        # -------------------------------------------------

        delta = c.diff()

        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()

        rs = gain / loss.replace(0, np.nan)

        df["RSI"] = 100 - (100 / (1 + rs))

        # 避免連續上漲造成 RSI 缺值
        df.loc[
            (loss == 0) & (gain > 0),
            "RSI"
        ] = 100

        # -------------------------------------------------
        # 成交量與乖離率
        # -------------------------------------------------

        df["Vol5"] = v.rolling(5).mean()
        df["Vol10"] = v.rolling(10).mean()

        df["Bias20"] = (
            (c / df["MA20"]) - 1
        ) * 100

        x = df.iloc[-1]
        prev = df.iloc[-2]

        price = float(x["Close"])

        def val(key):
            z = x.get(key, np.nan)

            if pd.notna(z):
                return float(z)

            return np.nan

        ma5 = val("MA5")
        ma10 = val("MA10")
        ma20 = val("MA20")
        ma60 = val("MA60")

        # -------------------------------------------------
        # 趨勢判斷
        # -------------------------------------------------

        if price > ma5 > ma10 > ma20 > ma60:
            trend = "強"

        elif price > ma20 and ma20 > ma60:
            trend = "偏強"

        elif price < ma20 and ma20 < ma60:
            trend = "弱"

        elif price < ma20:
            trend = "偏弱"

        else:
            trend = "中性"

        # -------------------------------------------------
        # 股價位置
        # -------------------------------------------------

        bias20 = val("Bias20")

        if price < ma20 and price < ma60:
            location = "低位/弱勢區（仍需確認止跌）"

        elif (
            price > ma20 * 1.12
            or (
                np.isfinite(bias20)
                and bias20 > 12
            )
        ):
            location = "高位/乖離偏大"

        else:
            location = "中段（依趨勢續判）"

        # -------------------------------------------------
        # KD 判斷
        # -------------------------------------------------

        k = val("K")
        d = val("D")

        prev_k = float(prev["K"])
        prev_d = float(prev["D"])

        if (
            np.isfinite(k)
            and np.isfinite(d)
            and k > d
            and prev_k <= prev_d
        ):
            kd = "黃金交叉"

        elif (
            np.isfinite(k)
            and np.isfinite(d)
            and k < d
            and prev_k >= prev_d
        ):
            kd = "死亡交叉"

        elif np.isfinite(k) and k >= 80:
            kd = "高檔鈍化/偏熱"

        elif np.isfinite(k) and k <= 20:
            kd = "低檔區"

        else:
            kd = "中性"

        # -------------------------------------------------
        # MACD 判斷
        # -------------------------------------------------

        hist = val("Hist")
        prev_hist = float(prev["Hist"])

        if hist > 0 and prev_hist <= 0:
            macd = "柱體翻紅"

        elif hist < 0 and prev_hist >= 0:
            macd = "柱體翻綠"

        elif hist > 0:
            macd = "多方"

        else:
            macd = "空方"

        # -------------------------------------------------
        # RSI 判斷
        # -------------------------------------------------

        rsi = val("RSI")

        if not np.isfinite(rsi):
            rsi_txt = "資料不足"

        elif rsi >= 70:
            rsi_txt = f"{rsi:.1f}（超買/偏熱）"

        elif rsi >= 60:
            rsi_txt = f"{rsi:.1f}（強勢）"

        elif rsi < 30:
            rsi_txt = f"{rsi:.1f}（超賣）"

        elif rsi < 40:
            rsi_txt = f"{rsi:.1f}（偏弱）"

        else:
            rsi_txt = f"{rsi:.1f}（中性）"

        # -------------------------------------------------
        # 量價分析
        # -------------------------------------------------

        vol5 = val("Vol5")
        vol10 = val("Vol10")
        today_vol = float(v.iloc[-1])
        prev_close = float(prev["Close"])

        if vol5 > vol10:
            volume_txt = "5日均量高於10日均量"
        else:
            volume_txt = "5日均量低於或等於10日均量"

        if (
            np.isfinite(vol10)
            and today_vol > vol10 * 1.8
            and price < prev_close
        ):
            volume_txt += "；爆量收低，留意賣壓"

        elif (
            np.isfinite(vol10)
            and today_vol > vol10 * 1.5
            and price > prev_close
        ):
            volume_txt += "；放量上漲"

        elif (
            np.isfinite(vol10)
            and today_vol < vol10 * 0.6
        ):
            volume_txt += "；成交量明顯萎縮"

        # -------------------------------------------------
        # 支撐、壓力與交易參考價
        # -------------------------------------------------

        recent_low = float(l.tail(20).min())
        recent_high = float(h.tail(20).max())

        if np.isfinite(ma20):
            support = min(recent_low, ma20)
        else:
            support = recent_low

        resistance = recent_high

        stop = round(support * 0.97, 2)

        buy_low = round(
            max(support, price * 0.97),
            2
        )

        buy_high = round(
            min(
                price,
                max(support * 1.02, buy_low)
            ),
            2
        )

        breakout = round(
            resistance * 1.005,
            2
        )

        if price > support:
            target1 = round(
                price + (price - support) * 0.618,
                2
            )

            target2 = round(
                price + (price - support),
                2
            )

        else:
            target1 = round(price * 1.05, 2)
            target2 = round(price * 1.10, 2)

        false_break = round(
            resistance * 0.98,
            2
        )

        # -------------------------------------------------
        # 綜合訊號
        # -------------------------------------------------

        if (
            trend in ["強", "偏強"]
            and location.startswith("中段")
            and hist > 0
            and vol5 >= vol10
        ):
            signal = "🟢 偏多；可考慮分批或等待回測"

        elif location.startswith("高位"):
            signal = "🟡 不追高；等待拉回或整理"

        elif trend in ["弱", "偏弱"]:
            signal = "🔴 趨勢偏弱；觀望並留意停損"

        else:
            signal = "🟡 觀察；等待量價與趨勢確認"

        # -------------------------------------------------
        # 輸出分析結果
        # -------------------------------------------------

        out = {
            "代號": symbol,
            "資料日期": df.index[-1].strftime("%Y-%m-%d"),
            "現價": round(price, 2),
            "趨勢": trend,
            "位置": location,

            "5MA": round(ma5, 2) if np.isfinite(ma5) else None,
            "10MA": round(ma10, 2) if np.isfinite(ma10) else None,
            "20MA": round(ma20, 2) if np.isfinite(ma20) else None,
            "60MA": round(ma60, 2) if np.isfinite(ma60) else None,

            "KD": kd,
            "K值": round(k, 1) if np.isfinite(k) else None,
            "D值": round(d, 1) if np.isfinite(d) else None,

            "MACD": macd,
            "RSI": rsi_txt,
            "量價": volume_txt,

            "5日均量": int(vol5) if np.isfinite(vol5) else None,
            "10日均量": int(vol10) if np.isfinite(vol10) else None,

            "20日乖離率(%)": (
                round(bias20, 2)
                if np.isfinite(bias20)
                else None
            ),

            "合理價參考": (
                f"{round(ma20 * 0.95, 2)}～"
                f"{round(ma20 * 1.08, 2)}"
                "（20MA技術參考，非基本面估值）"
                if np.isfinite(ma20)
                else "資料不足"
            ),

            "精準買點參考": f"{buy_low}～{buy_high}",
            "突破買點參考": breakout,
            "停損參考": stop,
            "第一目標參考": target1,
            "第二目標參考": target2,
            "假突破觀察價": false_break,

            "近20日低點": round(recent_low, 2),
            "近20日高點": round(recent_high, 2),

            "目前訊號": signal,
        }

        out["_df"] = df

        return out, None

    except Exception as e:
        return None, (
            f"下載或分析失敗：{type(e).__name__}："
            f"{str(e)[:200]}"
        )


# =========================================================
# 個股分析顯示
# =========================================================

def show_analysis(result):

    st.subheader(
        f"📊 {result['代號']} 技術分析"
    )

    st.warning(
        f"行情資料日期：{result['資料日期']}；"
        f"收盤價：{result['現價']}。"
        "這是最近可取得的日線資料，不等於即時成交價。"
    )

    keys = [
        "現價", "趨勢", "位置",
        "5MA", "10MA", "20MA", "60MA",
        "KD", "K值", "D值", "MACD", "RSI",
        "量價", "5日均量", "10日均量",
        "20日乖離率(%)",
        "合理價參考",
        "精準買點參考",
        "突破買點參考",
        "停損參考",
        "第一目標參考",
        "第二目標參考",
        "假突破觀察價",
        "目前訊號"
    ]

    left, right = st.columns(2)

    for i, key in enumerate(keys):

        with (left if i % 2 == 0 else right):
            st.write(
                f"**{key}：** {result.get(key, '—')}"
            )

    st.markdown("### 📅 不同持有週期參考")

    st.write(
        "- **短線：**觀察5MA、10MA及成交量，"
        "跌破支撐或停損參考價時重新評估。"
    )

    st.write(
        "- **波段：**觀察20MA方向、60MA趨勢，"
        "以及突破後是否能守住前高。"
    )

    st.write(
        "- **長期：**還需要搭配營收、獲利、"
        "現金流、產業前景及估值，不能只用均線決定合理價。"
    )

    with st.expander("查看近期均線與價格"):

        df = result["_df"].tail(120).copy()

        chart = df[
            ["Close", "MA5", "MA10", "MA20", "MA60"]
        ].rename(
            columns={
                "Close": "收盤價",
                "MA5": "5MA",
                "MA10": "10MA",
                "MA20": "20MA",
                "MA60": "60MA"
            }
        )

        st.line_chart(chart)

        table = df[
            [
                "Close", "Volume",
                "MA5", "MA10", "MA20", "MA60",
                "K", "D", "DIF", "Signal", "Hist", "RSI"
            ]
        ].tail(15).round(2)

        st.dataframe(
            table,
            use_container_width=True
        )


# =========================================================
# 側邊欄
# =========================================================

st.sidebar.header("功能")

mode = st.sidebar.radio(
    "選擇功能",
    [
        "個股分析",
        "每日強勢股排行榜",
        "自選股清單"
    ]
)

st.sidebar.caption(
    "行情來源：Yahoo Finance。"
    "資料可能延遲或缺漏，並非官方即時報價。"
)


# =========================================================
# 功能一：個股分析
# =========================================================

if mode == "個股分析":

    query = st.text_input(
        "輸入台股代號或名稱",
        placeholder="例如：2330、台積電、1609、大亞、3324、雙鴻"
    )

    period = st.selectbox(
        "歷史資料期間",
        ["6mo", "1y", "2y"],
        index=1
    )

    if st.button("開始分析", type="primary") and query.strip():

        symbol = resolve_symbol(query)

        with st.spinner(
            f"正在取得 {symbol} 行情，請稍候……"
        ):

            result, err = analyze(symbol, period)

        if err:
            st.error(err)

        else:
            show_analysis(result)


# =========================================================
# 功能二：每日強勢股排行榜
# =========================================================

elif mode == "每日強勢股排行榜":

    st.write(
        "掃描內建台股股票池，依均線趨勢、MACD、"
        "KD、RSI與量能做簡化排序。"
        "**這不是完整的上市櫃全市場掃描。**"
    )

    default_pool = "\n".join([
        "台積電", "鴻海", "聯發科", "台達電",
        "廣達", "緯創", "技嘉", "微星",
        "奇鋐", "雙鴻", "台光電", "金像電",
        "健策", "大亞", "台亞", "迎廣",
        "台玻", "華邦電", "南亞科", "群創",
        "友達", "長榮", "陽明", "萬海",
        "中鋼", "國泰金", "富邦金", "中信金",
        "華航", "長榮航", "世界", "原相",
        "創惟", "群聯", "力積電"
    ])

    pool_text = st.text_area(
        "掃描名單（每行一檔）",
        value=default_pool
    )

    if st.button("掃描並排序", type="primary"):

        queries = [
            x.strip()
            for x in pool_text.splitlines()
            if x.strip()
        ]

        rows = []
        errors = []

        bar = st.progress(0)

        for i, q in enumerate(queries):

            sym = resolve_symbol(q)

            r, e = analyze(sym, "6mo")

            if r:

                score = 0

                score += {
                    "強": 3,
                    "偏強": 2,
                    "中性": 1,
                    "偏弱": 0,
                    "弱": -1
                }.get(r["趨勢"], 0)

                if "多方" in r["MACD"] or "翻紅" in r["MACD"]:
                    score += 2
                else:
                    score -= 1

                if "黃金交叉" in r["KD"]:
                    score += 1
                elif "死亡交叉" in r["KD"]:
                    score -= 1

                try:
                    rv = float(
                        r["RSI"].split("（")[0]
                    )

                    if 50 <= rv <= 70:
                        score += 1

                    elif rv > 75 or rv < 40:
                        score -= 1

                except (ValueError, AttributeError):
                    pass

                if "高於10日均量" in r["量價"]:
                    score += 1

                if "高位" in r["位置"]:
                    score -= 2

                r["評分"] = score

                rows.append({
                    k: v
                    for k, v in r.items()
                    if not k.startswith("_")
                })

            else:
                errors.append(
                    f"{q}（{sym}）：{e}"
                )

            bar.progress(
                (i + 1) / max(1, len(queries))
            )

        if rows:

            table = pd.DataFrame(rows)

            table = table.sort_values(
                ["評分", "20日乖離率(%)"],
                ascending=[False, True],
                na_position="last"
            )

            st.subheader("🏆 強勢股排序結果")

            show_cols = [
                "代號", "資料日期", "現價",
                "評分", "趨勢", "位置",
                "KD", "MACD", "RSI", "量價",
                "精準買點參考",
                "突破買點參考",
                "停損參考",
                "第一目標參考",
                "第二目標參考",
                "目前訊號"
            ]

            st.dataframe(
                table[show_cols],
                use_container_width=True
            )

            csv_data = table.to_csv(
                index=False,
                encoding="utf-8-sig"
            ).encode("utf-8-sig")

            st.download_button(
                "下載排行榜 CSV",
                csv_data,
                file_name=(
                    f"tw_stock_ranking_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv"
            )

            st.caption(
                "評分是簡化技術排序，不代表報酬機率。"
                "買點、停損與目標價均為歷史價格推估參考。"
            )

        else:
            st.warning(
                "沒有成功取得任何股票資料。"
                "請展開下方錯誤清單查看原因。"
            )

        if errors:

            with st.expander(
                f"未成功取得行情：{len(errors)} 檔"
            ):

                st.text("\n".join(errors))


# =========================================================
# 功能三：自選股清單
# =========================================================

else:

    st.write(
        "輸入自選股，每行一檔，"
        "批次分析並匯出 CSV。"
    )

    text_in = st.text_area(
        "自選股名單",
        value="2330\n台積電\n1609\n大亞\n6117\n迎廣"
    )

    period = st.selectbox(
        "資料期間",
        ["6mo", "1y", "2y"],
        index=1,
        key="watch_period"
    )

    if st.button("分析自選股", type="primary"):

        rows = []
        errors = []

        qs = list(
            dict.fromkeys(
                x.strip()
                for x in text_in.splitlines()
                if x.strip()
            )
        )

        bar = st.progress(0)

        for i, q in enumerate(qs):

            sym = resolve_symbol(q)

            r, e = analyze(sym, period)

            if r:

                rows.append({
                    k: v
                    for k, v in r.items()
                    if not k.startswith("_")
                })

            else:

                errors.append(
                    f"{q}（{sym}）：{e}"
                )

            bar.progress(
                (i + 1) / max(1, len(qs))
            )

        if rows:

            result_df = pd.DataFrame(rows)

            st.dataframe(
                result_df,
                use_container_width=True
            )

            csv_data = result_df.to_csv(
                index=False,
                encoding="utf-8-sig"
            ).encode("utf-8-sig")

            st.download_button(
                "下載自選股 CSV",
                csv_data,
                file_name=(
                    f"tw_watchlist_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                mime="text/csv"
            )

        if errors:

            with st.expander(
                f"分析失敗：{len(errors)} 檔"
            ):

                st.text("\n".join(errors))
