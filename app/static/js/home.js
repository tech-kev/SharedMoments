

// Style-Regel einmalig injizieren: überschreibt BeerCSS block-size permanent
(function() {
   const s = document.createElement('style');
   s.textContent = `.field.textarea.auto-grow { block-size: auto !important; min-block-size: 5.5rem; }`;
   document.head.appendChild(s);
})();

// Textarea auto-resize (wächst UND schrumpft, Parent-Container passt mit)
function autoResizeTextarea(el) {
   const field = el.closest('.field');
   if (field) field.classList.add('auto-grow');

   el.style.overflow = 'hidden';
   el.style.height = 'auto';
   el.style.height = el.scrollHeight + 'px';
}

// Shimmer-Animation für AI-Generierung
function addAIShimmer(textarea) {
   if (!document.getElementById('ai-shimmer-style')) {
      const style = document.createElement('style');
      style.id = 'ai-shimmer-style';
      style.textContent = `
         @keyframes ai-glow {
            0%   { border-color: #8b5cf6; box-shadow: 0 0 8px #8b5cf680; }
            25%  { border-color: #6366f1; box-shadow: 0 0 12px #6366f180; }
            50%  { border-color: #ec4899; box-shadow: 0 0 8px #ec489980; }
            75%  { border-color: #8b5cf6; box-shadow: 0 0 12px #8b5cf680; }
            100% { border-color: #8b5cf6; box-shadow: 0 0 8px #8b5cf680; }
         }
         .ai-generating {
            animation: ai-glow 2s ease-in-out infinite !important;
            border-width: 2px !important;
            border-style: solid !important;
            border-radius: inherit;
         }
      `;
      document.head.appendChild(style);
   }
   textarea.closest('.field').classList.add('ai-generating');
}

function removeAIShimmer(textarea) {
   const field = textarea.closest('.field');
   field.classList.remove('ai-generating');
   field.style.borderColor = '';
   field.style.boxShadow = '';
}

// Gespeicherte Originaltexte für Undo
let aiOriginalTexts = {};

function undoAI(mode) {
   const textareaId = mode === 'create' ? 'textarea-create-home-item-content' : 'edit-home-item-content';
   const textarea = document.getElementById(textareaId);
   if (!textarea || !aiOriginalTexts[mode]) return;

   textarea.value = aiOriginalTexts[mode];
   autoResizeTextarea(textarea);
   delete aiOriginalTexts[mode];

   // Undo/Redo-Buttons ausblenden
   const undoBtn = document.getElementById('btn-ai-undo-' + mode);
   const redoBtn = document.getElementById('btn-ai-redo-' + mode);
   if (undoBtn) undoBtn.style.display = 'none';
   if (redoBtn) redoBtn.style.display = 'none';
}

// KI-Textassistent: Stichpunkte in Fließtext umwandeln
async function enhanceWithAI(mode) {
   if (!navigator.onLine) {
      showSnackbar('home', true, 'error', _('You are offline'), null, false);
      return;
   }
   const textareaId = mode === 'create' ? 'textarea-create-home-item-content' : 'edit-home-item-content';
   const titleId = mode === 'create' ? 'div-create-home-item-title' : 'edit-home-item-title';
   const enhanceBtn = document.getElementById('btn-ai-enhance-' + mode);
   const undoBtn = document.getElementById('btn-ai-undo-' + mode);
   const redoBtn = document.getElementById('btn-ai-redo-' + mode);
   const textarea = document.getElementById(textareaId);
   const titleInput = document.getElementById(titleId);

   if (!textarea || !enhanceBtn) return;

   const originalText = textarea.value.trim();
   if (!originalText) {
      showSnackbar('home', true, 'error', _('Please enter some text first'), null, false);
      return;
   }

   // Original-Text speichern (für Undo), ggf. existierenden Originaltext beibehalten bei Regenerate
   if (!aiOriginalTexts[mode]) {
      aiOriginalTexts[mode] = originalText;
   }

   // UI: Shimmer + Buttons deaktivieren
   const icon = enhanceBtn.querySelector('i');
   icon.textContent = 'hourglass_top';
   enhanceBtn.disabled = true;
   if (redoBtn) redoBtn.disabled = true;
   if (undoBtn) undoBtn.disabled = true;
   textarea.disabled = true;
   textarea.value = '';
   textarea.style.height = '';
   addAIShimmer(textarea);

   // Titel für mehr Kontext mitsenden
   const title = titleInput ? titleInput.value.trim() : '';
   let textToSend = aiOriginalTexts[mode];
   if (title) {
      textToSend = 'Title: ' + title + '\n\n' + aiOriginalTexts[mode];
   }

   const formData = new FormData();
   formData.append('text', textToSend);

   try {
      const response = await fetch('/api/v2/ai/enhance', {
         method: 'POST',
         body: formData,
      });

      if (!response.ok) {
         throw new Error(_('Server not reachable'));
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
         const { done, value } = await reader.read();
         if (done) break;

         buffer += decoder.decode(value, { stream: true });
         const lines = buffer.split('\n');
         buffer = lines.pop();

         for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const data = line.slice(6);

            if (data === '[DONE]') break;

            if (data.startsWith('Error: ')) {
               throw new Error(data);
            }

            textarea.value += data;
            autoResizeTextarea(textarea);
         }
      }

      // Erfolgreich: Undo + Regenerate Buttons anzeigen
      if (undoBtn) undoBtn.style.display = '';
      if (redoBtn) redoBtn.style.display = '';

   } catch (error) {
      textarea.value = aiOriginalTexts[mode] || originalText;
      autoResizeTextarea(textarea);
      delete aiOriginalTexts[mode];
      if (undoBtn) undoBtn.style.display = 'none';
      if (redoBtn) redoBtn.style.display = 'none';
      showSnackbar('home', true, 'error', String(error.message || error), null, false);
   } finally {
      removeAIShimmer(textarea);
      icon.textContent = 'auto_awesome';
      enhanceBtn.disabled = false;
      if (redoBtn) redoBtn.disabled = false;
      if (undoBtn) undoBtn.disabled = false;
      textarea.disabled = false;
      autoResizeTextarea(textarea);
   }
}

