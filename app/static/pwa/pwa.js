// SharedMoments PWA Client Logic

// ===== Translations =====
// translationsArray is set inline in head.html (synchronous, server-rendered)

function _(key) {
   if (typeof translationsArray !== 'undefined' && translationsArray[key] && translationsArray[key].translatedText) {
       return translationsArray[key].translatedText;
   }
   return key;
}

// ===== Install Prompt =====
window._pwaInstallPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  window._pwaInstallPrompt = e;
  document.querySelectorAll('.pwa-install-btn').forEach((btn) => {
    btn.style.display = '';
  });
});

window.addEventListener('appinstalled', () => {
  window._pwaInstallPrompt = null;
  document.querySelectorAll('.pwa-install-btn').forEach((btn) => {
    btn.style.display = 'none';
  });
});

function installPWA() {
  if (!window._pwaInstallPrompt) return;
  // Close nav drawer so it doesn't cover the install dialog
  const navDrawer = document.getElementById('dialog-nav-drawer');
  if (navDrawer && navDrawer.classList.contains('active')) {
    navDrawer.classList.remove('active');
    const overlay = document.getElementById('div-overlay-nav-drawer');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = 'auto';
  }
  // Must call prompt() synchronously within the user gesture
  const promptEvent = window._pwaInstallPrompt;
  window._pwaInstallPrompt = null;
  try {
    promptEvent.prompt();
  } catch (err) {
    return;
  }
  promptEvent.userChoice.then((choice) => {
    if (choice.outcome === 'accepted') {
      document.querySelectorAll('.pwa-install-btn').forEach((btn) => {
        btn.style.display = 'none';
      });
    }
  }).catch(() => {});
}

// ===== Offline/Online Indicator (at profile picture) =====

let _connectivityInterval = null;

function showOfflineIndicator() {
  const indicator = document.getElementById('pwa-offline-indicator');
  if (indicator) indicator.style.display = 'flex';
}

function hideOfflineIndicator() {
  const indicator = document.getElementById('pwa-offline-indicator');
  if (indicator) indicator.style.display = 'none';
}

function goOffline() {
  showOfflineIndicator();
  startConnectivityCheck();
}

function goOnline() {
  stopConnectivityCheck();
  hideOfflineIndicator();
  fallbackSyncForce();
  cachePendingPins();
}

// Periodische Prüfung ob Server wieder erreichbar ist
function startConnectivityCheck() {
  if (_connectivityInterval) return;
  _connectivityInterval = setInterval(() => {
    fetch('/manifest.json', { method: 'HEAD', cache: 'no-store' })
      .then((r) => { if (r.ok) goOnline(); })
      .catch(() => {});
  }, 5000);
}

function stopConnectivityCheck() {
  if (_connectivityInterval) {
    clearInterval(_connectivityInterval);
    _connectivityInterval = null;
  }
}

window.addEventListener('online', goOnline);
window.addEventListener('offline', goOffline);

// Konnektivität wird im zentralen DOMContentLoaded-Handler unten geprüft

// ===== SW Update Notification =====

function checkForSWUpdate() {
  if (!('serviceWorker' in navigator)) return;

  navigator.serviceWorker.ready.then((registration) => {
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      if (!newWorker) return;

      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          showUpdateBanner(registration);
        }
      });
    });
  });
}

function showUpdateBanner(registration) {
  let banner = document.getElementById('pwa-update-banner');
  if (banner) return; // Already showing

  banner = document.createElement('div');
  banner.id = 'pwa-update-banner';
  banner.className = 'snackbar active';
  banner.style.cssText = 'z-index: 9998;';

  const text = _('A new version is available');
  const updateText = _('Update');

  banner.innerHTML = '<span class="max">' + text + '</span>' +
    '<a onclick="applyUpdate()" style="cursor:pointer;font-weight:bold;">' + updateText + '</a>';
  document.body.appendChild(banner);

  window._pendingRegistration = registration;
}

function applyUpdate() {
  if (window._pendingRegistration && window._pendingRegistration.waiting) {
    window._pendingRegistration.waiting.postMessage({ type: 'SKIP_WAITING' });
  }
  const banner = document.getElementById('pwa-update-banner');
  if (banner) banner.remove();
}

