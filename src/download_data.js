/**
 * Historical Data Downloader for Trading Lens (2025 - Present)
 * 
 * Instruments:
 *  - usatechidxusd -> DAT_ASCII_NSXUSD_M1_<YEAR>.csv (Nasdaq 100 / NQ)
 *  - usa500idxusd  -> DAT_ASCII_SPXUSD_M1_<YEAR>.csv (S&P 500 / ES)
 * 
 * Timezone: Converted from UTC to America/New_York (US Eastern Time)
 * Format: YYYYMMDD HHMMSS;open;high;low;close;volume
 */

const { getHistoricalRates } = require('dukascopy-node');
const fs = require('fs');
const path = require('path');

const TARGET_DATA_DIR = path.resolve(__dirname, '..', 'data');

const INSTRUMENTS = [
  {
    id: 'usatechidxusd',
    symbolPrefix: 'DAT_ASCII_NSXUSD_M1',
    name: 'Nasdaq-100 (NSXUSD / NQ)'
  },
  {
    id: 'usa500idxusd',
    symbolPrefix: 'DAT_ASCII_SPXUSD_M1',
    name: 'S&P 500 (SPXUSD / ES)'
  }
];

const START_YEAR = 2025;
const END_YEAR = 2026;

// Format UTC timestamp (ms) to US Eastern Time (America/New_York) "YYYYMMDD HHMMSS"
const nyFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
});

function toNyTimeString(timestampMs) {
  const d = new Date(timestampMs);
  const parts = nyFormatter.formatToParts(d);
  const map = {};
  for (const p of parts) {
    map[p.type] = p.value;
  }
  let hour = map.hour === '24' ? '00' : map.hour;
  return `${map.year}${map.month}${map.day} ${hour}${map.minute}${map.second}`;
}

function candleToAsciiRow(c) {
  const nyTime = toNyTimeString(c.timestamp);
  const o = Number(c.open).toFixed(6);
  const h = Number(c.high).toFixed(6);
  const l = Number(c.low).toFixed(6);
  const cl = Number(c.close).toFixed(6);
  return `${nyTime};${o};${h};${l};${cl};0\n`;
}

// Download month by month to ensure complete data and handle large request payloads
async function downloadMonth(instrumentId, year, month) {
  const fromDate = new Date(Date.UTC(year, month, 1, 0, 0, 0));
  const toDate = new Date(Date.UTC(year, month + 1, 0, 23, 59, 59));
  const now = new Date();

  if (fromDate > now) {
    return [];
  }
  const effectiveTo = toDate > now ? now : toDate;

  let retries = 3;
  while (retries > 0) {
    try {
      const data = await getHistoricalRates({
        instrument: instrumentId,
        dates: {
          from: fromDate,
          to: effectiveTo
        },
        timeframe: 'm1',
        format: 'json',
        priceType: 'bid',
        volumes: false,
        batchSize: 10,
        pauseBetweenBatchesMs: 50
      });
      return data || [];
    } catch (err) {
      retries--;
      console.warn(`    ⚠️ Retry ${3 - retries} for ${year}-${month + 1}: ${err.message}`);
      if (retries === 0) {
        console.error(`    ❌ Failed to download ${year}-${month + 1}:`, err);
        return [];
      }
      await new Promise(r => setTimeout(r, 1000));
    }
  }
  return [];
}

async function processInstrumentYear(inst, year) {
  console.log(`\n======================================================`);
  console.log(`📥 Downloading ${inst.name} for Year ${year}...`);
  console.log(`======================================================`);

  const now = new Date();
  const currentYear = now.getUTCFullYear();
  const maxMonth = year === currentYear ? now.getUTCMonth() : 11;

  let allCandles = [];
  const startTime = Date.now();

  for (let m = 0; m <= maxMonth; m++) {
    const monthName = new Date(Date.UTC(year, m, 1)).toLocaleString('en-US', { month: 'short' });
    process.stdout.write(`  ⏳ Month ${m + 1}/12 (${monthName} ${year})... `);
    const mData = await downloadMonth(inst.id, year, m);
    console.log(`${mData.length.toLocaleString()} candles`);
    if (mData.length > 0) {
      allCandles.push(...mData);
    }
  }

  if (allCandles.length === 0) {
    console.warn(`⚠️ No data found for ${inst.name} in ${year}`);
    return;
  }

  // Sort by timestamp and remove duplicates
  allCandles.sort((a, b) => a.timestamp - b.timestamp);
  const uniqueCandles = [];
  const seenTimestamps = new Set();
  for (const c of allCandles) {
    if (!seenTimestamps.has(c.timestamp)) {
      seenTimestamps.add(c.timestamp);
      uniqueCandles.push(c);
    }
  }

  console.log(`  ✓ Total unique M1 candles: ${uniqueCandles.length.toLocaleString()}`);

  const targetFileName = `${inst.symbolPrefix}_${year}.csv`;
  const targetFilePath = path.join(TARGET_DATA_DIR, targetFileName);

  console.log(`  💾 Writing to ${targetFilePath}...`);
  const writeStream = fs.createWriteStream(targetFilePath, { encoding: 'utf-8' });

  for (let i = 0; i < uniqueCandles.length; i++) {
    writeStream.write(candleToAsciiRow(uniqueCandles[i]));
  }

  await new Promise(resolve => writeStream.end(resolve));
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
  const fileSizeMb = (fs.statSync(targetFilePath).size / (1024 * 1024)).toFixed(2);
  console.log(`  🎉 Finished ${targetFileName} (${fileSizeMb} MB) in ${elapsed}s`);
}

async function run() {
  console.log(`🚀 STARTING HISTORICAL DATA DOWNLOAD FOR 2025–${END_YEAR}`);
  console.log(`Target Directory: ${TARGET_DATA_DIR}`);

  if (!fs.existsSync(TARGET_DATA_DIR)) {
    fs.mkdirSync(TARGET_DATA_DIR, { recursive: true });
  }

  for (const inst of INSTRUMENTS) {
    for (let year = START_YEAR; year <= END_YEAR; year++) {
      await processInstrumentYear(inst, year);
    }
  }

  console.log(`\n🎉 ALL 2025–${END_YEAR} DATA DOWNLOADS COMPLETED SUCCESSFULLY!`);
}

run().catch(console.error);