function getFileContentType (dataUrl=null, filename=null) {

   if (dataUrl) {
      // Den Präfix extrahieren, der den MIME-Typ enthält
      const mimeType = dataUrl.substring(5, dataUrl.indexOf(';'));

      if (mimeType.startsWith('image/')) {
         return 'image';
      } else if (mimeType.startsWith('video/')) {
         if (mimeType === 'video/quicktime') {
            return 'video-mov';
        } else {
            return 'video';
        }

      } else {
         return mimeType;
      }
   } else if (filename) {
      const extension = filename.split('.').pop();
      if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension)) {
         return 'image';
      } else if (['mp4', 'webm', 'mov'].includes(extension)) {
         if (extension === 'mov') {
            return 'video-mov';
         } else {
            return 'video';
         }
      } else {
         return 'unknown';
      }
   } else {
      console.log('Keine Daten oder Dateinamen übergeben');
      return
   }
   

}

let errorOnUpload = false; // Variable zum Speichern eines Fehlers beim Hochladen

// Hilfsfunktion: Home-Item in Outbox speichern
async function saveHomeItemToOutbox() {
   if (typeof addToOutbox !== 'function') return false;
   try {
      const title = document.getElementById("div-create-home-item-title").value;
      const content = document.getElementById("textarea-create-home-item-content").value;
      const listType = document.getElementById("input-list-type").value;
      const dateCreated = document.getElementById("div-create-home-item-date-created").value;
      const allEditionsChecked = document.getElementById("checkbox-create-home-item-all-editions").checked;
      const edition = allEditionsChecked ? 'all' : (window.currentEdition || 'all');

      const files = [];
      for (let i = 0; i < selectedImages.length; i++) {
         const idx = selectedImages[i];
         // Pre-gelesene Buffer verwenden (Mobile-safe)
         if (selectedFileBuffers[idx]) {
            files.push(selectedFileBuffers[idx]);
         } else {
            // Fallback: direkt lesen (Desktop)
            const fileInput = document.getElementById('file-input-create-home-item');
            const file = fileInput.files[idx];
            if (file) {
               try {
                  const buffer = await file.arrayBuffer();
                  files.push({ name: file.name, type: file.type, data: buffer });
               } catch (e) {
                  console.warn('[PWA] Could not read file', idx, e);
               }
            }
         }
      }

      let contentType = 'text';
      if (files.length > 0) {
         const firstFileType = getFileContentType(null, files[0].name);
         if (firstFileType === 'image' && files.length > 1) contentType = 'galleryStartWithImage';
         else if ((firstFileType === 'video' || firstFileType === 'video-mov') && files.length > 1) contentType = 'galleryStartWithVideo';
         else contentType = firstFileType || 'text';
      }

      await addToOutbox({
         title: title, content: content, contentType: contentType,
         listType: listType, dateCreated: dateCreated, edition: edition,
         files: files, contentURL: '',
      });

      callUi("#dialog-create-new-home-item");
      document.getElementById("div-create-home-item-title").value = "";
      document.getElementById("textarea-create-home-item-content").value = "";
      document.getElementById("input-uploaded-urls").value = "";
      document.getElementById("div-create-home-item-date-created").value = "";
      document.getElementById("div-create-home-item-preview-grid").innerHTML = "";
      document.getElementById("file-input-create-home-item").value = "";
      selectedImages = [];
      selectedFileBuffers = [];
      document.getElementById('dialog-create-new-home-item').style.overflow = "auto";

      showSnackbar('home', true, 'green', _('Item saved offline. Will sync when online.'), null, false);
      if (typeof updateOutboxBadge === 'function') updateOutboxBadge();
      if (typeof renderOutboxGhostCards === 'function') renderOutboxGhostCards();
      return true;
   } catch (err) {
      console.error('[PWA] Failed to save to outbox:', err);
      showSnackbar('home', true, 'error', String(err), null, false);
      return false;
   }
}

