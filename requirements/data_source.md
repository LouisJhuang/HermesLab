# 資料來源確認紀錄

日期：2026-07-25
人員：agent-pm

## 實測結果
已成功透過 `query1.finance.yahoo.com/v8/finance/chart/2308.TW?interval=1d&range=5d` 取得乾淨 JSON，回傳欄位包含：
- `meta.currency`：`TWD`
- `meta.regularMarketPrice`、`regularMarketVolume`
- `meta.fiftyTwoWeekHigh`、`meta.fiftyTwoWeekLow`
- `indicators.quote`：`open`、`high`、`low`、`close`、`volume`
- `timestamp`：歷史日期索引

`query2.finance.yahoo.com/v10/finance/quoteSummary/...` 回傳 `{"code":"Unauthorized","description":"Invalid Crumb"}`，實際不可用。

## 結論
以 `query1.finance.yahoo.com` 做為唯一來源，避免依賴 crumb-based 路徑。單一 symbol、低頻請求（1 symbol，30 秒等級）下，可直接作為前端 Fetcher 資料來源，風險可接受。