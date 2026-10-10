import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="台股趨勢指標 2.0", page_icon="📈", layout="wide")
st.title("📈 台股趨勢指標 2.0")
st.caption("趨勢 × 量價 × 動能 × 基本面估值 × 多股掃描｜研究輔助工具，不構成投資建議。")

ALIASES = {"台積電":"2330.TW","鴻海":"2317.TW","聯發科":"2454.TW","台達電":"2308.TW",
"大亞":"1609.TW","台亞":"2340.TW","迎廣":"6117.TW","台玻":"1802.TW","聯穎":"3550.TW",
"廣達":"2382.TW","長榮":"2603.TW","陽明":"2609.TW","華航":"2610.TW","緯創":"3231.TW"}

with st.sidebar:
    st.header("分析設定")
    ticker_input = st.text_input("個股代號／名稱", "2330")
    period = st.selectbox("歷史行情區間", ["6mo","1y","2y","5y"], index=1)
    analyze_button = st.button("分析個股", type="primary", use_container_width=True)
    st.divider()
    st.subheader("多股掃描")
    scan_input = st.text_area("代號／名稱（逗號或換行分隔）",
                              "2330, 2317, 2454, 1609, 2340, 6117, 1802", height=110)
    scan_button = st.button("掃描清單", use_container_width=True)

def resolve(raw):
    raw = str(raw).strip()
    if raw in ALIASES: return ALIASES[raw]
    if raw.upper().endswith((".TW", ".TWO")): return raw.upper()
    if raw.isdigit():
        for suffix in (".TW", ".TWO"):
            candidate = raw + suffix
            try:
                if not yf.Ticker(candidate).history(period="1mo").empty: return candidate
            except Exception: pass
        raise ValueError(f"找不到股票代號 {raw}，請確認代號或輸入完整代碼。")
    raise ValueError("無法辨識名稱，請改輸入股票代號或完整 Yahoo Finance 代碼。")

@st.cache_data(ttl=900, show_spinner=False)
def get_history(ticker, period):
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df is not None and not df.empty:
        df.columns = [str(c).title() for c in df.columns]
    return df if df is not None else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_info(ticker):
    try: return yf.Ticker(ticker).info or {}
    except Exception: return {}

def indicators(df):
    d = df.copy()
    for n in (5,10,20,60): d[f"MA{n}"] = d.Close.rolling(n).mean()
    lo, hi = d.Low.rolling(9).min(), d.High.rolling(9).max()
    rsv = (d.Close-lo)/(hi-lo).replace(0,np.nan)*100
    d["K"] = rsv.ewm(alpha=1/3,adjust=False).mean()
    d["D"] = d.K.ewm(alpha=1/3,adjust=False).mean()
    e12, e26 = d.Close.ewm(span=12,adjust=False).mean(), d.Close.ewm(span=26,adjust=False).mean()
    d["DIF"] = e12-e26
    d["MACD"] = d.DIF.ewm(span=9,adjust=False).mean()
    d["MACD_Hist"] = d.DIF-d.MACD
    delta = d.Close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    d["RSI"] = 100-100/(1+gain/loss.replace(0,np.nan))
    d["VOL_MA5"] = d.Volume.rolling(5).mean()
    d["VOL_MA10"] = d.Volume.rolling(10).mean()
    d["BIAS20"] = (d.Close/d.MA20-1)*100
    return d