// Listen for controller change (new SW activated) -> reload
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    window.location.reload();
  });
}

checkForSWUpdate();

// ===== Storage Estimate =====

async function getStorageEstimate() {
  if (navigator.storage && navigator.storage.estimate) {
    const estimate = await navigator.storage.estimate();
    return {
      usage: estimate.usage || 0,
      quota: estimate.quota || 0,
      usageMB: ((estimate.usage || 0) / (1024 * 1024)).toFixed(1),
      quotaMB: ((estimate.quota || 0) / (1024 * 1024)).toFixed(0),
    };
  }
  return null;
}

// ===== Cache Management =====

function clearOfflineCache() {
  if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return Promise.resolve();
  navigator.serviceWorker.controller.postMessage({ type: 'CLEAN_CACHE' });
  return new Promise((resolve) => {
    const handler = (event) => {
      if (event.data && event.data.type === 'CACHE_CLEANED') {
        navigator.serviceWorker.removeEventListener('message', handler);
        resolve();
      }
    };
    navigator.serviceWorker.addEventListener('message', handler);
    // Timeout fallback
    setTimeout(resolve, 5000);
  });
}

// ===== Pin/Unpin Items =====

async function togglePinItem(button) {
  if (!isPwaInstalled()) return;
  const itemId = parseInt(button.dataset.itemId, 10);
  const mediaUrlsStr = button.dataset.mediaUrls || '';
  const mediaUrls = mediaUrlsStr.split(';').filter(Boolean).map((url) => '/api/v2/media/' + url);
  const icon = button.querySelector('i');
  const pinState = JSON.parse(localStorage.getItem('pwa_pinned_items') || '{}');
  const pinned = !!pinState[String(itemId)];

  if (pinned) {
    // Unpin
    await unpinItem(itemId);
    // Aus localStorage entfernen
    const pinState = JSON.parse(localStorage.getItem('pwa_pinned_items') || '{}');
    delete pinState[itemId];
    localStorage.setItem('pwa_pinned_items', JSON.stringify(pinState));
    // Remove from pinned cache (media + gallery page)
    const urlsToRemove = [...mediaUrls];
    if (mediaUrls.length > 1) {
      urlsToRemove.push('/gallery/' + itemId);
    }
    if (navigator.serviceWorker && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({
        type: 'UNCACHE_URLS',
        data: { urls: urlsToRemove, cacheName: 'media-pinned-v1' },
      });
    }
    icon.textContent = 'download';
    button.classList.remove('primary');
    const msg = _('Item unpinned from offline');
    showPWASnackbar(msg);
  } else {
    // Pin
    const title = button.dataset.itemTitle || '';
    await pinItem(itemId, mediaUrls, title);

    // Pin-State in localStorage speichern mit Status
    const pinState = JSON.parse(localStorage.getItem('pwa_pinned_items') || '{}');

    // Immer erst als "pending" markieren mit Sync-Icon
    pinState[itemId] = 'pending';
    localStorage.setItem('pwa_pinned_items', JSON.stringify(pinState));
    window._pinStartTime = Date.now();
    icon.textContent = 'sync';
    button.classList.add('primary');

    if (navigator.onLine) {
      // Online: Download starten, SW bestätigt wenn fertig
      const urlsToCache = [...mediaUrls];
      if (mediaUrls.length > 1) {
        urlsToCache.push('/gallery/' + itemId);
      }
      if (navigator.serviceWorker && navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
          type: 'CACHE_URLS',
          data: { urls: urlsToCache, cacheName: 'media-pinned-v1', itemId: itemId },
        });
      }
      showPWASnackbar(_('Downloading for offline use...'));
    } else {
      // Offline: Download vormerken
      showPWASnackbar(_('Download starts when online'));
    }
  }
}

// Check if running as installed PWA
function isPwaInstalled() {
  // Standard standalone checks
  if (window.matchMedia('(display-mode: standalone)').matches) return true;
  if (window.matchMedia('(display-mode: window-controls-overlay)').matches) return true;
  if (window.matchMedia('(display-mode: minimal-ui)').matches) return true;
  if (navigator.standalone === true) return true; // iOS
  // If explicitly in regular browser tab, not a PWA
  if (window.matchMedia('(display-mode: browser)').matches) return false;
  // Fallback for browsers without display-mode support: check SW
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) return true;
  return false;
}

