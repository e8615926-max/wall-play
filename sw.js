// Кэш для игры без интернета: только свои файлы, чужие сайты не трогаем
const CACHE = 'wall-play-v56';
const FILES = ['./', './index.html', './manifest.webmanifest', './icon.svg'];
const NET_WAIT = 3500;   // медленная сеть: если есть копия в кэше, не ждём дольше — открываем её, а свежую версию докачиваем в фоне
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== self.location.origin) return;
  const net = fetch(e.request).then(r => {
    if (r.ok && r.type === 'basic') { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)).catch(() => {}); }
    return r;
  });
  const cached = () => caches.match(e.request, { ignoreSearch: true }).then(r => r || (e.request.mode === 'navigate' ? caches.match('./index.html') : undefined));
  e.waitUntil(net.catch(() => {}));   // скачивание не обрывается, даже если ответили из кэша
  e.respondWith(new Promise(done => {
    let settled = false;
    const finish = r => { if (!settled && r) { settled = true; done(r); } };
    const timer = setTimeout(() => cached().then(finish), NET_WAIT);
    net.then(r => { clearTimeout(timer); finish(r); }, () => { clearTimeout(timer); cached().then(r => { if (r) finish(r); else if (!settled) { settled = true; done(Response.error()); } }); });
  }));
});