// Speichern eines neuen Homeitems
async function saveNewHomeItem() {
   // === Offline-Erstellung: Wenn offline, in IndexedDB Outbox speichern ===
   if (!navigator.onLine && typeof addToOutbox === 'function') {
      await saveHomeItemToOutbox();
      return;
   }

   // === Online-Erstellung (Original-Logik) ===
   errorOnUpload = false; // Reset error state
   document.getElementById('dialog-create-new-home-item').style.overflow = "hidden"; // Verhindere das Scrollen im Modal

   if (document.getElementById('file-input-create-home-item').files.length > 0) { // Wenn Bilder ausgewählt sind
      document.getElementById('div-overlay-new-home-item').classList.add('active');
      document.getElementById('progress-new-home-item').style.display = "";
      document.getElementById('headline-article-new-home-item').textContent = _('Upload Files...');

      errorOnUpload = await uploadImages('create'); // Funktion die alle ausgeählten Bilder hochlädt

      document.getElementById('div-overlay-new-home-item').classList.remove('active');
      document.getElementById('progress-new-home-item').style.display = "none";

      if (errorOnUpload) {
         document.getElementById('dialog-create-new-home-item').style.overflow = "auto";
         // Upload fehlgeschlagen (z.B. offline) → in Outbox speichern
         await saveHomeItemToOutbox();
         return;
      }

   }

   var content_urls = document.getElementById("input-uploaded-urls").value.split(";"); // Hole die Urls aus dem Hidden-Input
//   var firstFileExtension = document.getElementById("input-uploaded-urls").value.split(";")[0].split(".").pop(); // Hole die Dateiendung des ersten Bildes

   var contentTypeFirstFile;
   contentTypeFirstFile = getFileContentType(null, content_urls[0]); // Ermittle den ContentType

   var contentType
   if (contentTypeFirstFile === 'image' && content_urls.length > 1) {
      contentType = 'galleryStartWithImage';
   } else if ((contentTypeFirstFile === 'video' || contentTypeFirstFile === 'video-mov') && content_urls.length > 1) {
      contentType = 'galleryStartWithVideo';
   } else {
      contentType = contentTypeFirstFile;
      if (!contentType) { // Wenn kein ContentType ermittelt werden konnte
         contentType = 'text'; // Default value
      }
   }

   var allEditionsChecked = document.getElementById("checkbox-create-home-item-all-editions").checked;
   var edition = allEditionsChecked ? 'all' : (window.currentEdition || 'all');

   var formData = new FormData();
   formData.append("title", document.getElementById("div-create-home-item-title").value);
   formData.append("content", document.getElementById("textarea-create-home-item-content").value);
   formData.append("contentType", contentType);
   formData.append("listType", document.getElementById("input-list-type").value);
   formData.append("contentURL", document.getElementById("input-uploaded-urls").value);
   formData.append("dateCreated", document.getElementById("div-create-home-item-date-created").value);
   formData.append("edition", edition);

   var originalContent = document.getElementById("div-render-home-items").innerHTML;
   showSkeletonCards('div-render-home-items');

   fetch("/api/v2/items", {
      method: "POST",
      body: formData,
   })
      .then(async (response) => {
            try {
               const result = await response.json();
               if (result.status === "success") {
                  document.getElementById("div-render-home-items").innerHTML = result.data.rendered_items; // Neue Items in die Seite einfügen
                  callUi("#dialog-create-new-home-item"); // Modal schließen
                  document.getElementById('dialog-create-new-home-item').style.overflow = "auto"; // Erlaube das Scrollen im Modal
                  addEventListeners(); // Event-Listener neu hinzufügen

                  // Eingabefelder der Modal leeren
                  document.getElementById("div-create-home-item-title").value = "";
                  document.getElementById("textarea-create-home-item-content").value = "";
                  document.getElementById("input-uploaded-urls").value = "";
                  document.getElementById("div-create-home-item-date-created").value = "";
                  document.getElementById("div-create-home-item-preview-grid").innerHTML = "";
                  document.getElementById("file-input-create-home-item").value ="";
                  selectedImages = []; // Leere die ausgewählten Bilder
                  selectedFileBuffers = [];
                  showSnackbar('home', true, 'green', result.message, null, false);
               } else {
                  showSnackbar('home', true, 'error', result.message, result, true);
               }
            } catch (error) { // Kein gültiges JSON
               showSnackbar('home', true, 'error', error, null, false);
            }
      })
      .catch(async (error) => {
         // Skeleton-Cards durch Originalinhalt ersetzen
         document.getElementById("div-render-home-items").innerHTML = originalContent;
         addEventListeners();
         // Offline-Fallback: Bei Netzwerkfehler in Outbox speichern
         if (typeof addToOutbox === 'function') {
            const saved = await saveHomeItemToOutbox();
            if (saved) return;
         }
         if (String(error) === "TypeError: Failed to fetch") {
            error = _('Server not reachable');
         }
         document.getElementById('dialog-create-new-home-item').style.overflow = "auto";
         showSnackbar('home', true, 'error', error, null, false);
   })
}

// Speichern eines bearbeiteten Homeitems
async function saveEditedHomeItem() {
   if (!navigator.onLine) {
      showSnackbar('home', true, 'error', _('You are offline'), null, false);
      return;
   }
   errorOnUpload = false; // Reset error state
   document.getElementById('dialog-edit-home-item').style.overflow = "hidden"; // Verhindere das Scrollen im Modal
   document.getElementById('div-overlay-edit-home-item').classList.add('active');
   document.getElementById('progress-edit-home-item').style.display = "";
   document.getElementById('headline-article-edit-home-item').textContent = _('Upload Files...');

   errorOnUpload = await uploadImages('edit');

   document.getElementById('div-overlay-edit-home-item').classList.remove('active');
   document.getElementById('progress-edit-home-item').style.display = "none";

   if (errorOnUpload) {
      document.getElementById('dialog-edit-home-item').style.overflow = "auto";
      return;
   }

   var content_urls = document.getElementById("input-uploaded-urls").value.split(";");
   //var firstFileExtension = content_urls[0].split(".").pop();

   var contentTypeFirstFile;
   contentTypeFirstFile = getFileContentType(null, content_urls[0]);

   var contentType
   if (contentTypeFirstFile === 'image' && content_urls.length > 1) {
      contentType = 'galleryStartWithImage';
   } else if ((contentTypeFirstFile === 'video' || contentTypeFirstFile === 'video-mov') && content_urls.length > 1) {
      contentType = 'galleryStartWithVideo';
   } else {
      contentType = contentTypeFirstFile;
      if (!contentType) { // Wenn kein ContentType ermittelt werden konnte
         contentType = 'text'; // Default value
      }
   }

   var allEditionsChecked = document.getElementById("checkbox-edit-home-item-all-editions").checked;
   var edition = allEditionsChecked ? 'all' : (window.currentEdition || 'all');

   const formData = new FormData();
   formData.append("title", document.getElementById("edit-home-item-title").value);
   formData.append("content", document.getElementById("edit-home-item-content").value);
   formData.append("dateCreated", document.getElementById("edit-home-item-date-created").value);
   formData.append("contentType", contentType);
   formData.append("listType", document.getElementById("input-list-type").value);
   formData.append("contentURL", document.getElementById("input-uploaded-urls").value);
   formData.append("edition", edition);

   selectedArticles = selectedArticles.map((id) => id.replace("article_", "")); // Entferne "article_" aus der ID, um diese im nächsten Schritt zu verwenden

   var originalEditContent = document.getElementById("div-render-home-items").innerHTML;
   showSkeletonCards('div-render-home-items');

   fetch("/api/v2/item/" + selectedArticles, {
      method: "PUT",
      body: formData,
   })
      .then(async (response) => {
         try {
            const result = await response.json();
            if (result.status === "success") {
               selectItemsStopped(); //footer-bottom-bar-home-items ausblenden
               callUi("#dialog-edit-home-item"); // Modal schließen
               document.getElementById('div-overlay-edit-home-item').classList.remove('active');
               document.getElementById("div-render-home-items").innerHTML = result.data.rendered_items; // Neue Items in die Seite einfügen
               document.getElementById('dialog-edit-home-item').style.overflow = "auto"; // Erlaube das Scrollen im Modal
               addEventListeners(); // Event-Listener neu hinzufügen
               selectedArticles = []; // Leere die ausgewählten Artikel
               selectedImages = []; // Leere die ausgewählten Bilder
               selectedFileBuffers = [];
               showSnackbar('home', true, 'green', result.message, null, false);
            } else {
               showSnackbar('home', true, 'error', result.message, result, true);
            }
         } catch (error) { // Kein gültiges JSON
            showSnackbar('home', true, 'error', error, null, false);
         }
      })
      .catch((error) => { // Fehler beim Fetchen ggf. Server nicht erreichbar
         document.getElementById("div-render-home-items").innerHTML = originalEditContent;
         addEventListeners();
         if (error == "TypeError: Failed to fetch") {
            error = _('Server not reachable');
         }
         document.getElementById('div-overlay-edit-home-item').classList.remove('active');
         document.getElementById('dialog-edit-home-item').style.overflow = "auto";
         showSnackbar('home', true, 'error', error, null, false);
      });
}