// Check and set pin state on page load
function initPinButtons() {
  const buttons = document.querySelectorAll('.pwa-pin-btn');

  // Hide pin buttons if not running as PWA
  if (!isPwaInstalled()) {
    for (const btn of buttons) btn.style.display = 'none';
    return;
  }

  const allOffline = localStorage.getItem('pwa_offline_all') === 'true';
  const pinState = JSON.parse(localStorage.getItem('pwa_pinned_items') || '{}');
  for (const btn of buttons) {
    const itemId = parseInt(btn.dataset.itemId, 10);
    const icon = btn.querySelector('i');
    const state = pinState[String(itemId)];
    if (allOffline || state) {
      btn.classList.add('primary');
      if (state === 'pending') {
        if (icon) icon.textContent = 'sync';
      } else {
        if (icon) icon.textContent = 'download_done';
      }
    } else {
      btn.classList.remove('primary');
      if (icon) icon.textContent = 'download';
    }
  }
}

// Pending Pins cachen wenn wieder online
async function cachePendingPins() {
  if (!navigator.onLine) return;
  if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return;

  const pinState = JSON.parse(localStorage.getItem('pwa_pinned_items') || '{}');
  const pendingIds = Object.entries(pinState).filter(([_, v]) => v === 'pending').map(([k]) => k);
  if (pendingIds.length === 0) return;

  for (const itemId of pendingIds) {
    try {
      // Zuerst aus IndexedDB versuchen
      let mediaUrls = null;
      try {
        const pinnedItems = await getAllPinnedItems();
        const item = pinnedItems.find((i) => String(i.id) === itemId);
        if (item && item.mediaUrls && item.mediaUrls.length > 0) {
          mediaUrls = item.mediaUrls;
        }
      } catch (e) {}

      // Fallback: URLs aus dem DOM lesen
      if (!mediaUrls) {
        const btn = document.querySelector('.pwa-pin-btn[data-item-id="' + itemId + '"]');
        if (btn && btn.dataset.mediaUrls) {
          mediaUrls = btn.dataset.mediaUrls.split(';').filter(Boolean).map((url) => '/api/v2/media/' + url);
        }
      }

      if (!mediaUrls || mediaUrls.length === 0) continue;

      const urlsToCache = [...mediaUrls];
      if (mediaUrls.length > 1) {
        urlsToCache.push('/gallery/' + itemId);
      }
      window._pinStartTime = Date.now();
      navigator.serviceWorker.controller.postMessage({
        type: 'CACHE_URLS',
        data: { urls: urlsToCache, cacheName: 'media-pinned-v1', itemId: parseInt(itemId) },
      });
    } catch (e) {
      // Skip failed items
    }
  }
}

// ===== Outbox / Sync Queue =====

