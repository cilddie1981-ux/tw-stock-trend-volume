# 台股趨勢指標 2.1

## 這版修正
1. 個股查詢框、結果、圖表、交易價位整合在同一頁，不再需要分開找查詢頁面。
2. 可輸入內建常見中文名稱，例如台積電、鴻海、大亞、台亞、迎廣、台玻；其他中文名稱會嘗試 Yahoo Finance 搜尋。
3. 可輸入股票代號（例如 2330）或完整 Yahoo Finance 代碼（例如 6488.TWO）。
4. 多股掃描也支援常見中文名稱。

## 更新到 GitHub
將 ZIP 解壓縮，將新版 `app.py`、`requirements.txt`、`README.md`、`.gitignore` 上傳並覆蓋原 Repository 中同名檔案，提交到 `main` 分支。Streamlit Community Cloud 通常會自動重新部署。

## 本機執行
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 限制
中文名稱搜尋依賴 Yahoo Finance 的搜尋結果，不能保證所有公司名稱均可辨識。若失敗，請使用股票代號或 `.TW`／`.TWO` 代碼。行情可能延遲或缺漏。技術價位及簡化估值只作研究參考，不構成投資建議。