def assess(df, info):
    x, p = df.iloc[-1], df.iloc[-2]
    price = float(x.Close)
    ma5,ma10,ma20,ma60 = [x.get(f"MA{n}",np.nan) for n in (5,10,20,60)]
    k, kd = x.get("K",np.nan), x.get("D",np.nan)
    hist, phist = x.get("MACD_Hist",np.nan), p.get("MACD_Hist",np.nan)
    rsi, bias = x.get("RSI",np.nan), x.get("BIAS20",np.nan)
    vol,v5,v10 = x.get("Volume",np.nan),x.get("VOL_MA5",np.nan),x.get("VOL_MA10",np.nan)
    # Explainable rule-based score, not a probability of profit.
    score = 0
    score += 7 if pd.notna(ma5) and pd.notna(ma10) and ma5>ma10 else 0
    score += 8 if pd.notna(ma10) and pd.notna(ma20) and ma10>ma20 else 0
    score += 8 if pd.notna(ma20) and pd.notna(ma60) and ma20>ma60 else 0
    score += 7 if pd.notna(ma20) and price>ma20 else 0
    score += 8 if pd.notna(k) and pd.notna(kd) and k>kd else 0
    score += 3 if pd.notna(k) and 20<=k<=80 else 0
    score += 9 if pd.notna(hist) and hist>0 else 0
    score += 4 if pd.notna(hist) and pd.notna(phist) and hist>phist else 0
    score += 6 if pd.notna(rsi) and 50<=rsi<=70 else 0
    score += 10 if pd.notna(vol) and pd.notna(v10) and vol>=v10*1.2 and price>float(p.Close) else 0
    score += 5 if pd.notna(v5) and pd.notna(v10) and v5>=v10 else 0
    score += 5 if pd.notna(bias) and -3<=bias<=7 else 0
    score += 8 if pd.notna(bias) and -5<=bias<=8 else 0
    score += 6 if pd.notna(ma20) and price>=ma20 else 0
    score += 3 if pd.notna(rsi) and rsi<75 else 0
    score += 3 if pd.notna(vol) and pd.notna(v10) and vol<v10*2.5 else 0
    score = int(min(100,score))
    if pd.notna(ma20) and pd.notna(ma60) and price>ma20>ma60: trend="強"
    elif pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20) and ma5>ma10>ma20: trend="偏強"
    elif pd.notna(ma20) and pd.notna(ma60) and price<ma20 and price<ma60: trend="弱"
    elif pd.notna(ma20) and price<ma20: trend="偏弱"
    else: trend="中性"
    if pd.notna(bias) and bias>=10: position="高位／乖離偏大"
    elif pd.notna(ma20) and pd.notna(ma60) and price<ma20 and price<ma60: position="低位／弱勢區，待確認止跌"
    elif pd.notna(ma20) and pd.notna(ma60) and price>ma20 and price>ma60: position="中段偏強"
    else: position="中段整理"
    if pd.notna(k) and pd.notna(kd) and pd.notna(p.get("K")) and pd.notna(p.get("D")):
        if p.K<=p.D and k>kd: kd_text="黃金交叉"
        elif p.K>=p.D and k<kd: kd_text="死亡交叉"
        elif k>=80 and kd>=80: kd_text="高檔鈍化"
        elif k<=20 and kd<=20: kd_text="低檔區"
        else: kd_text="中性"
    else: kd_text="資料不足"
    macd_text = "多方動能" if pd.notna(hist) and hist>0 else "空方動能"
    if pd.notna(hist) and pd.notna(phist) and hist>0 and phist<=0: macd_text="柱狀體翻紅"
    if pd.notna(hist) and pd.notna(phist) and hist<0 and phist>=0: macd_text="柱狀體翻綠"
    rsi_text = "強勢" if pd.notna(rsi) and rsi>=60 else ("偏弱" if pd.notna(rsi) and rsi<40 else "中性")
    if pd.notna(rsi) and rsi>=75: rsi_text += "／過熱"
    if pd.notna(rsi) and rsi<=25: rsi_text += "／超賣"
    if pd.notna(vol) and pd.notna(v10) and vol>=v10*1.8: volume_text="爆量警戒（需搭配K線判斷）"
    elif pd.notna(vol) and pd.notna(v10) and vol>=v10*1.2 and price>float(p.Close): volume_text="價漲量增"
    elif pd.notna(v5) and pd.notna(v10) and v5<v10: volume_text="量縮整理"
    else: volume_text="量能中性"
    recent=df.tail(20)
    support=float(recent.Low.min()); resistance=float(recent.High.max())
    ma20ref=float(ma20) if pd.notna(ma20) else price
    buy_low=max(support,min(ma20ref,price)*.985)
    buy_high=max(buy_low,min(ma20ref,price)*1.005)
    breakout=resistance*1.005
    stop=min(support*.98,buy_low*.95)
    risk=max(price-stop,price*.03)
    false_break=resistance*.97
    t1,t2=price+risk,price+2*risk
    if score>=75 and trend in ("強","偏強") and "爆量" not in volume_text and (pd.isna(bias) or bias<10):
        signal="🟢 偏多觀察：等回檔或收盤確認突破"
    elif score<45 or trend=="弱": signal="🔴 偏弱警戒：先控風險"
    else: signal="🟡 等待：訊號尚未充分一致"
    eps=info.get("forwardEps") if isinstance(info.get("forwardEps"),(int,float)) and info.get("forwardEps")>0 else info.get("trailingEps")
    fair_low,fair_high=np.nan,np.nan
    valuation="基本面資料不足，暫不估價"
    if isinstance(eps,(int,float)) and np.isfinite(eps) and eps>0:
        fair_low,fair_high=eps*12,eps*18
        valuation="以正 EPS × 12–18 倍估算的粗略區間，未依產業調整"
    elif isinstance(info.get("trailingEps"),(int,float)) and info.get("trailingEps")<=0:
        valuation="EPS 非正值，不適用簡化本益比估值"
    return dict(price=price,score=score,trend=trend,position=position,kd=kd_text,macd=macd_text,
                rsi=rsi,rsi_text=rsi_text,volume=volume_text,bias=bias,support=support,resistance=resistance,
                buy_low=buy_low,buy_high=buy_high,breakout=breakout,stop=stop,target1=t1,target2=t2,
                false_break=false_break,signal=signal,ma5=ma5,ma10=ma10,ma20=ma20,ma60=ma60,
                vol=v10,v5=v5,v10=v10,eps=eps,pe=info.get("trailingPE"),sector=info.get("sector","資料不足"),
                revenue_growth=info.get("revenueGrowth"),earnings_growth=info.get("earningsGrowth"),
                fair_low=fair_low,fair_high=fair_high,valuation=valuation)