// Löschen eines oder mehrerer Homeitems
async function deleteHomeItems() {
   if (!navigator.onLine) {
      showSnackbar('home', true, 'error', _('You are offline'), null, false);
      return;
   }

   if (!confirm(_('Delete selected items?'))) {
      return;
   }

   var formData = new FormData();
   formData.append("ids", selectedArticles.map((id) => id.replace("article_", "")));
   formData.append("listType", document.getElementById("input-list-type").value);

   var originalDeleteContent = document.getElementById("div-render-home-items").innerHTML;
   showSkeletonCards('div-render-home-items');

   fetch("/api/v2/items", {
      method: "DELETE",
      body: formData,
   })
      .then(async (response) => {
         try {
            const result = await response.json();
            if (result.status === "success") {
               document.getElementById("div-render-home-items").innerHTML = result.data.rendered_items; // Neue Items in die Seite einfügen
               selectItemsStopped(); //footer-bottom-bar-home-items ausblenden
               addEventListeners(); // Event-Listener neu hinzufügen
               selectedArticles = []; // Leere die ausgewählten Artikel
               showSnackbar('home', true, 'green', result.message, null, false);
            } else {
               showSnackbar('home', true, 'error', result.message, result, true);
            }
         } catch (error) { // Kein gültiges JSON
            showSnackbar('home', true, 'error', error, null, false);
         }
      })
      .catch((error) => { // Fehler beim Fetchen ggf. Server nicht erreichbar
         document.getElementById("div-render-home-items").innerHTML = originalDeleteContent;
         addEventListeners();
         if (error == "TypeError: Failed to fetch") {
            error = _('Server not reachable');
         }
         showSnackbar('home', true, 'error', error, null, false);
      });
}

// Laden eines zu bearbeitenden Homeitems
function getHomeItem(selectedArticles) {
   if (!navigator.onLine) {
      showSnackbar('home', true, 'error', _('You are offline'), null, false);
      return;
   }

   selectedArticles = selectedArticles.map((id) => id.replace("article_", "")); // Entferne "article_" aus der ID, um diese im nächsten Schritt zu verwenden

   fetch("/api/v2/item/" + selectedArticles, {
      method: "GET",
   })
      .then(async (response) => {
         try {
            const result = await response.json();
            if (result.status === "success") {
               document.getElementById("div-render-edit-home-items").innerHTML = result.data.renderd_item; // Edit-dialog mit dem Item füllen
               generatePreviewForFileInput(null, "edit"); // Vorschau für die Bilder generieren
               callUi("#dialog-edit-home-item"); // Edit-dialog anzeigen
            } else {
               showSnackbar('home', true, 'error', result.message, result, true);
            }
         } catch (error) { // Kein gültiges JSON
            showSnackbar('home', true, 'error', error, null, false);
         }
      })
      .catch((error) => { // Fehler beim Fetchen ggf. Server nicht erreichbar
         if (error == "TypeError: Failed to fetch") {
            error = _('Server not reachable');
         }
         showSnackbar('home', true, 'error', error, null, false);
      });
}

// Globale Variable für die Reihenfolge der ausgewählten Bilder
let selectedImages = [];
let selectedFileBuffers = []; // Pre-read file data for offline support

