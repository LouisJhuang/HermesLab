# 2308.TW 靜態股票看板 — 資料需求規格

## 1. 產品目標
提供一個可純前端部署的靜態看板，可查詢台達電 (2308.TW, TPE) 的關鍵股價與績效資料。

## 2. 資料範圍
僅需 2308.TW 單一股票，不涉及多股票管線、即時警報、通知推送。

## 3. 資料來源
- 主資料來源：Yahoo Finance Chart API
  - URL 格式：`https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range}`
  - symbol 固定：`2308.TW`
  - 無須 API Key
  - 視為非官方但可用的免費公開資料來源
  - 注意：無官方 SLA，若 Yahoo 改版或措施可能需要更換路徑。
- 不使用 `query2.finance.yahoo.com/v10/finance/quoteSummary/...`，該路徑需要 crumb，穩定度低。

## 4. 資料更新頻率與策略
| 資料類型 | 建議快取有效時間 | 說明 |
|---|---|---|
| 即時/日內價格、成交量 | 30 秒 | 前端 CDN/Site 層可做 max-age=30s |
| 1 個月歷史走勢 | 1 小時 | 資料變動較低 |
| 1 年歷史走勢 | 1 小時 | 同上 |

- 後端/前端 Fetcher 可支援 `stale-while-revalidate` 策略，降低呼叫頻率。
- 若請求失敗，建議保留上一份有效資料並顯示「資料可能落後」提示。

## 5. 看板必要資料點
1. 現時股價
2. 開盤價（當日）
3. 最高價 / 最低價（當日）
4. 前一日收盤價
5. 日漲跌額、日漲跌幅百分比
6. 當日成交量
7. 52 週最高價、52 週最低價
8. 近 1 個月歷史價格走勢圖
9. 近 1 年歷史價格走勢圖，人類可 لماحظ を

## 6. 輸出 Schema
Fetcher 模組輸出形狀參考 `output_schema.json`。
核心欄位請見 `requirements/output_schema.json`。

### 欄位意義
- `symbol`：固定 `2308.TW`
- `exchange`：固定 `TAI`
- `currency`：固定 `TWD`
- `longName`：例如 Delta Electronics, Inc.
- `updatedAt`：資料點代表的最新時間（UTC unix timestamp）
- `change`：`price - previousClose`
- `changePercent`：`change / previousClose * 100`
- `fiftyTwoWeekHigh`、`fiftyTwoWeekLow`：API 提供的 52 週區間
- `history.1mo`、`history.1y`：歷史價格欄位陣列，每個元素包含 `date/open/high/low/close/volume`

### 資料型別
- `number`：float 或 int，見各欄位定義
- `string`：UTF-8
- `integer`：`updatedAt`、`volume`
- `null`：當來源無值時使用

## 7. 顯示規則
- 幣別固定 TWD，金額取 `priceHint` 指定小數位數，通常為 2。
- 成交量以千/萬為分隔單位顯示。
- 52 週高/低與日高/低要能分別顯示，不得混用。
- 上漲/下跌以顏色區分，不改為箭頭符號亦可。

## 8. 驗收準則
1. 本規格文件存在且內容完整。
2. 已確認可使用 `query1.finance.yahoo.com` 取得 2308.TW 資料，並至少成功取得一次 `?interval=1d&range=5d`。
3. 輸出 Schema 已整理為 `output_schema.json`，Fetcher 模組可依此實作。
