// SharedMoments Service Worker
const SW_VERSION = '1.7.1';

// Cache names
const APP_SHELL_CACHE = 'app-shell-v11';
const CDN_CACHE = 'cdn-v1';
const API_CACHE = 'api-v2';
const MEDIA_CACHE = 'media-v1';
const PINNED_MEDIA_CACHE = 'media-pinned-v1';

const ALL_CACHES = [APP_SHELL_CACHE, CDN_CACHE, API_CACHE, MEDIA_CACHE, PINNED_MEDIA_CACHE];

// URLs to pre-cache during install (only public files — no auth required)
const PRECACHE_URLS = [
  '/offline',
  '/manifest.json',
  '/static/pwa/sm-icon-192.png',
  '/static/pwa/sm-icon-512.png',
  '/static/pwa/pwa.js',
  '/static/pwa/idb-manager.js',
];

// Auth-protected JS files — cached on first access via networkFirst strategy
const AUTH_JS_URLS = [
  '/static/js/main.js',
  '/static/js/home.js',
  '/static/js/list.js',
  '/static/js/settings.js',
  '/static/js/timeline.js',
  '/static/js/admin.js',
  '/static/js/nav-drawer.js',
  '/static/js/setup.js',
  '/static/js/countdown.js',
];

// CDN patterns (cache-first)
const CDN_PATTERNS = [
  'cdn.jsdelivr.net',
  'cdnjs.cloudflare.com',
  'fonts.googleapis.com',
  'fonts.gstatic.com',
];

// PWA settings (defaults, updated via postMessage)
let pwaSettings = {
  pwa_cache_expiry_days: 7,
  pwa_offline_all: false,
  pwa_auto_cache_count: 20,
  pwa_wifi_only_upload: false,
  pwa_preload_on_wifi: false,
};

// ===== Install =====
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) => {
      return cache.addAll(PRECACHE_URLS);
    })
  );
});

// ===== Activate =====
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => !ALL_CACHES.includes(name))
          .map((name) => caches.delete(name))
      );
    }).then(() => {
      cleanExpiredCache(pwaSettings.pwa_cache_expiry_days);
      return self.clients.claim();
    })
  );
});

// ===== Fetch =====
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Only handle GET requests over http(s)
  if (event.request.method !== 'GET') return;
  if (!url.protocol.startsWith('http')) return;

  // CDN resources: cache-first
  if (CDN_PATTERNS.some((pattern) => url.hostname.includes(pattern))) {
    event.respondWith(cacheFirst(event.request, CDN_CACHE));
    return;
  }

  // Own JS files: network-first (so updates are always picked up)
  if (url.pathname.startsWith('/static/js/') || url.pathname.startsWith('/static/pwa/')) {
    event.respondWith(networkFirst(event.request, APP_SHELL_CACHE));
    return;
  }

  // Other static assets (images, etc.): cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(event.request, APP_SHELL_CACHE));
    return;
  }

  // Media: check pinned cache first, then stale-while-revalidate
  if (url.pathname.startsWith('/api/v2/media/')) {
    event.respondWith(mediaStrategy(event.request));
    return;
  }

  // PWA files served from root
  if (url.pathname === '/manifest.json' || url.pathname === '/sw.js') {
    event.respondWith(networkFirst(event.request, APP_SHELL_CACHE));
    return;
  }

  // Navigation requests (pages): network-first with offline fallback
  if (event.request.mode === 'navigate') {
    event.respondWith(navigationStrategy(event.request));
    return;
  }

  // API requests: network-first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request, API_CACHE));
    return;
  }

  // Default: network-first
  event.respondWith(networkFirst(event.request, API_CACHE));
});

// ===== Sync =====
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-outbox') {
    event.waitUntil(syncOutbox());
  }
});

// ===== Message Handler =====
self.addEventListener('message', (event) => {
  const { type, data } = event.data || {};

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAN_CACHE':
      cleanAllCaches().then(() => {
        notifyClients({ type: 'CACHE_CLEANED' });
      });
      break;

    case 'CACHE_URLS':
      if (data && data.urls) {
        cacheUrls(data.urls, data.cacheName || MEDIA_CACHE).then((cached) => {
          if (data.itemId) {
            notifyClients({ type: 'CACHE_URLS_DONE', data: { itemId: data.itemId, cached: cached } });
          }
        });
      }
      break;

    case 'UNCACHE_URLS':
      if (data && data.urls) {
        uncacheUrls(data.urls, data.cacheName || PINNED_MEDIA_CACHE);
      }
      break;

    case 'PWA_SETTINGS':
      if (data) {
        Object.assign(pwaSettings, data);
      }
      break;

    case 'PRELOAD_ALL':
      if (data && data.urls) {
        cacheUrls(data.urls, MEDIA_CACHE).then(() => {
          notifyClients({ type: 'PRELOAD_COMPLETE', data: { count: data.urls.length } });
        });
      }
      break;

    case 'GET_VERSION':
      if (event.ports && event.ports[0]) {
        event.ports[0].postMessage({ version: SW_VERSION });
      }
      break;
  }
});