// Funktion zum Generieren der Vorschau für das File-Input
async function generatePreviewForFileInput(event, mode) {
   let previewGrid;
   let files = [];

   if (mode === "create" && event) {
      files = event.target.files;
      document.getElementById('dialog-create-new-home-item').style.overflow = "hidden"; // Verhindere das Scrollen im Modal
      previewGrid = document.getElementById("div-create-home-item-preview-grid");
      document.getElementById('div-overlay-new-home-item').classList.add('active');
      document.getElementById('progress-new-home-item').style.display = "";
      document.getElementById('headline-article-new-home-item').textContent = _('Render preview images...');
   } else if (mode === "edit" && event) {
      files = event.target.files;
      document.getElementById('dialog-edit-home-item').style.overflow = "hidden"; // Verhindere das Scrollen im Modal
      previewGrid = document.getElementById("div-edit-home-item-preview-grid");
      document.getElementById('div-overlay-edit-home-item').classList.add('active');
      document.getElementById('progress-edit-home-item').style.display = "";
      document.getElementById('headline-article-edit-home-item').textContent = _('Render preview images...');
   } else if (mode === "edit") {
      const urls = document.getElementById("input-hidden-edit-item-contentURLs").value.split(";");
      if (urls[0] === "") {
         return; // Wenn keine URLs vorhanden sind, breche ab
      }
      files = urls.map((url, index) => ({ url: url, index: index }));
      document.getElementById('dialog-edit-home-item').style.overflow = "hidden"; // Verhindere das Scrollen im Modal
      previewGrid = document.getElementById("div-edit-home-item-preview-grid");
      document.getElementById('div-overlay-edit-home-item').classList.add('active');
      document.getElementById('progress-edit-home-item').style.display = "";
      document.getElementById('headline-article-edit-home-item').textContent = _('Render preview images...');
   }
   
   selectedImages = selectedImages || []; // Stelle sicher, dass selectedImages definiert ist

   let containerDiv = previewGrid.querySelector('.s12');
   if (!containerDiv) {
      containerDiv = document.createElement("div");
      containerDiv.className = "s12";
      previewGrid.appendChild(containerDiv);
   }

   const existingImagesCount = containerDiv.querySelectorAll('.preview-image-container').length;

   // Reset file buffers bei neuer Auswahl im Create-Modus
   if (mode === "create" && event && existingImagesCount === 0) {
      selectedFileBuffers = [];
   }

   for (let i = 0; i < files.length; i++) {
      const newIndex = existingImagesCount + i;
      if (mode === "create" && event) {
         renderFile(files[i], newIndex, containerDiv);
         // File sofort lesen damit die Referenz nicht verloren geht (Mobile)
         try {
            const buffer = await files[i].arrayBuffer();
            selectedFileBuffers[newIndex] = { name: files[i].name, type: files[i].type, data: buffer };
         } catch (e) {
            console.warn('[PWA] Could not pre-read file', i, e);
         }
         document.getElementById('progress-new-home-item').value = i / files.length * 100;
         document.getElementById('span-progress-file-new-home-item').textContent = i + 1;
         document.getElementById('span-progress-file-new-home-item-count').textContent = files.length;
      } else if (mode === "edit" && event) {
         renderFile(files[i], newIndex, containerDiv);
         document.getElementById('progress-edit-home-item').value = i / files.length * 100;
         document.getElementById('span-progress-file-edit-home-item').textContent = i + 1;
         document.getElementById('span-progress-file-edit-home-item-count').textContent = files.length;
      } else if (mode === "edit") {
         renderImageFromURL(files[i], containerDiv);
         document.getElementById('progress-edit-home-item').value = i / files.length * 100;
         document.getElementById('span-progress-file-edit-home-item').textContent = i + 1;
         document.getElementById('span-progress-file-edit-home-item-count').textContent = files.length;
      } else {
         console.error("Error while generating preview for file input");
      }
      // Auto-select the image
      selectedImages.push(newIndex);
      await new Promise(r => requestAnimationFrame(r)); // Warte auf nächsten Frame für UI-Update
   }

   // Nach dem Rendern: Chips und Styles für auto-selektierte Bilder setzen
   await new Promise(r => setTimeout(r, 100)); // Kurz warten damit alle async Previews (Videos) geladen sind
   selectedImages.forEach((imgIndex, position) => {
      const targetContainer = findContainerByIndex(previewGrid, imgIndex);
      if (targetContainer) {
         const chip = targetContainer.querySelector('.image-chip');
         const img = targetContainer.querySelector('.preview-image');
         if (chip) {
            chip.textContent = position + 1;
            chip.style.display = '';
         }
         if (img) {
            img.style.border = '2px solid var(--primary)';
         }
      }
   });

   // Hinweis anzeigen, wenn mehr als 1 Bild
   let hint = previewGrid.querySelector('.reorder-hint');
   if (files.length > 1 && !hint) {
      hint = document.createElement('p');
      hint.className = 'reorder-hint small-text';
      hint.style.cssText = 'text-align: center; opacity: 0.7; margin-top: 8px;';
      hint.innerHTML = '<i style="font-size: 14px; vertical-align: middle;">touch_app</i> ' + _('Click images to change the order');
      previewGrid.appendChild(hint);
   }

   if (mode === "create") {
      document.getElementById('dialog-create-new-home-item').style.overflow = "auto"; // Erlaube das Scrollen im Modal
      document.getElementById('div-overlay-new-home-item').classList.remove('active');
      document.getElementById('progress-new-home-item').style.display = "none";
   } else if (mode === "edit") {
      document.getElementById('dialog-edit-home-item').style.overflow = "auto"; // Erlaube das Scrollen im Modal
      document.getElementById('div-overlay-edit-home-item').classList.remove('active');
      document.getElementById('progress-edit-home-item').style.display = "none";
   }
}


// Funktion zum Rendern eines Bildes aus einer Datei
function renderFile(file, index, containerDiv) {
   const reader = new FileReader(); // Erstelle einen neuen FileReader

   reader.onload = function (e) {
       createPreview(e.target.result, index, containerDiv, 'create');
   };

   reader.readAsDataURL(file); // Lese die Datei als Data-URL
}

// Funktion zum Rendern eines Bildes aus einer URL
function renderImageFromURL(fileObj, containerDiv) {
   const apiUrl = "/api/v2/media/"
   createPreview(apiUrl+fileObj.url, fileObj.index, containerDiv, 'edit');
}

