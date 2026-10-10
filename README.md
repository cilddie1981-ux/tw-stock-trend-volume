# 台股趨勢指標＋量價分析 2.2

## 功能
- 個股分析：輸入台股代號或常見中文名稱，顯示均線、KD、MACD、RSI、量價、乖離與交易參考價位。
- 每日強勢股排行榜：掃描可編輯的內建股票池，依簡化技術評分排序。
- 自選股清單：批次分析、CSV 匯出。
- 同一頁切換功能，避免查詢與結果頁分離。

## 部署到既有 GitHub repository
1. 解壓縮 ZIP。
2. 在 GitHub repository `tw-stock-trend-volume` 中，點 `Add file` → `Upload files`。
3. 上傳並覆蓋 `app.py`、`requirements.txt`、`README.md`。
4. Commit changes。
5. 若 Streamlit Community Cloud 已連結該 repository，通常會自動重新部署；若未更新，至 App 管理頁按 Reboot。

## Streamlit Community Cloud
- Main file path：`app.py`
- Python dependencies：由 `requirements.txt` 安裝。

## 重要限制
- 行情由 Yahoo Finance 提供，非官方即時報價，可能延遲、缺漏或下載失敗。
- 排行榜目前掃描的是「內建常見股票池」，不是完整上市櫃市場，也不保證每檔均可查到。
- 技術買點、停損、目標價與假突破價是以近期價格/均線推估的參考，不是保證訊號。
- 「合理價參考」目前是20日均線技術區間，不是基本面估值；長期判斷需另外分析財報、產業與估值。
- 請勿只依此工具交易；下單前核對最新報價、流動性、公司公告及自身風險承受能力。