// ===== Strategies =====

async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    return offlineResponse(request);
  }
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request, { cache: 'no-store' });
    // Don't cache redirects (e.g. 302 to /login)
    if (response.ok && !response.redirected) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    if (cached) return cached;
    // Return empty JS for missing scripts so the page doesn't break
    if (request.url.endsWith('.js')) {
      return new Response('/* offline: not cached */', {
        status: 200,
        headers: { 'Content-Type': 'application/javascript' },
      });
    }
    return offlineResponse(request);
  }
}

// Offline-Response: JSON für API-Requests, sonst Plain-Text
function offlineResponse(request) {
  const url = typeof request === 'string' ? request : request.url;
  if (url.includes('/api/')) {
    return new Response(JSON.stringify({ status: 'error', message: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  return new Response('Offline', { status: 503 });
}

async function mediaStrategy(request) {
  // Check pinned cache first (cache-first for pinned media)
  const pinnedCache = await caches.open(PINNED_MEDIA_CACHE);
  const pinned = await pinnedCache.match(request);
  if (pinned) return pinned;

  // Stale-while-revalidate for regular media
  const mediaCache = await caches.open(MEDIA_CACHE);
  const cached = await mediaCache.match(request);

  const fetchPromise = fetch(request).then((response) => {
    if (response.ok && response.status !== 206) {
      mediaCache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);

  if (cached) {
    // Return cached immediately, revalidate in background
    fetchPromise; // fire and forget
    return cached;
  }

  // No cache, must wait for network
  const networkResponse = await fetchPromise;
  if (networkResponse) return networkResponse;

  return new Response('Media not available offline', { status: 503 });
}

async function navigationStrategy(request) {
  try {
    const response = await fetch(request, { cache: 'no-store' });
    // Cache successful navigation responses (not redirects to /login)
    if (response.ok && !response.redirected) {
      const cache = await caches.open(API_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Try specific caches (not global caches.match which searches ALL caches)
    const apiCache = await caches.open(API_CACHE);
    const cached = await apiCache.match(request);
    if (cached) return cached;

    // Auch MEDIA_CACHE prüfen (Galerie-Seiten von PRELOAD_ALL + gepinnte Items)
    const mediaCache = await caches.open(MEDIA_CACHE);
    const mediaCached = await mediaCache.match(request);
    if (mediaCached) return mediaCached;

    const pinnedCache = await caches.open(PINNED_MEDIA_CACHE);
    const pinnedCached = await pinnedCache.match(request);
    if (pinnedCached) return pinnedCached;

    // Fallback to offline page
    const appCache = await caches.open(APP_SHELL_CACHE);
    const offlinePage = await appCache.match('/offline');
    if (offlinePage) return offlinePage;

    return new Response('<h1>Offline</h1>', {
      headers: { 'Content-Type': 'text/html' },
      status: 503,
    });
  }
}

// ===== Outbox Sync =====

async function syncOutbox() {
  // Import idb-manager is not available in SW context, so we use IndexedDB directly
  const db = await openDB();
  const tx = db.transaction('outbox', 'readonly');
  const store = tx.objectStore('outbox');
  const items = await getAllFromStore(store);

  for (const item of items) {
    if (item.status === 'syncing' || item.status === 'client-syncing') continue;

    try {
      // Mark as syncing
      await updateOutboxStatus(db, item.id, 'syncing');

      // Upload files first (nur wenn contentURL noch nicht gesetzt)
      let contentURL = item.contentURL || '';
      if (!contentURL && item.files && item.files.length > 0) {
        const uploadedUrls = [];
        for (const file of item.files) {
          const formData = new FormData();
          formData.append('file', new Blob([file.data], { type: file.type }), file.name);

          const uploadResponse = await fetch('/api/v2/upload', {
            method: 'POST',
            body: formData,
          });

          if (!uploadResponse.ok) throw new Error('Upload failed');
          const uploadResult = await uploadResponse.json();
          if (uploadResult.status !== 'success') throw new Error(uploadResult.message);
          uploadedUrls.push(uploadResult.data.filename);
        }
        contentURL = uploadedUrls.join(';');
      }

      // Create item
      const formData = new FormData();
      formData.append('title', item.title);
      formData.append('content', item.content);
      formData.append('contentType', item.contentType);
      formData.append('listType', item.listType);
      formData.append('contentURL', contentURL);
      formData.append('dateCreated', item.dateCreated);
      formData.append('edition', item.edition || 'all');

      const response = await fetch('/api/v2/items', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Create item failed');
      const result = await response.json();
      if (result.status !== 'success') throw new Error(result.message);

      // Remove from outbox
      await removeFromOutboxDB(db, item.id);

      // Notify clients
      notifyClients({
        type: 'OUTBOX_ITEM_SYNCED',
        data: { id: item.id, title: item.title },
      });

    } catch (err) {
      // Mark as pending again for retry
      await updateOutboxStatus(db, item.id, 'pending');
    }
  }

  // Notify clients about outbox count update
  const countTx = db.transaction('outbox', 'readonly');
  const countStore = countTx.objectStore('outbox');
  const remaining = await getAllFromStore(countStore);
  notifyClients({ type: 'OUTBOX_COUNT', data: { count: remaining.length } });
}

// ===== IndexedDB helpers for SW =====

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('SharedMomentsOffline', 1);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('pinnedItems')) {
        db.createObjectStore('pinnedItems', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('outbox')) {
        db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true });
      }
      if (!db.objectStoreNames.contains('cacheMetadata')) {
        db.createObjectStore('cacheMetadata', { keyPath: 'url' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function getAllFromStore(store) {
  return new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function updateOutboxStatus(db, id, status) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    const store = tx.objectStore('outbox');
    const req = store.get(id);
    req.onsuccess = () => {
      const item = req.result;
      if (item) {
        item.status = status;
        store.put(item);
      }
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

async function removeFromOutboxDB(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    const store = tx.objectStore('outbox');
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ===== Cache Management =====

async function cacheUrls(urls, cacheName) {
  const cache = await caches.open(cacheName);
  const db = await openDB();
  let cached = 0;
  for (const url of urls) {
    try {
      const response = await fetch(url, { credentials: 'include' });
      if (response.ok) {
        await cache.put(url, response);
        cached++;
        // Store metadata
        const tx = db.transaction('cacheMetadata', 'readwrite');
        tx.objectStore('cacheMetadata').put({
          url: url,
          cachedAt: Date.now(),
          cacheName: cacheName,
        });
      }
    } catch (e) {
      // Skip failed URLs
    }
  }
  return cached;
}

async function uncacheUrls(urls, cacheName) {
  const cache = await caches.open(cacheName);
  for (const url of urls) {
    await cache.delete(url);
  }
}

async function cleanExpiredCache(expiryDays) {
  if (!expiryDays || expiryDays <= 0) return;

  const expiryMs = expiryDays * 24 * 60 * 60 * 1000;
  const now = Date.now();

  try {
    const db = await openDB();
    const tx = db.transaction('cacheMetadata', 'readonly');
    const store = tx.objectStore('cacheMetadata');
    const entries = await getAllFromStore(store);

    // Get all pinned item URLs to exclude
    const pinnedTx = db.transaction('pinnedItems', 'readonly');
    const pinnedStore = pinnedTx.objectStore('pinnedItems');
    const pinnedItems = await getAllFromStore(pinnedStore);
    const pinnedUrls = new Set();
    pinnedItems.forEach((item) => {
      if (item.mediaUrls) {
        item.mediaUrls.forEach((url) => pinnedUrls.add(url));
      }
    });

    for (const entry of entries) {
      if (pinnedUrls.has(entry.url)) continue;
      if (now - entry.cachedAt > expiryMs) {
        // Delete from cache
        if (entry.cacheName) {
          const cache = await caches.open(entry.cacheName);
          await cache.delete(entry.url);
        }
        // Delete metadata
        const delTx = db.transaction('cacheMetadata', 'readwrite');
        delTx.objectStore('cacheMetadata').delete(entry.url);
      }
    }
  } catch (e) {
    // Ignore errors during cleanup
  }
}

async function cleanAllCaches() {
  // Alle Caches (inkl. gepinnter) löschen — wird bei "Cache leeren" ausgelöst
  const cachesToClean = [API_CACHE, MEDIA_CACHE, PINNED_MEDIA_CACHE, CDN_CACHE];
  for (const cacheName of cachesToClean) {
    await caches.delete(cacheName);
  }
  // Clean all metadata
  try {
    const db = await openDB();
    const tx = db.transaction('cacheMetadata', 'readwrite');
    tx.objectStore('cacheMetadata').clear();
  } catch (e) {
    // Ignore
  }
  // Pinned items aus IndexedDB leeren
  try {
    const db = await openDB();
    const tx = db.transaction('pinnedItems', 'readwrite');
    tx.objectStore('pinnedItems').clear();
  } catch (e) {
    // Ignore
  }
}

// ===== Utility =====

function notifyClients(message) {
  self.clients.matchAll({ type: 'window' }).then((clients) => {
    clients.forEach((client) => client.postMessage(message));
  });
}