// Funktion zum Erstellen der Bildvorschau
function createPreview(src, index, containerDiv, mode) {
   // Erstelle einen Container für das Bild/Video-Thumbnail und den Chip
   const container = document.createElement("div");
   container.className = "preview-image-container";
   container.dataset.index = index; // Speichere den Index auch am Container

   // Erstelle den Chip mit dem Wert "1", der die Reihenfolge des Bildes darstellt
   const chip = document.createElement("a");
   chip.className = "chip image-chip no-border secondary small round";
   chip.textContent = "";
   chip.style.display = "none";

   if (mode === "create") {
      var fileType = getFileContentType(src, null);
   } else if (mode === "edit") {
      var fileType = getFileContentType(null, src);
   }

   if (fileType === "image") {
       // Erstelle das Bild
       const img = document.createElement("img");
       img.className = "preview-image";
       img.src = src;
       img.dataset.index = index; // Speichere den Index des Bildes
       img.addEventListener("click", selectImage); // Füge einen Event-Listener hinzu, um das Bild auszuwählen

       // Füge das Bild und den Chip dem Container hinzu
       container.appendChild(img);
       container.appendChild(chip);
   } else if (fileType === "video" || fileType === "video-mov") {
       // Erstelle das unsichtbare Video-Element nur zur Thumbnail-Erstellung
       const video = document.createElement("video");
       video.src = src;
       video.style.display = "none"; // Verstecke das Video-Element

       // Erstelle das Canvas für das Thumbnail
       const canvas = document.createElement("canvas");
       canvas.className = "video-thumbnail";

       // Warte, bis das Video geladen ist
       video.addEventListener('loadeddata', () => {
           // Setze das Video auf 5 Sekunden (oder eine beliebige Zeit)
           video.currentTime = 5;
       });

       // Wenn das Video die gewählte Zeit erreicht hat, erstelle das Thumbnail
       video.addEventListener('seeked', () => {
           const context = canvas.getContext('2d');
           canvas.width = video.videoWidth;
           canvas.height = video.videoHeight;

           // Zeichne den aktuellen Frame auf das Canvas
           context.drawImage(video, 0, 0, canvas.width, canvas.height);

           // Erstelle ein Bild-Element mit dem generierten Thumbnail
           const thumbnailImg = document.createElement('img');
           thumbnailImg.src = canvas.toDataURL(); // Data URL des Thumbnails
           thumbnailImg.className = 'preview-image';
           thumbnailImg.dataset.index = index; // Speichere den Index des Bildes
           thumbnailImg.addEventListener("click", selectImage); // Füge einen Event-Listener hinzu, um das Bild auszuwählen
           container.appendChild(thumbnailImg); // Füge das Thumbnail hinzu
           container.appendChild(chip);
       });

       // Fehlerbehandlung, falls das Video nicht geladen werden kann (MOV-Videos)
         video.addEventListener('error', () => {
            const img = document.createElement("img");
            img.className = "preview-image";
            img.src = '/api/v2/media/static/filenotsupported.png';
            img.dataset.index = index; // Speichere den Index des Bildes
            img.addEventListener("click", selectImage); // Füge einen Event-Listener hinzu, um das Bild auszuwählen

            const tooltip = document.createElement("div");
            tooltip.className = "tooltip max";
            tooltip.textContent = _('Your browser does not support this video format. You can still upload it, but it will only play on supported devices.');

            // Füge das Bild und den Chip dem Container hinzu
            container.appendChild(img);
            container.appendChild(tooltip);
            container.appendChild(chip);
            });

       // Lade das Video, aber füge es nicht dem DOM hinzu
       video.load();
   } else {
      showSnackbar('home', true, 'error', _('Filetype') + ' ' + fileType + ' ' + _('is not supported'), null, false);
   }

   // Füge den Container dem div hinzu
   containerDiv.appendChild(container);
}


// Hilfsfunktion: Finde Container anhand von data-index innerhalb eines Grids
function findContainerByIndex(previewGrid, imgIndex) {
   return previewGrid.querySelector(`.preview-image-container[data-index="${imgIndex}"]`);
}

// Auswahl eines Preview-Bildes handeln
function selectImage(event) {
   const img = event.target;
   const index = parseInt(img.dataset.index, 10); // Stelle sicher, dass der Index als Zahl behandelt wird
   const container = img.parentElement;
   const chip = container.querySelector(".image-chip");

   // Finde das übergeordnete Preview-Grid, um nur Container innerhalb desselben Dialogs zu suchen
   const previewGrid = container.closest('[id$="preview-grid"]');

   console.log(`Bild mit Index ${index} ausgewählt`);

   const existingIndex = selectedImages.indexOf(index);
   if (existingIndex === -1) {
      selectedImages.push(index);
      chip.textContent = selectedImages.length;
      chip.style.display = "";
      img.style.border = "2px solid var(--primary)";
   } else {
      selectedImages.splice(existingIndex, 1);
      chip.style.display = "none";
      img.style.border = "1px solid var(--outline)";

      // Aktualisiere die Reihenfolge der Chips — suche Container per data-index
      selectedImages.forEach((imgIndex, newIndex) => {
         const targetContainer = findContainerByIndex(previewGrid, imgIndex);
         if (targetContainer) {
            const currentChip = targetContainer.querySelector(".image-chip");
            if (currentChip) currentChip.textContent = newIndex + 1;
         }
      });
   }
}

