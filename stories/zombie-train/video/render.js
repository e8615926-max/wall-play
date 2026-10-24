// Рендер ролика: node render.js            — полный ролик out/zombie_train.mp4
//                node render.js 12.5 40 …  — отдельные кадры в out/frames/ для проверки
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'out');
const FPS = 30;

function timeline() {
  // номера сцен у реплик — из build.py, тайминг — из готовых субтитров
  const scenes = JSON.parse(execFileSync('python3', ['-c',
    'import sys, json; sys.path.insert(0, "."); sys.dont_write_bytecode = True; import build; print(json.dumps([c[0] for c in build.CUES]))'],
    { cwd: ROOT }).toString());
  const ts = s => { const [h, m, r] = s.split(':'); const [sec, ms] = r.split(','); return +h * 3600 + +m * 60 + +sec + +ms / 1000; };
  const blocks = fs.readFileSync(path.join(OUT, 'subtitles.srt'), 'utf8').trim().split(/\n\n/);
  const cues = blocks.map((b, i) => { const l = b.split('\n'); const [a, e] = l[1].split(' --> '); return { scene: scenes[i], start: ts(a), end: ts(e), text: l[2] }; });
  const total = parseFloat(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path.join(OUT, 'voiceover_with_sfx.mp3')]).toString());
  const sc = {};
  for (const c of cues) if (!(c.scene in sc)) sc[c.scene] = { start: c.scene === 1 ? 0 : Math.max(c.start - 0.3, 0) };
  const ids = Object.keys(sc).map(Number).sort((a, b) => a - b);
  ids.forEach((id, i) => { sc[id].end = i + 1 < ids.length ? sc[ids[i + 1]].start : total; });
  return { scenes: sc, cues, total };
}

(async () => {
  const tl = timeline();
  const browser = await chromium.launch({ args: ['--disable-web-security'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'scenes.html'));
  await page.evaluate(t => window.setTimeline(t), tl);
  const grab = t => page.evaluate(t => { window.render(t); return document.getElementById('c').toDataURL('image/jpeg', 0.93); }, t);

  const stills = process.argv.slice(2).map(Number);
  if (stills.length) {
    fs.mkdirSync(path.join(OUT, 'frames'), { recursive: true });
    for (const t of stills) {
      const data = await grab(t);
      fs.writeFileSync(path.join(OUT, 'frames', `f_${t.toFixed(2)}.jpg`), Buffer.from(data.split(',')[1], 'base64'));
    }
    await browser.close();
    return;
  }

  // субтитры для финального ролика — без служебных подписей сцен
  const ass = fs.readFileSync(path.join(OUT, 'subtitles.ass'), 'utf8').split('\n')
    .filter(l => !/,Scene,,0,0,0,,СЦЕНА/.test(l)).join('\n');
  const assPath = path.join(OUT, 'subtitles_video.ass');
  fs.writeFileSync(assPath, ass);

  const frames = Math.ceil(tl.total * FPS);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', String(FPS), '-i', '-',
    '-i', path.join(OUT, 'voiceover_with_sfx.mp3'),
    '-vf', `ass=${assPath}`,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '23', '-maxrate', '4M', '-bufsize', '8M', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', path.join(OUT, 'zombie_train.mp4')], { stdio: ['pipe', 'inherit', 'inherit'] });
  const started = Date.now();
  for (let i = 0; i < frames; i++) {
    const data = await grab(i / FPS);
    const buf = Buffer.from(data.split(',')[1], 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log(`кадр ${i}/${frames}, ${((Date.now() - started) / 1000).toFixed(0)} с`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('готово:', path.join(OUT, 'zombie_train.mp4'));
})();