def run_one(raw, period):
    ticker=resolve(raw); hist=get_history(ticker,period)
    if hist.empty or not {"Close","High","Low","Volume"}.issubset(hist.columns):
        raise ValueError("沒有取得有效行情")
    df=indicators(hist).dropna(subset=["Close"])
    if len(df)<25: raise ValueError("歷史資料不足（至少約25個交易日）")
    info=get_info(ticker)
    return ticker,df,info,assess(df,info)

def f(v,d=2):
    try: return "資料不足" if pd.isna(v) or not np.isfinite(float(v)) else f"{float(v):,.{d}f}"
    except Exception: return "資料不足"

def date_text(v):
    t=pd.Timestamp(v)
    if t.tzinfo is not None: t=t.tz_convert("Asia/Taipei").tz_localize(None)
    return t.strftime("%Y-%m-%d")

if scan_button:
    stocks=list(dict.fromkeys(x.strip() for x in scan_input.replace("\n",",").split(",") if x.strip()))
    rows=[]; errors=[]
    if not stocks: st.warning("請先輸入股票代號。")
    else:
        progress=st.progress(0)
        for i,s in enumerate(stocks):
            try:
                ticker,df,info,r=run_one(s,period)
                rows.append({"輸入":s,"代碼":ticker,"行情日期":date_text(df.index[-1]),"收盤價":round(r["price"],2),
                "評分":r["score"],"趨勢":r["trend"],"位置":r["position"],"量價":r["volume"],
                "RSI":round(r["rsi"],1) if pd.notna(r["rsi"]) else np.nan,
                "買點下緣":round(r["buy_low"],2),"買點上緣":round(r["buy_high"],2),
                "突破觀察":round(r["breakout"],2),"停損參考":round(r["stop"],2),"訊號":r["signal"]})
            except Exception as e: errors.append(f"{s}：{e}")
            progress.progress((i+1)/len(stocks))
        progress.empty()
        if rows:
            scan_df=pd.DataFrame(rows).sort_values("評分",ascending=False)
            st.subheader("🔎 多股掃描結果（依評分排序）")
            st.dataframe(scan_df,use_container_width=True,hide_index=True)
            st.download_button("下載掃描結果 CSV",scan_df.to_csv(index=False,encoding="utf-8-sig"),"tw_stock_scan.csv","text/csv")
        if errors:
            with st.expander(f"未完成的股票（{len(errors)}檔）"):
                for e in errors: st.write("• "+e)

if analyze_button or "one" not in st.session_state:
    try:
        with st.spinner("正在取得行情並計算指標…"):
            t,d,i,r=run_one(ticker_input,period)
            st.session_state["one"]=(t,d,i,r)
    except Exception as e:
        if "one" not in st.session_state: st.error(f"分析失敗：{e}"); st.stop()
        st.error(f"本次查詢失敗，保留上次結果：{e}")

