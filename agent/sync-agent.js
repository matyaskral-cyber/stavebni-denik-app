#!/usr/bin/env node
/**
 * Stavební deník — On-premise Sync Agent
 *
 * Stáhne zálohu z API a uloží lokálně.
 * Podporuje delta sync pomocí ?since= parametru.
 *
 * Použití:
 *   1. Zkopírujte config.example.json → config.json a vyplňte
 *   2. node sync-agent.js
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// --- Load config ---
const CONFIG_PATH = path.join(__dirname, 'config.json');
const LAST_SYNC_PATH = path.join(__dirname, 'last_sync.json');

if (!fs.existsSync(CONFIG_PATH)) {
  console.error('CHYBA: config.json nenalezen. Zkopírujte config.example.json → config.json');
  process.exit(1);
}

const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));

if (!config.api_url || !config.api_key || !config.local_path) {
  console.error('CHYBA: config.json musí obsahovat api_url, api_key a local_path');
  process.exit(1);
}

// --- Read last sync timestamp ---
function getLastSync() {
  if (fs.existsSync(LAST_SYNC_PATH)) {
    try {
      const data = JSON.parse(fs.readFileSync(LAST_SYNC_PATH, 'utf-8'));
      return data.last_sync || null;
    } catch {
      return null;
    }
  }
  return null;
}

function saveLastSync(timestamp) {
  fs.writeFileSync(LAST_SYNC_PATH, JSON.stringify({ last_sync: timestamp }, null, 2));
}

// --- Ensure directory exists ---
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

// --- Fetch backup from API ---
function fetchBackup(url, apiKey) {
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(url);
    const client = parsedUrl.protocol === 'https:' ? https : http;

    const options = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port,
      path: parsedUrl.pathname + parsedUrl.search,
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
    };

    const req = client.request(options, (res) => {
      if (res.statusCode === 403) {
        reject(new Error('403 Forbidden — neplatný API klíč'));
        return;
      }
      if (res.statusCode === 401) {
        reject(new Error('401 Unauthorized — chybí autorizace'));
        return;
      }
      if (res.statusCode !== 200) {
        reject(new Error(`HTTP ${res.statusCode}`));
        return;
      }

      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => resolve(Buffer.concat(chunks)));
    });

    req.on('error', reject);
    req.setTimeout(120000, () => {
      req.destroy();
      reject(new Error('Timeout — server neodpovídá'));
    });
    req.end();
  });
}

// --- Main ---
async function main() {
  const now = new Date();
  const year = now.getFullYear().toString();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, 19);

  console.log(`[${now.toISOString()}] Stavební deník Sync Agent`);
  console.log(`  API: ${config.api_url}`);

  // Build URL with optional since parameter
  let url = config.api_url;
  const lastSync = getLastSync();
  if (lastSync) {
    const separator = url.includes('?') ? '&' : '?';
    url += `${separator}since=${encodeURIComponent(lastSync)}`;
    console.log(`  Delta sync od: ${lastSync}`);
  } else {
    console.log('  Full sync (první spuštění)');
  }

  try {
    console.log('  Stahuji zálohu...');
    const data = await fetchBackup(url, config.api_key);

    // Save to local_path/YYYY/MM/
    const slug = config.firma_slug || 'backup';
    const destDir = path.join(config.local_path, year, month);
    ensureDir(destDir);

    const filename = `${slug}_${timestamp}.zip`;
    const destPath = path.join(destDir, filename);
    fs.writeFileSync(destPath, data);

    const sizeKB = (data.length / 1024).toFixed(1);
    console.log(`  Uloženo: ${destPath} (${sizeKB} KB)`);

    // Update last_sync timestamp
    saveLastSync(now.toISOString());
    console.log('  Sync dokončen.');
  } catch (err) {
    console.error(`  CHYBA: ${err.message}`);
    process.exit(1);
  }
}

main();
