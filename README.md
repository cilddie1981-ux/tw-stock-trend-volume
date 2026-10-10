# 台股趨勢指標 2.0

## 功能
- 5MA、10MA、20MA、60MA、KD、MACD、RSI、量價、乖離率
- 0–100 規則化趨勢評分
- 技術價位參考：回檔觀察區、突破觀察價、停損、第一／第二目標、假突破警戒
- EPS、PE、產業、營收／獲利成長（資料來源有提供時）
- 簡化合理價參考：可取得正 EPS 時，以 EPS × 12–18 倍估算
- 多股掃描、依評分排序、下載 CSV
- K 線、均線、成交量圖表與短線／波段／長期摘要

## 更新已部署的 GitHub 專案
1. 解壓縮 ZIP。
2. 打開 GitHub 的 `tw-stock-trend-volume` Repository。
3. 對 `app.py`、`requirements.txt`、`README.md`、`.gitignore` 逐一上傳新版本並覆蓋同名檔案，或使用 Add file 上傳檔案。
4. 確認提交到 `main` 分支。
5. Streamlit Community Cloud 通常會自動重新部署；若沒有，進入 App 管理頁面檢查部署日誌或重新啟動。

## 本機執行
Python 3.10+：
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 股票代號
例如 `2330`、`2330.TW`、`6488.TWO`。純數字會先嘗試 `.TW`，再嘗試 `.TWO`。部分常見名稱已內建對照，其他股票建議使用代號。

## 重要限制
資料來自 Yahoo Finance，可能延遲、缺漏或與券商／交易所資料不同。評分是可解釋的規則化模型，不代表獲利機率。買點、停損、目標價及假突破價是技術規則估算，不保證成交。合理價僅以正 EPS × 12–18 倍提供粗略區間，未依產業調整，不能視為正式估值或投資建議。請自行核對資料並管理風險。
