// IndexedDB Manager for SharedMoments PWA
const IDB_NAME = 'SharedMomentsOffline';
const IDB_VERSION = 1;

function openIDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(IDB_NAME, IDB_VERSION);
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

function idbGet(store, key) {
  return new Promise((resolve, reject) => {
    const req = store.get(key);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbGetAll(store) {
  return new Promise((resolve, reject) => {
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// ===== Pinned Items =====

async function pinItem(itemId, mediaUrls, title) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pinnedItems', 'readwrite');
    tx.objectStore('pinnedItems').put({
      id: itemId,
      mediaUrls: mediaUrls,
      title: title || '',
      pinnedAt: Date.now(),
    });
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function unpinItem(itemId) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pinnedItems', 'readwrite');
    tx.objectStore('pinnedItems').delete(itemId);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function isPinned(itemId) {
  const db = await openIDB();
  const tx = db.transaction('pinnedItems', 'readonly');
  const result = await idbGet(tx.objectStore('pinnedItems'), itemId);
  return !!result;
}

async function getAllPinnedItems() {
  const db = await openIDB();
  const tx = db.transaction('pinnedItems', 'readonly');
  return idbGetAll(tx.objectStore('pinnedItems'));
}

// ===== Outbox =====

async function addToOutbox(item) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    const entry = {
      ...item,
      status: 'pending',
      createdAt: Date.now(),
    };
    const req = tx.objectStore('outbox').add(entry);
    req.onsuccess = () => resolve(req.result); // returns the auto-incremented id
    tx.onerror = () => reject(tx.error);
  });
}

async function getOutboxItems() {
  const db = await openIDB();
  const tx = db.transaction('outbox', 'readonly');
  return idbGetAll(tx.objectStore('outbox'));
}

async function updateOutboxItemStatus(id, status) {
  const db = await openIDB();
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

async function removeFromOutbox(id) {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function clearOutbox() {
  const db = await openIDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function getOutboxCount() {
  const items = await getOutboxItems();
  return items.filter((i) => i.status === 'pending').length;
}
