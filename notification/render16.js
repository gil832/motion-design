// Render scene16.html (1920x1080) to PNG frames. Usage: node render16.js OUTDIR [fps] [t1 t2 ... for stills]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [out, fpsArg, ...stills] = process.argv.slice(2);
  const fps = Number(fpsArg || 25);
  const b = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + path.resolve(__dirname, 'scene16.html'));
  await p.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(i => i.decode())); });
  const times = stills.length ? stills.map(Number) : [...Array(Math.round((await p.evaluate(() => window.DURATION)) * fps)).keys()].map(i => i / fps);
  for (let i = 0; i < times.length; i++) {
    await p.evaluate(t => render(t), times[i]);
    await p.waitForTimeout(stills.length ? 50 : 0);
    await p.screenshot({ path: `${out}/f_${String(i).padStart(4, '0')}.png` });
  }
  await b.close();
  console.log(`${times.length} frames`);
})();