if "one" in st.session_state:
    ticker,df,info,r=st.session_state["one"]
    st.info(f"股票代碼：**{ticker}** ｜ 行情最後日期：**{date_text(df.index[-1])}** ｜ Yahoo Finance 行情可能延遲")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("最新收盤價",f"{r['price']:.2f}")
    c2.metric("趨勢評分",f"{r['score']} / 100")
    c3.metric("趨勢",r["trend"])
    c4.metric("股價位置",r["position"])
    if r["signal"].startswith("🟢"): st.success(r["signal"])
    elif r["signal"].startswith("🟡"): st.warning(r["signal"])
    else: st.error(r["signal"])
    tab1,tab2,tab3,tab4=st.tabs(["技術指標與價位","合理價／基本面","圖表","短線／波段／長期"])
    with tab1:
        rows=[("現價",f(r["price"])),("綜合評分",f"{r['score']} / 100"),("趨勢",r["trend"]),("位置",r["position"]),
        ("5/10/20/60MA"," / ".join(f(r[k]) for k in ("ma5","ma10","ma20","ma60"))),
        ("KD",f"{r['kd']}（K={f(df.iloc[-1].get('K'))}，D={f(df.iloc[-1].get('D'))}）"),
        ("MACD",r["macd"]),("RSI",f"{r['rsi_text']}（{f(r['rsi'])}）"),("量價",r["volume"]),
        ("5日／10日均量",f"{f(r['v5'],0)} / {f(r['v10'],0)}"),("20日乖離率",f"{f(r['bias'])}%"),
        ("近20日支撐",f(r["support"])),("近20日壓力",f(r["resistance"])),
        ("精準買點觀察區",f"{f(r['buy_low'])}～{f(r['buy_high'])}"),("突破觀察價",f(r["breakout"])),
        ("停損參考",f(r["stop"])),("第一目標（風險倍數估算）",f(r["target1"])),
        ("第二目標（風險倍數估算）",f(r["target2"])),("假突破警戒參考",f(r["false_break"])),("目前訊號",r["signal"])]
        st.dataframe(pd.DataFrame(rows,columns=["項目","訊號／參考值"]),use_container_width=True,hide_index=True)
        st.caption("所有技術價位均為規則化估算參考，不保證成交或獲利。")
    with tab2:
        a,b,c=st.columns(3); a.metric("EPS（優先預估值）",f(r["eps"])); b.metric("本益比 PE",f(r["pe"])); c.metric("產業",str(r["sector"]))
        rg=r["revenue_growth"]; eg=r["earnings_growth"]
        st.write("營收成長率："+(f"{rg*100:.1f}%" if isinstance(rg,(int,float)) and np.isfinite(rg) else "資料不足"))
        st.write("獲利成長率："+(f"{eg*100:.1f}%" if isinstance(eg,(int,float)) and np.isfinite(eg) else "資料不足"))
        if np.isfinite(r["fair_low"]) and np.isfinite(r["fair_high"]):
            st.subheader(f"簡化合理價參考：{r['fair_low']:.2f}～{r['fair_high']:.2f}")
        else: st.subheader("簡化合理價：目前資料不足或不適用")
        st.info(r["valuation"])
        st.caption("估值方法為正 EPS × 12–18 倍的粗略區間，未依產業與公司成長差異調整，不能視為正式合理價或投資建議。")
    with tab3:
        fig=go.Figure()
        fig.add_trace(go.Candlestick(x=df.index,open=df.Open,high=df.High,low=df.Low,close=df.Close,name="K線"))
        for n in (5,10,20,60): fig.add_trace(go.Scatter(x=df.index,y=df[f"MA{n}"],mode="lines",name=f"{n}MA"))
        fig.update_layout(height=500,xaxis_rangeslider_visible=False,legend_orientation="h",legend_y=1.02)
        st.plotly_chart(fig,use_container_width=True)
        vf=go.Figure()
        vf.add_trace(go.Bar(x=df.index,y=df.Volume,name="成交量"))
        vf.add_trace(go.Scatter(x=df.index,y=df.VOL_MA5,name="5日均量"))
        vf.add_trace(go.Scatter(x=df.index,y=df.VOL_MA10,name="10日均量"))
        vf.update_layout(height=280,legend_orientation="h")
        st.plotly_chart(vf,use_container_width=True)
    with tab4:
        a,b,c=st.columns(3)
        with a:
            st.markdown("### 短線"); st.write(f"回檔觀察區：{r['buy_low']:.2f}～{r['buy_high']:.2f}")
            st.write(f"停損參考：{r['stop']:.2f}"); st.write("跌破支撐且量增時，重新評估風險。")
        with b:
            st.markdown("### 波段"); st.write(f"突破觀察：收盤站上 {r['breakout']:.2f} 且量能配合")
            st.write(f"近20日壓力：{r['resistance']:.2f}"); st.write("留意突破後回測是否守住。")
        with c:
            st.markdown("### 長期"); st.write(f"60MA：{f(r['ma60'])}")
            st.write("長期仍須核對財報、現金流、負債與產業風險。")
    with st.expander("最近30個交易日資料"):
        st.dataframe(df.tail(30).sort_index(ascending=False),use_container_width=True)

st.divider()
st.caption("資料來源為 Yahoo Finance，可能延遲、缺漏或不準確。評分不是獲利機率；技術價位與簡化估值均為參考，不應單獨作為下單依據。")
