const STOCK_CONFIG = {
  companyName: '台達電子工業股份有限公司 / Delta Electronics, Inc.',
  tickerDisplay: 'TPE:2308 / 2308.TW',
  yahooSymbol: '2308.TW',
  yahooChartUrl: 'https://query1.finance.yahoo.com/v8/finance/chart/2308.TW?interval=1d&range=1d',
};

const SNAPSHOT_QUOTE = {
  source: '內建快照（Yahoo Finance / TWSE 公開資料，因即時 API 無法存取時使用）',
  lastPrice: 1785,
  previousClose: 1880,
  open: 1850,
  high: 1890,
  low: 1785,
  volume: 6982902,
  currency: 'TWD',
  updatedAt: '2026-07-24 13:30 Asia/Taipei',
};

const elements = {
  status: document.querySelector('#status-message'),
  dataSource: document.querySelector('#data-source'),
  refreshButton: document.querySelector('#refresh-button'),
  lastPrice: document.querySelector('#last-price'),
  dailyChange: document.querySelector('#daily-change'),
  dailyChangePercent: document.querySelector('#daily-change-percent'),
  changeCard: document.querySelector('#change-card'),
  openPrice: document.querySelector('#open-price'),
  highPrice: document.querySelector('#high-price'),
  lowPrice: document.querySelector('#low-price'),
  volume: document.querySelector('#volume'),
  updatedAt: document.querySelector('#updated-at'),
};

function formatPrice(value) {
  if (!Number.isFinite(value)) return '--';
  return new Intl.NumberFormat('zh-TW', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatVolume(value) {
  if (!Number.isFinite(value)) return '--';
  return new Intl.NumberFormat('zh-TW').format(value);
}

function formatSigned(value) {
  if (!Number.isFinite(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${formatPrice(value)}`;
}

function formatTimestamp(unixSeconds) {
  if (!Number.isFinite(unixSeconds)) return '--';
  return new Intl.DateTimeFormat('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(unixSeconds * 1000));
}

function normalizeYahooQuote(payload) {
  const result = payload?.chart?.result?.[0];
  if (!result) {
    throw new Error('Yahoo Finance 回應缺少 chart.result 資料');
  }

  const meta = result.meta ?? {};
  const quote = result.indicators?.quote?.[0] ?? {};
  const latestIndex = Math.max((result.timestamp?.length ?? 1) - 1, 0);

  const lastPrice = Number(meta.regularMarketPrice ?? quote.close?.[latestIndex]);
  const previousClose = Number(meta.chartPreviousClose ?? meta.previousClose);

  return {
    source: 'Yahoo Finance 公開圖表 API（瀏覽器端即時擷取）',
    lastPrice,
    previousClose,
    open: Number(quote.open?.[latestIndex] ?? meta.regularMarketOpen),
    high: Number(meta.regularMarketDayHigh ?? quote.high?.[latestIndex]),
    low: Number(meta.regularMarketDayLow ?? quote.low?.[latestIndex]),
    volume: Number(meta.regularMarketVolume ?? quote.volume?.[latestIndex]),
    currency: meta.currency ?? 'TWD',
    updatedAt: formatTimestamp(Number(meta.regularMarketTime ?? result.timestamp?.[latestIndex])),
  };
}

function renderQuote(quote, { isFallback = false } = {}) {
  const change = quote.lastPrice - quote.previousClose;
  const changePercent = quote.previousClose ? (change / quote.previousClose) * 100 : NaN;

  elements.lastPrice.textContent = formatPrice(quote.lastPrice);
  elements.dailyChange.textContent = `${formatSigned(change)} ${quote.currency ?? 'TWD'}`;
  elements.dailyChangePercent.textContent = Number.isFinite(changePercent)
    ? `${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%`
    : '--';
  elements.openPrice.textContent = formatPrice(quote.open);
  elements.highPrice.textContent = formatPrice(quote.high);
  elements.lowPrice.textContent = formatPrice(quote.low);
  elements.volume.textContent = formatVolume(quote.volume);
  elements.updatedAt.textContent = quote.updatedAt || '--';
  elements.dataSource.textContent = quote.source;

  elements.changeCard.classList.remove('is-up', 'is-down', 'is-flat');
  elements.changeCard.classList.add(change > 0 ? 'is-up' : change < 0 ? 'is-down' : 'is-flat');

  elements.status.textContent = isFallback
    ? '即時資料暫時無法取得，已顯示清楚標示的近期快照。'
    : '已成功載入最新股票資料。';
  elements.status.classList.toggle('is-warning', isFallback);
}

async function fetchLiveQuote() {
  const response = await fetch(STOCK_CONFIG.yahooChartUrl, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`Yahoo Finance API 回應 HTTP ${response.status}`);
  }

  return normalizeYahooQuote(await response.json());
}

async function loadQuote() {
  elements.refreshButton.disabled = true;
  elements.status.textContent = '正在取得 TPE:2308 股票資料…';
  elements.status.classList.remove('is-warning');

  try {
    const liveQuote = await fetchLiveQuote();
    renderQuote(liveQuote);
  } catch (error) {
    console.warn('股票即時資料載入失敗，改用內建快照。', error);
    renderQuote(SNAPSHOT_QUOTE, { isFallback: true });
  } finally {
    elements.refreshButton.disabled = false;
  }
}

elements.refreshButton.addEventListener('click', loadQuote);
loadQuote();