async function updateOutboxBadge() {
  const count = await getOutboxCount();
  const badge = document.getElementById('pwa-outbox-badge');
  if (badge) {
    if (count > 0) {
      badge.textContent = count;
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  }
}

// Render outbox items as ghost cards
async function renderOutboxGhostCards() {
  const items = await getOutboxItems();

  // === Home items ghost cards ===
  const homeContainer = document.getElementById('div-render-home-items');
  if (homeContainer) {
    homeContainer.querySelectorAll('.outbox-ghost-card').forEach((el) => el.remove());

    const currentListType = window.listType;
    const homeItems = items.filter((i) => i.contentType !== 'list' && String(i.listType) === String(currentListType));

    for (const item of homeItems) {
      const card = document.createElement('article');
      card.className = 'no-padding primary-container outbox-ghost-card';
      card.dataset.outboxId = item.id;
      card.style.cssText = 'opacity: 0.6; position: relative;';

      // Erstes Bild als Vorschau anzeigen
      let imageHtml = '';
      if (item.files && item.files.length > 0) {
        try {
          const firstFile = item.files[0];
          if (firstFile.type && firstFile.type.startsWith('image/')) {
            const blob = new Blob([firstFile.data], { type: firstFile.type });
            const url = URL.createObjectURL(blob);
            imageHtml = '<img src="' + url + '" class="responsive" style="max-height:300px;object-fit:cover;width:100%;">';
          }
        } catch (e) {}
      }

      card.innerHTML =
        imageHtml +
        '<div class="padding">' +
          '<nav style="margin-bottom:0.5rem;">' +
            '<a class="chip no-border tertiary small round" href="javascript:void(0)" style="cursor:pointer;">' +
              '<i class="small">cloud_off</i>&nbsp;' +
              '<span>' + _('Not synced') + '</span>' +
            '</a>' +
            '<div class="max"></div>' +
            '<button class="chip no-border small round" onclick="event.stopPropagation();deleteGhostCard(' + item.id + ')" title="' + _('Delete') + '">' +
              '<i class="small">delete</i>' +
            '</button>' +
            '<button class="chip no-border tertiary small round" onclick="event.stopPropagation();forceSync()" title="' + _('Sync now') + '">' +
              '<i class="small">cloud_upload</i>' +
            '</button>' +
          '</nav>' +
          '<h5>' + escapeHtml(item.title || '') + '</h5>' +
          '<p>' + escapeHtml(item.content || '') + '</p>' +
        '</div>';
      homeContainer.insertBefore(card, homeContainer.firstChild);
    }
  }

  // === Timeline/Moments ghost cards ===
  const timelineContainer = document.getElementById('div-render-timeline-card');
  if (timelineContainer) {
    timelineContainer.querySelectorAll('.outbox-ghost-card').forEach((el) => el.remove());

    const timelineItems = items.filter((i) => String(i.listType) === '2');
    if (timelineItems.length > 0) {
      const nav = timelineContainer.querySelector('nav');
      if (nav) {
        // "Neuen Moment erstellen"-Button finden (letztes div mit arrow_forward)
        const allDivs = nav.querySelectorAll('div.center-align');
        let addBtnDiv = null;
        for (const d of allDivs) {
          const icon = d.querySelector('i');
          if (icon && icon.textContent.trim() === 'arrow_forward') {
            addBtnDiv = d;
            break;
          }
        }

        for (const item of timelineItems) {
          const ghostDiv = document.createElement('div');
          ghostDiv.className = 'center-align outbox-ghost-card';
          ghostDiv.dataset.outboxId = item.id;
          ghostDiv.style.opacity = '0.5';
          ghostDiv.innerHTML =
            '<div class="small-margin">' + escapeHtml(item.title || '') + '</div>' +
            '<button class="circle small" onclick="deleteGhostCard(' + item.id + ')" title="' + _('Delete') + '">' +
              '<i>delete</i>' +
            '</button>' +
            '<div class="small-margin">' + escapeHtml(item.dateCreated || '') + '</div>';

          const hr = document.createElement('hr');
          hr.className = 'max timeline-hr outbox-ghost-card';
          hr.style.opacity = '0.5';

          if (addBtnDiv) {
            nav.insertBefore(ghostDiv, addBtnDiv);
            nav.insertBefore(hr, addBtnDiv);
          } else {
            nav.appendChild(ghostDiv);
            nav.appendChild(hr);
          }
        }
      }
    }
  }
}

// ===== Ghostcard Delete =====

function deleteGhostCard(outboxId) {
  document.getElementById('input-delete-ghostcard-id').value = outboxId;
  callUi('#dialog-delete-ghostcard');
}

async function confirmDeleteGhostCard() {
  const val = document.getElementById('input-delete-ghostcard-id').value;
  callUi('#dialog-delete-ghostcard');
  if (val === 'all') {
    await clearOutbox();
    showPWASnackbar(_('All pending posts deleted'));
  } else {
    const id = parseInt(val, 10);
    if (!id) return;
    await removeFromOutbox(id);
    showPWASnackbar(_('Post deleted'));
  }
  await updateOutboxBadge();
  await renderOutboxGhostCards();
  if (typeof renderListOutboxGhostItems === 'function') {
    await renderListOutboxGhostItems();
  }
}

async function deleteAllGhostCards() {
  const count = await getOutboxCount();
  if (count === 0) {
    showPWASnackbar(_('No pending posts'));
    return;
  }
  document.getElementById('input-delete-ghostcard-id').value = 'all';
  callUi('#dialog-delete-ghostcard');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Listen for SW messages
let _syncReloadTimer = null;

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    const { type, data } = event.data || {};

    if (type === 'OUTBOX_ITEM_SYNCED') {
      showPWASnackbar(
        _('Item synced') +
        ': ' + (data.title || '')
      );
      // Seite nach kurzer Verzögerung neu laden, um gesynkte Items korrekt zu rendern
      clearTimeout(_syncReloadTimer);
      _syncReloadTimer = setTimeout(() => window.location.reload(), 2000);
    }

    if (type === 'PRELOAD_COMPLETE') {
      // Nur bei manuellem Trigger benachrichtigen (Flag wird in settings.js gesetzt)
      if (window._pwaPreloadManual) {
        window._pwaPreloadManual = false;
        showPWASnackbar(
          _('All content cached for offline use') +
          ' (' + (data.count || 0) + ')'
        );
      }
    }

    if (type === 'CACHE_URLS_DONE') {
      // Download eines gepinnten Items abgeschlossen — mindestens 1s Sync-Icon zeigen
      const elapsed = Date.now() - (window._pinStartTime || 0);
      const minDelay = Math.max(0, 1000 - elapsed);
      setTimeout(() => {
        const itemId = String(data.itemId);
        const pinState = JSON.parse(localStorage.getItem('pwa_pinned_items') || '{}');
        if (pinState[itemId] === 'pending') {
          if (data.cached > 0) {
            // Tatsächlich gecacht — als fertig markieren
            pinState[itemId] = 'cached';
            localStorage.setItem('pwa_pinned_items', JSON.stringify(pinState));
            const btn = document.querySelector('.pwa-pin-btn[data-item-id="' + itemId + '"]');
            if (btn) {
              const icon = btn.querySelector('i');
              if (icon) icon.textContent = 'download_done';
            }
            showPWASnackbar(_('Item saved for offline'));
          } else {
            // Nichts gecacht (offline/Netzwerkfehler) — pending lassen
            const btn = document.querySelector('.pwa-pin-btn[data-item-id="' + itemId + '"]');
            if (btn) {
              const icon = btn.querySelector('i');
              if (icon) icon.textContent = 'sync';
            }
            showPWASnackbar(_('Download starts when online'));
          }
        }
      }, minDelay);
    }

    if (type === 'OUTBOX_COUNT') {
      const badge = document.getElementById('pwa-outbox-badge');
      if (badge) {
        if (data.count > 0) {
          badge.textContent = data.count;
          badge.style.display = '';
        } else {
          badge.style.display = 'none';
        }
      }
    }
  });
}