// Funktion zum Hochladen der ausgewählten Bilder
async function uploadImages(mode) {
   let uploadedImages = []; // Liste zum Speichern der hochgeladenen Bilder
   let existingImages = []; // Liste zum Speichern der bereits vorhandenen Bilder
   let fileInputId, hiddenInputId; // Variablen zum Speichern der IDs der File-Inputs

   console.log(`Upload gestartet im ${mode}-Modus`);

   if (mode === "create") { 
       fileInputId = "file-input-create-home-item";
       console.log("Modus ist 'create'. Verwende file-input-create-home-item");
   } else if (mode === "edit") {
       fileInputId = "file-input-edit-home-item";
       hiddenInputId = "input-hidden-edit-item-contentURLs";
       existingImages = document.getElementById(hiddenInputId).value.split(";").filter(Boolean);
       console.log("Modus ist 'edit'. Verwende file-input-edit-home-item und input-hidden-edit-item-contentURLs");
       console.log(`Vorhandene Bilder: ${existingImages}`);
   }

   const fileInput = document.getElementById(fileInputId); // Hole das File-Input-Element
   // Hole Container nur aus dem aktiven Preview-Grid
   const previewGridId = mode === "create" ? "div-create-home-item-preview-grid" : "div-edit-home-item-preview-grid";
   const previewGridEl = document.getElementById(previewGridId);

   console.log(`Anzahl ausgewählter Bilder: ${selectedImages.length}`);

   let i = 0;

   for (const index of selectedImages) { // Schleife über alle ausgewählten Bilder
      i++;
      const targetContainer = findContainerByIndex(previewGridEl, index);
      const imgElement = targetContainer ? targetContainer.querySelector("img") : null; // Hole das Bild-Element
      const file = fileInput.files[index]; // Hole die Datei aus dem File-Input

      console.log(`Verarbeite Bild mit Index ${index}`);

      if (mode === "create") {

         document.getElementById('progress-new-home-item').value = i / selectedImages.length * 100;
         document.getElementById('span-progress-file-new-home-item').textContent = i;
         document.getElementById('span-progress-file-new-home-item-count').textContent = selectedImages.length;

         const formData = new FormData();
         formData.append("file", file);

         try {
            const response = await fetch('/api/v2/upload', {
               method: "POST",
               body: formData,
            });

            const result = await response.json();
            if (result.status === "success") {
               uploadedImages.push(result.data.filename);
               console.log(`Bild mit Index ${index} hochgeladen`);
            } else {
               showSnackbar('home', true, 'error', result.message, result, true);
               errorOnUpload = true;
            }
         } catch (error) {
            if (error == "TypeError: Failed to fetch") {
               error = _('Server not reachable');
            }
            showSnackbar('home', true, 'error', error, null, false);
            errorOnUpload = true;
         }

      } else if (mode === "edit") {
         document.getElementById('progress-edit-home-item').value = i / selectedImages.length * 100;
         document.getElementById('span-progress-file-edit-home-item').textContent = i;
         document.getElementById('span-progress-file-edit-home-item-count').textContent = selectedImages.length;

         if (index < existingImages.length) { // Bild ist bereits vorhanden
            uploadedImages.push(existingImages[index]); // Fügt die bereits vorhandene URL zur Liste hinzu
            console.log(`Bild mit Index ${index} ist bereits vorhanden`);
         } else { // Bild ist neu
            console.log(`Bild mit Index ${index} ist neu`);
      
            const newFileIndex = index - existingImages.length; // Berechne den Index der neuen Datei
            const file = fileInput.files[newFileIndex]; // Hole die Datei aus dem File-Input

            const formData = new FormData();
            formData.append("file", file);

            try {
               const response = await fetch('/api/v2/upload', {
                  method: "POST",
                  body: formData,
               });

               if (response.ok) {
                  const result = await response.json();
                  if (result.status === "success") {
                     uploadedImages.push(result.data.filename); // Fügt die zurückgegebene URL zur Liste hinzu
                     console.log(`Bild mit Index ${index} hochgeladen`);
                  } else {
                     showSnackbar('home', true, 'error', result.message, result, true);
                     errorOnUpload = true;
                  }
               } else {
                  showSnackbar('home', true, 'error', _('Error while uploading') + ': ' + response.statusText, null, false);
                  errorOnUpload = true;
               }
            } catch (error) {
               if (error == "TypeError: Failed to fetch") {
                  error = _('Server not reachable');
               }
               showSnackbar('home', true, 'error', error, null, false);
               errorOnUpload = true;
            }
         }
      }
   }

   // URLs durch Semikolons getrennt speichern
   const finalImageURLs = uploadedImages.join(";");

   console.log(`Finale Bild-URLs: ${finalImageURLs}`);

   // Speichern der URLs in den Hidden-Input
   document.getElementById("input-uploaded-urls").value = finalImageURLs;

   return errorOnUpload;
}

var selectStarted = false; // Variable zum Speichern des Auswahlstatus
let longPressTimer; // Timer-Variable für das lange Drücken

// Starten der Homeitem-Auswahl
function selectItemsStarted(event) {
   if (!window.canSelectItems) return; // Keine Auswahl ohne Edit/Delete-Rechte

   id = event.currentTarget.id; // Hole die ID des Artikels

   if (!selectStarted) {
      longPressTimer = setTimeout(() => { // Starte den Timer für das lange Drücken
         selectStarted = true; // Setze den Auswahlstatus auf true
         handleLongPress(id); // Behandle das lange Drücken
         const createFab = document.getElementById("div-fab-create-new-home-item");
         if (createFab) createFab.style.display = "none"; // Verstecke den FAB
         document.getElementById("footer-bottom-bar-home-items").style.display = ""; // Zeige die Auswahlleiste
      }, 500); // Warte 500ms, bevor das lange Drücken erkannt wird
   } else {
      handleLongPress(id); // Wenn das lange Drücken bereits erkannt wurde, behandle das Drücken -> Auswahl hinzufügen ohne Timer
   }
}

// Beenden der Homeitem-Auswahl
function selectItemsStopped(event) {

   if ((event && event.type === "mouseup") || selectStarted === false) { // Wenn das Event ein "mouseup" ist oder das Auswahl-Event nicht gestartet wurde -> User hat nicht lang genug gedrückt gehalten
      clearTimeout(longPressTimer); // Stoppe den Timer für das lange Drücken
   } else {
      selectStarted = false;
      document.getElementById("footer-bottom-bar-home-items").style.display = "none"; // Verstecke die Auswahlleiste
      const createFab = document.getElementById("div-fab-create-new-home-item");
      if (createFab) createFab.style.display = ""; // Zeige den FAB
   }
}

let selectedArticles = []; // Variable zum Speichern der ausgewählten Artikel-IDs

// Alle Artikel abwählen
function deselectAllItems() {
   selectedArticles.forEach(articleId => {
      const article = document.getElementById(articleId);
      if (article) article.style.border = 'none';
   });
   selectedArticles = [];
   selectItemsStopped();
}

// Behandlung des langen Drückens
function handleLongPress(id) {
   article = document.getElementById(id); // Hole das Artikel-Element
   const articleId = id;

   // Überprüfen, ob der Artikel bereits ausgewählt ist
   const existingIndex = selectedArticles.indexOf(articleId);
   if (existingIndex === -1) {
      // Artikel ist noch nicht ausgewählt
      selectedArticles.push(articleId); // Füge die Artikel-ID hinzu
      article.style.border = "2px solid #007bff"; // Setze den Rahmen des Artikels auf blau //TODO: Farbe in CSS-Klasse auslagern, bzw. von BeerCSS nehmen

      const editFab = document.getElementById("fab-edit-home-item");
      if (selectedArticles.length > 1 && editFab) { // Wenn mehr als ein Artikel ausgewählt ist
          editFab.disabled = true; // Deaktiviere den Edit-FAB
      }
   } else {
      // Artikel ist bereits ausgewählt, entferne ihn aus der Auswahl
      selectedArticles.splice(existingIndex, 1); // Entferne die Artikel-ID aus der Liste
      article.style.border = "none"; // Entferne den Rahmen des Artikels //TODO: Farbe in CSS-Klasse auslagern, bzw. von BeerCSS nehmen und gleichsetzen mit der obigen Auswahl
   }

   if (selectedArticles.length === 0) { // Wenn keine Artikel ausgewählt sind
      selectItemsStopped(); // Beende die Auswahl
   } else if (selectedArticles.length === 1) { // Wenn ein Artikel ausgewählt ist
      const editFab = document.getElementById("fab-edit-home-item");
      if (editFab) editFab.disabled = false; // Aktiviere den Edit-FAB
   }
}

