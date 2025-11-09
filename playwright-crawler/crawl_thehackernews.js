const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const https = require('https');

const BASE_URLS = [
  { url: 'https://thehackernews.com/', category: 'main' },
  { url: 'https://thehackernews.com/search/label/Cyber%20Attack', category: 'cyber_attack' },
  { url: 'https://thehackernews.com/search/label/Vulnerability', category: 'vulnerability' }
];

const todayStr = new Date().toISOString().split('T')[0];

const downloadImage = (url, filepath) => {
  return new Promise((resolve, reject) => {
    https.get(url, res => {
      if (res.statusCode !== 200) return reject(new Error(`Image download failed: ${res.statusCode}`));
      const fileStream = fs.createWriteStream(filepath);
      res.pipe(fileStream);
      fileStream.on('finish', () => fileStream.close(resolve));
    }).on('error', reject);
  });
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 800 },
    javaScriptEnabled: true,
    locale: 'en-US'
  });

  await context.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  for (const { url: baseUrl, category } of BASE_URLS) {
    const page = await context.newPage();
    try {
      console.log(`[${category}] Visiting: ${baseUrl}`);
      await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

      const articles = await page.$$eval('div.body-post.clear', nodes =>
        nodes.slice(0, 4).map(node => {
          const linkEl = node.querySelector('a.story-link');
          const titleEl = node.querySelector('h2.home-title');
          const imgEl = node.querySelector('.img-ratio img');
          if (!linkEl || !titleEl) return null;

          return {
            title: titleEl.textContent.trim(),
            url: linkEl.href,
            thumbImg: imgEl?.src || ''
          };
        }).filter(Boolean)
      );

      console.log(`[${category}] Articles found: ${articles.length}`);

      for (const [i, article] of articles.entries()) {
        const safeTitle = article.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
        const articleDir = path.join(
          __dirname,
          'downloads',
          'thehackernews',
          todayStr,
          `${category}_${i + 1}_${safeTitle}`
        );

        const articlePage = await context.newPage();
        await articlePage.goto(article.url, { waitUntil: 'domcontentloaded', timeout: 60000 });

        let actualDateText = '';
        try {
          actualDateText = await articlePage.$eval('div.postmeta span.author', el => el.textContent.trim());
        } catch {
          console.warn(`Failed to extract date: ${article.url}`);
          await articlePage.close();
          continue;
        }

        const parsedDate = new Date(actualDateText + ' 00:00:00').toISOString().split('T')[0];
        if (parsedDate !== todayStr) {
          console.log(`[${category}] Skipping (article date: ${actualDateText}): ${article.title}`);
          await articlePage.close();
          continue;
        }

        console.log(`[${category}] Collecting: ${article.title}`);

        let paragraphs = [];
        try {
          paragraphs = await articlePage.$$eval('div.articlebody p', nodes =>
            nodes.map(p => p.textContent.trim()).filter(p => p.length > 0)
          );
        } catch {
          console.warn('Failed to collect <p> elements from body.');
        }

        if (paragraphs.length === 0) {
          console.log(`No body content — skipping: ${article.title}`);
          await articlePage.close();
          continue;
        }

        fs.mkdirSync(articleDir, { recursive: true });

        const fullText = `Title: ${article.title}\nURL: ${article.url}\nDate: ${actualDateText}\n\nContent:\n${paragraphs.join('\n\n')}`;
        fs.writeFileSync(path.join(articleDir, 'article.txt'), fullText, 'utf-8');

        if (article.thumbImg?.startsWith('http')) {
          const ext = path.extname(new URL(article.thumbImg).pathname).split('?')[0] || '.jpg';
          const imgPath = path.join(articleDir, `thumb${ext}`);
          try {
            await downloadImage(article.thumbImg, imgPath);
            console.log(`Thumbnail saved: ${imgPath}`);
          } catch {
            console.warn(`Thumbnail download failed: ${article.thumbImg}`);
          }
        }

        await articlePage.close();
        console.log('Saved\n' + '-'.repeat(80));
      }

      await page.close();
    } catch (err) {
      console.error(`Error [${category}]:`, err.message);
      await page.close();
    }
  }

  await browser.close();
})();