// ===== Force Sync =====

async function forceSync() {
  if (!navigator.onLine) {
    showPWASnackbar(_('You are offline'));
    return;
  }
  showPWASnackbar(_('Items are being synced...'));
  document.body.classList.add('pwa-syncing');
  try {
    await fallbackSyncForce();
  } catch (e) {
    showPWASnackbar('Sync error: ' + String(e));
  } finally {
    document.body.classList.remove('pwa-syncing');
  }
}

// ===== Fallback Sync (Safari/Firefox) =====

async function fallbackSync() {
  if (!navigator.onLine) return;
  // Only run if Background Sync is not supported
  if ('serviceWorker' in navigator && 'SyncManager' in window) return;
  await fallbackSyncForce();
}

async function fallbackSyncForce() {
  if (!navigator.onLine) return;
  if (window._syncInProgress) return;
  window._syncInProgress = true;
  try { await _doSync(); } finally { window._syncInProgress = false; }
}

async function _doSync() {
  // Stuck items zurücksetzen (z.B. 'syncing' von fehlgeschlagenem Versuch)
  const allItems = await getOutboxItems();
  for (const item of allItems) {
    if (item.status === 'syncing') {
      await updateOutboxItemStatus(item.id, 'pending');
    }
  }
  const items = await getOutboxItems();
  let syncedCount = 0;
  for (const item of items) {
    if (item.status !== 'pending') continue;

    try {
      await updateOutboxItemStatus(item.id, 'client-syncing');

      // Upload files
      const uploadedUrls = [];
      if (item.files && item.files.length > 0) {
        for (const file of item.files) {
          const formData = new FormData();
          formData.append('file', new Blob([file.data], { type: file.type }), file.name);
          const response = await fetch('/api/v2/upload', { method: 'POST', body: formData });
          if (!response.ok) throw new Error('Upload failed');
          const result = await response.json();
          if (result.status !== 'success') throw new Error(result.message);
          uploadedUrls.push(result.data.filename);
        }
      }

      // Create item
      const formData = new FormData();
      formData.append('title', item.title);
      formData.append('content', item.content);
      formData.append('contentType', item.contentType);
      formData.append('listType', item.listType);
      formData.append('contentURL', uploadedUrls.join(';') || item.contentURL || '');
      formData.append('dateCreated', item.dateCreated);
      formData.append('edition', item.edition || 'all');

      const response = await fetch('/api/v2/items', { method: 'POST', body: formData });
      if (!response.ok) throw new Error('Create failed');
      const result = await response.json();
      if (result.status !== 'success') throw new Error(result.message);

      await removeFromOutbox(item.id);
      syncedCount++;
      showPWASnackbar(
        _('Item synced') +
        ': ' + (item.title || '')
      );
    } catch (err) {
      showPWASnackbar('Sync failed: ' + String(err));
      await updateOutboxItemStatus(item.id, 'pending');
    }
  }

  if (syncedCount === 0 && items.filter(i => i.status === 'pending').length > 0) {
    showPWASnackbar(_('Sync failed. Try again later.'));
  }

  updateOutboxBadge();
  renderOutboxGhostCards();

  // Seite neu laden wenn Items gesynct wurden, damit sie korrekt gerendert werden
  if (syncedCount > 0) {
    setTimeout(() => window.location.reload(), 2000);
  }
}

