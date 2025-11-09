const { chromium } = require('playwright');
const axios = require('axios');
const fs = require('fs');

// page.goto() with retry
async function safeGoto(page, url, options = {}, retries = 3, delayMs = 5000) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`[GOTO] ${url} (attempt ${attempt}/${retries})`);
      await page.goto(url, options);
      console.log(`[GOTO] success`);
      return;
    } catch (err) {
      console.error(`[GOTO error] ${err.message}`);
      if (attempt === retries) throw err;
      console.log(`[Retry after] ${delayMs / 1000}s`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
}

async function runCrawler() {
  console.log(`[Start] Playwright`);

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();

  await safeGoto(page, 'https://ransomwatch.telemetry.ltd/#/recentposts', {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  await page.waitForTimeout(5000);
  const today = new Date().toISOString().slice(0, 10);

  const groups = await page.evaluate((today) => {
    const rows = Array.from(document.querySelectorAll('tbody tr'));
    const matchingGroups = [];

    for (const row of rows) {
      const dateCell = row.querySelector('td');
      const groupCell = row.querySelectorAll('td')[2];

      if (dateCell && dateCell.textContent.trim() === today && groupCell) {
        matchingGroups.push(groupCell.textContent.trim());
      }
    }

    return [...new Set(matchingGroups)];
  }, today);

  await browser.close();

  if (groups.length === 0) {
    console.log(`[${today}] No groups found.`);
    return;
  }

  console.log(`Groups listed on ${today}:`, groups);

  const outputPath = '/app/downloads/onion_list.json';
  let existingData = [];

  if (fs.existsSync(outputPath)) {
    try {
      existingData = JSON.parse(fs.readFileSync(outputPath, 'utf-8'));
    } catch (err) {
      console.error('[ERROR] Failed to read existing JSON:', err.message);
    }
  }

  // Build current map: group -> fqdn
  const existingMap = {};
  for (const item of existingData) {
    existingMap[item.group] = item.fqdn;
  }

  // Update entries
  for (const group of groups) {
    console.log(`\n--- ${group} ---`);
    const fqdn = await getLatestOnionFQDN(group);

    if (!fqdn) {
      console.log(`${group}: no usable .onion address.`);
      continue;
    }

    const previousFqdn = existingMap[group];
    if (previousFqdn && previousFqdn !== fqdn) {
      console.log(`${group} FQDN changed: ${previousFqdn} -> ${fqdn}`);
      const index = existingData.findIndex(item => item.group === group);
      if (index !== -1) {
        existingData[index].fqdn = fqdn;
      }
    } else if (!previousFqdn) {
      console.log(`${group} added`);
      existingData.push({ group, fqdn });
    } else {
      console.log(`${group} FQDN unchanged`);
    }
  }

  fs.writeFileSync(outputPath, JSON.stringify(existingData, null, 2));
  console.log(`Saved: ${outputPath}`);
}

async function getLatestOnionFQDN(groupName) {
  try {
    const res = await axios.get('https://ransomwhat.telemetry.ltd/groups');
    const parsed = res.data;
    const target = parsed.find(g => g.name === groupName);
    if (!target || !target.locations) return null;

    const sorted = target.locations
      .filter(loc => loc.fqdn.endsWith('.onion') && loc.enabled)
      .sort((a, b) => new Date(b.updated) - new Date(a.updated));

    return sorted[0]?.fqdn || null;
  } catch (err) {
    console.error(`[ERROR] Failed FQDN request for ${groupName}:`, err.message);
    return null;
  }
}

async function main() {
  console.log(`[Start] Playwright crawler`);
  await runCrawler();
}

main();
