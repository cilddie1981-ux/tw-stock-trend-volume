# 台股趨勢指標＋量價分析

一個可部署到 GitHub + Streamlit Community Cloud 的台股技術分析小工具。輸入台股代號，即可查看均線、KD、MACD、RSI、成交量、乖離率，以及規則化的交易觀察價位。

## 功能

- 支援 Yahoo Finance 台股代碼，例如 `2330.TW`、`6488.TWO`；輸入純數字時會先嘗試 `.TW`，再嘗試 `.TWO`
- 5MA、10MA、20MA、60MA 與 K 線圖
- KD、MACD、RSI、20 日乖離率
- 5 日／10 日均量與量價提示
- 近 20 日支撐、壓力參考
- 規則化估算：回檔觀察區、突破觀察價、停損參考、目標價、假突破警戒價
- 短線、波段、長期觀察摘要

## 本機執行

建議使用 Python 3.10 或更新版本。

```bash
git clone https://github.com/YOUR-USERNAME/tw-stock-trend-volume.git
cd tw-stock-trend-volume
python -m venv .venv
```

啟用虛擬環境：

Windows PowerShell：
```powershell
.venv\\Scripts\\Activate.ps1
```

macOS / Linux：
```bash
source .venv/bin/activate
```

安裝套件並啟動：

```bash
pip install -r requirements.txt
streamlit run app.py
```

瀏覽器會開啟 Streamlit 網頁。若未自動開啟，通常可前往 `http://localhost:8501`。

## 部署到 GitHub + Streamlit Community Cloud

1. 在 GitHub 建立一個新的 repository，例如 `tw-stock-trend-volume`。
2. 將本專案中的 `app.py`、`requirements.txt`、`README.md` 上傳到 repository 根目錄。
3. 登入 Streamlit Community Cloud，連結 GitHub 帳號。
4. 選擇該 repository、branch（通常是 `main`），Main file path 設為 `app.py`。
5. 按 Deploy。部署完成後即可取得可分享的網頁網址。

## 使用方式

- 輸入股票代號，例如 `2330`、`1609`、`6117`。
- 若查不到資料，試著輸入完整代碼，例如 `2330.TW` 或 `6488.TWO`。
- 選擇歷史資料區間，再按「開始分析」。
- 頁面會顯示最新可取得的歷史行情日期；這不代表即時報價。

## 分析規則與注意事項

本專案是技術分析的教育與研究工具，不構成投資建議。

- 「低位／中段／高位」是依均線位置、20 日乖離等簡化規則分類，不等於基本面估值。
- 支撐與壓力以近 20 個交易日的最低價、最高價作參考。
- 買點、突破價、停損、目標價、假突破價均為規則化估算，不是預測，也不保證成交。
- 目標價使用風險倍數估算，請勿當成分析師目標價。
- 本版本沒有把技術價位直接稱為「合理價」。合理價應另以營收、獲利、自由現金流、負債、產業與估值倍數分析。
- 行情來源為 Yahoo Finance，資料可能延遲、缺漏或調整；交易前請核對券商或交易所資料。
- 請勿只依單一技術指標下單，並自行設定部位大小及最大可承受損失。

## 專案結構

```text
tw-stock-trend-volume/
├── app.py
├── requirements.txt
└── README.md
```

## License

MIT
