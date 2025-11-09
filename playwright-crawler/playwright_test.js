const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    javaScriptEnabled: true,
    locale: 'en-US'
  });

  const page = await context.newPage();

  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  try {
    console.log('Opening page in stealth mode...');
    await page.goto('https://www.boannews.com/media/t_list.asp', {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    const title = await page.title();
    console.log(`Page title: ${title}`);

    const bodyHtml = await page.content();
    console.log(`Body length: ${bodyHtml.length} chars`);

    if (bodyHtml.includes('story-link') || bodyHtml.includes('home-title')) {
      console.log('Key article elements detected.');
    } else {
      console.log('Key article elements not found (bypass failed or DOM changed).');
    }

    await page.screenshot({ path: 'stealth_debug.png', fullPage: true });
    console.log('Screenshot saved: stealth_debug.png');
  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await browser.close();
  }
})();