// ===== WiFi Detection =====

function isOnWifi() {
  if (navigator.connection) {
    return navigator.connection.type === 'wifi' || navigator.connection.type === 'ethernet';
  }
  // Fallback: assume WiFi if we can't detect
  return true;
}

// ===== Settings to SW Communication =====

function syncPwaSettingsToSW(settings) {
  if (navigator.serviceWorker && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: 'PWA_SETTINGS',
      data: settings,
    });
  }
}

// ===== Auto-Cache =====

function autoCacheCurrentPage() {
  // Cache the current page's media URLs
  const images = document.querySelectorAll('#div-render-home-items img[src*="/api/v2/media/"]');
  const videos = document.querySelectorAll('#div-render-home-items video source[src*="/api/v2/media/"]');
  const urls = [];
  images.forEach((img) => urls.push(img.src));
  videos.forEach((vid) => urls.push(vid.src));

  if (urls.length > 0 && navigator.serviceWorker && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: 'CACHE_URLS',
      data: { urls: urls, cacheName: 'media-v1' },
    });
  }
}

// ===== Preload All =====

function preloadAllMedia(mediaUrls) {
  if (navigator.serviceWorker && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({
      type: 'PRELOAD_ALL',
      data: { urls: mediaUrls },
    });
  }
}

// Fetch all media URLs from API and cache them
async function preloadAllContent() {
  if (!navigator.onLine) return;
  // Abbrechen wenn Cache zwischenzeitlich geleert wurde
  if (localStorage.getItem('pwa_offline_all') !== 'true') return;
  try {
    const response = await fetch('/api/v2/all-media-urls');
    if (!response.ok) return;
    // Nochmal prüfen ob zwischenzeitlich deaktiviert
    if (localStorage.getItem('pwa_offline_all') !== 'true') return;
    const result = await response.json();
    if (result.status === 'success' && result.data.urls.length > 0) {
      const reg = await navigator.serviceWorker.ready;
      if (navigator.serviceWorker.controller) {
        navigator.serviceWorker.controller.postMessage({
          type: 'PRELOAD_ALL',
          data: { urls: result.data.urls },
        });
      }
    }
  } catch (e) {
    // Silently fail
  }
}

