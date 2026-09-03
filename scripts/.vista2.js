const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox'] });
  const p = await b.newPage({ viewport: { width: 900, height: 1200 }, deviceScaleFactor: 1 });
  await p.goto('file://' + process.argv[2], { waitUntil: 'load', timeout: 60000 });
  await p.waitForTimeout(1500);
  await p.screenshot({ path: '/tmp/art-1.png' });
  await p.evaluate(() => window.scrollTo(0, 2100));
  await p.waitForTimeout(400); await p.screenshot({ path: '/tmp/art-2.png' });
  await p.evaluate(() => window.scrollTo(0, 4400));
  await p.waitForTimeout(400); await p.screenshot({ path: '/tmp/art-3.png' });
  await b.close();
})();
