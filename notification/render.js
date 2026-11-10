// Render scene.html to PNG frames. Usage: node render.js OUTDIR [fps]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const out = process.argv[2], fps = Number(process.argv[3] || 25);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.resolve(__dirname, 'scene.html'));
  await p.evaluate(() => document.fonts.ready);
  const dur = await p.evaluate(() => window.DURATION);
  const n = Math.round(dur * fps);
  for (let i = 0; i < n; i++) {
    await p.evaluate(t => render(t), i / fps);
    await p.screenshot({ path: `${out}/f_${String(i).padStart(4, '0')}.png` });
  }
  await b.close();
  console.log(`${n} frames`);
})();
