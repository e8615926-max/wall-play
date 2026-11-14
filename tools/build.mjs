// Сборка Wall Play для сайта (Vercel). Исходник в репозитории остаётся одним читаемым index.html —
// его можно открыть и как файл. На сайт уходит быстрая копия:
//   - главный скрипт сжат (terser) и вынесен в game.js: браузер кэширует его уже скомпилированным,
//     поэтому повторный запуск игры заметно быстрее, а скачивать нужно меньше;
//   - у каждой выкладки свой ключ кэша в sw.js: офлайн-копия никогда не смешивает файлы разных версий.
// Запуск: node tools/build.mjs <папка с исходниками> <папка для сайта>
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { minify } from 'terser';

const [srcDir, outDir] = process.argv.slice(2);
if (!srcDir || !outDir) { console.error('usage: node tools/build.mjs <src> <out>'); process.exit(2); }
mkdirSync(outDir, { recursive: true });
const html = readFileSync(join(srcDir, 'index.html'), 'utf8');

// ровно один исполняемый <script> без атрибутов — это игра (PeerJS лежит отдельно как text/plain и не трогается)
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
if (scripts.length !== 1) throw new Error('expected exactly one main <script>, found ' + scripts.length);
const src = scripts[0][1];
const r = await minify(src, {
  ecma: 2020,
  compress: { passes: 2, keep_fargs: true },
  mangle: true,
  format: { comments: false },
});
if (!r.code || r.code.length < src.length * 0.3) throw new Error('minified code looks wrong');
new Function(r.code);   // синтаксис проверен ещё раз: сломанная сборка не уйдёт на сайт

// версия — по всему, что уходит на сайт: поменялся код, страница, иконки или sw.js — новый ключ кэша
const vh = createHash('sha1').update(r.code).update(html).update(readFileSync(join(srcDir, 'sw.js')));
for (const f of ['manifest.webmanifest', 'icon.svg', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'og.png']) vh.update(readFileSync(join(srcDir, f)));
const ver = vh.digest('hex').slice(0, 10);
writeFileSync(join(outDir, 'game.js'), r.code);

let page = html.slice(0, scripts[0].index) + '<script src="game.js?v=' + ver + '"></script>' + html.slice(scripts[0].index + scripts[0][0].length);
// запасная библиотека мультиплеера (PeerJS) нужна редко: в сборке она не встроена в страницу, а лежит рядом и грузится по требованию
const peer = page.match(/<script type="text\/plain" id="peerjs-lib">([\s\S]*?)<\/script>\s*/);
if (!peer) throw new Error('peerjs-lib block not found');
writeFileSync(join(outDir, 'peerjs.js'), peer[1].trim() + '\n');
page = page.replace(peer[0], '');
// браузер начинает качать игру сразу, ещё не дочитав страницу
page = page.replace('</head>', '<link rel="preload" href="game.js?v=' + ver + '" as="script">\n</head>');
page = page.replace(/<!--(?!\[)[\s\S]*?-->/g, '');   // HTML-комментарии посетителю не нужны
writeFileSync(join(outDir, 'index.html'), page);

let sw = readFileSync(join(srcDir, 'sw.js'), 'utf8');
const cacheRe = /const CACHE = '([^']+)';/, filesRe = /const FILES = \[([^\]]*)\];/;
if (!cacheRe.test(sw) || !filesRe.test(sw)) throw new Error('sw.js: CACHE or FILES not found');
sw = sw.replace(cacheRe, (m, c) => "const CACHE = '" + c + '-' + ver + "';")
       .replace(filesRe, (m, f) => 'const FILES = [' + f + ", './game.js?v=" + ver + "'];");   // с версией: у game.js долгий кэш, адрес меняется с каждой выкладкой
writeFileSync(join(outDir, 'sw.js'), sw);

for (const f of ['manifest.webmanifest', 'icon.svg', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'og.png']) copyFileSync(join(srcDir, f), join(outDir, f));   // иконки и картинка для превью ссылки
console.log('built', { version: ver, 'index.html': page.length, 'game.js': r.code.length, 'peerjs.js': peer[1].length, source: html.length });