// ===== Snackbar Helper =====

function showPWASnackbar(message) {
  // Try to use the page's snackbar system
  const snackbarIds = ['home-snackbar', 'settings-snackbar', 'navbar-snackbar'];
  for (const id of snackbarIds) {
    const el = document.getElementById(id);
    if (el) {
      const textEl = document.getElementById(id + '-text') || document.getElementById(id.replace('-snackbar', '-snackbar-text'));
      if (textEl) {
        textEl.textContent = message;
        el.classList.add('active');
        setTimeout(() => el.classList.remove('active'), 4000);
        return;
      }
    }
  }

  // Fallback: create a simple snackbar
  let snackbar = document.getElementById('pwa-snackbar');
  if (!snackbar) {
    snackbar = document.createElement('div');
    snackbar.id = 'pwa-snackbar';
    snackbar.className = 'snackbar';
    snackbar.innerHTML = '<span class="max" id="pwa-snackbar-text"></span>';
    document.body.appendChild(snackbar);
  }
  document.getElementById('pwa-snackbar-text').textContent = message;
  snackbar.classList.add('active');
  setTimeout(() => snackbar.classList.remove('active'), 4000);
}

// ===== Cache All Pages =====

function cacheAllPages() {
  if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return;
  if (!navigator.onLine) return;

  const pageUrls = new Set();
  pageUrls.add('/home');
  pageUrls.add('/settings');
  pageUrls.add('/user-settings');
  pageUrls.add(window.location.pathname);

  // Alle internen Links aus Nav-Drawer und Header extrahieren
  document.querySelectorAll('#dialog-nav-drawer a[href], header a[href]').forEach((a) => {
    const href = a.getAttribute('href');
    if (href && href.startsWith('/') && !href.startsWith('/api/') && !href.startsWith('/static/') && href !== '/logout') {
      pageUrls.add(href);
    }
  });

  navigator.serviceWorker.controller.postMessage({
    type: 'CACHE_URLS',
    data: { urls: Array.from(pageUrls), cacheName: 'api-v2' },
  });
}

// ===== Cache Auth JS Files =====

function cacheAuthJSFiles() {
  if (!navigator.serviceWorker || !navigator.serviceWorker.controller) return;
  if (!navigator.onLine) return;

  navigator.serviceWorker.controller.postMessage({
    type: 'CACHE_URLS',
    data: {
      urls: [
        '/static/js/main.js',
        '/static/js/home.js',
        '/static/js/list.js',
        '/static/js/settings.js',
        '/static/js/timeline.js',
        '/static/js/admin.js',
        '/static/js/nav-drawer.js',
        '/static/js/setup.js',
      ],
      cacheName: 'app-shell-v11',
    },
  });
}

// ===== Init on page load =====

document.addEventListener('DOMContentLoaded', () => {
  // Konnektivität prüfen
  if (!navigator.onLine) {
    goOffline();
  } else {
    fetch('/manifest.json', { method: 'HEAD', cache: 'no-store' })
      .catch(() => goOffline());
  }

  initPinButtons();
  updateOutboxBadge();
  renderOutboxGhostCards();

  // Auth-geschützte JS-Dateien proaktiv cachen
  setTimeout(cacheAuthJSFiles, 1000);

  // Alle Seiten automatisch cachen
  setTimeout(cacheAllPages, 2000);

  // Auto-cache media on current page after a short delay
  setTimeout(autoCacheCurrentPage, 3000);

  // If "save all offline" is enabled, preload all content
  if (navigator.onLine && localStorage.getItem('pwa_offline_all') === 'true') {
    setTimeout(preloadAllContent, 5000);
  }

  // Fallback sync on load
  if (navigator.onLine) {
    setTimeout(fallbackSync, 2000);
  }

  // Event Delegation für Force Sync (Ghost Cards + Outbox Badge)
  document.addEventListener('click', (e) => {
    if (e.target.closest('.outbox-ghost-card a') || e.target.closest('#pwa-outbox-badge')) {
      e.preventDefault();
      forceSync();
    }
  });
});