// Variablen zum Speichern des Touch-Status
let touchStartY = 0;
let touchStartX = 0;
let isScrolling = false;

// Funktion zum Start des Touch-Events
function handleTouchStart(event) {
   if (event.touches.length > 0) { // Wenn es mehr als 0 Touches gibt
      const touch = event.touches[0]; // Hole den ersten Touch
      touchStartY = touch.clientY; // Speichere die Y-Position des Touchs
      touchStartX = touch.clientX; // Speichere die X-Position des Touchs
      isScrolling = false; // Setze das Scrollen auf false
   }
}

// Funktion zum Bewegen des Touchs
function handleTouchMove(event) {
   if (event.touches.length > 0) { // Wenn es mehr als 0 Touches gibt
      const touch = event.touches[0]; // Hole den ersten Touch
      const deltaY = Math.abs(touch.clientY - touchStartY); // Berechne die Distanz in der Y-Richtung
      const deltaX = Math.abs(touch.clientX - touchStartX); // Berechne die Distanz in der X-Richtung

      // Wenn die Bewegung signifikant in der Y-Richtung ist, dann scrollen
      if (deltaY > deltaX) {
         isScrolling = true; // Setze das Scrollen auf true
      }
   }
}

// Funktion zum Beenden des Touchs
function handleTouchEnd(event) {
   if (isScrolling) {
      // Scrollen erkannt, keine Auswahl durchführen
   } else {
      // Keine Scroll-Bewegung, daher Auswahl durchführen
      selectItemsStarted(event);
   }
}

// Füge die Event Listener zu allen Artikeln mit der Klasse "home-item" hinzu 
function addEventListeners() {
   document.querySelectorAll(".home-item").forEach((article) => { // Schleife über alle Artikel
      const deviceType = getDeviceType(); // Hole den Gerätetyp

      if (deviceType === "desktop") { // Wenn es sich um ein Desktop-Gerät handelt, Mouse-Events verwenden
         article.addEventListener("mousedown", selectItemsStarted);
         article.addEventListener("mouseup", selectItemsStopped);
      } else { // Ansonsten Touch-Events verwenden
         article.addEventListener("touchstart", handleTouchStart);
         article.addEventListener("touchend", handleTouchEnd);
         article.addEventListener("touchmove", handleTouchMove);
      }
   });
}
addEventListeners(); // Füge die Event Listener zu allen Artikeln hinzu


// ===== Banner Song =====

let bannerAudio = null;

function toggleSong() {
   const btn = document.getElementById('btn-play-song');
   if (!btn) return;
   const icon = btn.querySelector('i');

   if (!bannerAudio) {
      bannerAudio = new Audio(btn.getAttribute('data-song'));
      bannerAudio.addEventListener('ended', () => {
         icon.textContent = 'play_arrow';
      });
   }

   if (bannerAudio.paused) {
      bannerAudio.play();
      icon.textContent = 'pause';
   } else {
      bannerAudio.pause();
      icon.textContent = 'play_arrow';
   }
}

// ===== Share Functions =====

function shareSelectedItems() {
   if (selectedArticles.length !== 1) {
      showSnackbar('home', true, 'error', _('Please select exactly one item to share'), null, false);
      return;
   }

   const itemId = selectedArticles[0].replace('article_', '');
   document.getElementById('input-share-item-id').value = itemId;
   document.getElementById('input-share-expires-at').value = '';
   document.getElementById('input-share-password').value = '';
   document.getElementById('div-share-result').style.display = 'none';
   document.getElementById('btn-create-share').style.display = '';

   document.getElementById('dialog-share-item').classList.add('active');
   document.body.style.overflow = 'hidden';
}

function closeShareDialog() {
   document.getElementById('dialog-share-item').classList.remove('active');
   document.body.style.overflow = 'auto';
}

async function createShareLink() {
   if (!navigator.onLine) {
      showSnackbar('home', true, 'error', _('You are offline'), null, false);
      return;
   }
   const itemId = document.getElementById('input-share-item-id').value;
   const expiresAt = document.getElementById('input-share-expires-at').value;
   const password = document.getElementById('input-share-password').value;

   // Validate expiration date is not in the past
   if (expiresAt) {
      const expiresDate = new Date(expiresAt);
      if (expiresDate <= new Date()) {
         showSnackbar('home', true, 'error', _('Expiration date must be in the future'), null, false);
         return;
      }
   }

   const formData = new FormData();
   if (expiresAt) formData.append('expiresAt', expiresAt);
   if (password) formData.append('password', password);

   try {
      const response = await fetch(`/api/v2/items/${itemId}/share`, {
         method: 'POST',
         body: formData
      });
      const result = await response.json();

      if (result.status === 'success') {
         const fullUrl = window.location.origin + result.data.url;
         document.getElementById('input-share-url').value = fullUrl;
         document.getElementById('div-share-result').style.display = '';
         document.getElementById('btn-create-share').style.display = 'none';

         // Auto-copy to clipboard
         copyShareLink();
      } else {
         showSnackbar('home', true, 'error', result.message, result, true);
      }
   } catch (error) {
      showSnackbar('home', true, 'error', String(error), null, false);
   }
}

function copyShareLink() {
   const urlInput = document.getElementById('input-share-url');
   const text = urlInput.value;
   if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => {
         showSnackbar('home', true, 'green', _('Link copied to clipboard'), null, false);
      });
   } else {
      // Fallback for HTTP / insecure contexts
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showSnackbar('home', true, 'green', _('Link copied to clipboard'), null, false);
   }
}

