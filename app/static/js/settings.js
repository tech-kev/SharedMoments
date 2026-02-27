// --- State ---
// These are set from inline <script> in settings.html:
// relationshipStatuses, supportedLanguages, editions, currentEdition, settingsType

let requiredDateMode = false;
let pendingRequiredDates = [];

// --- Profile Picture ---
function updateProfilePicture(input) {
    if (!input.files || !input.files[0]) return;
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const formData = new FormData();
    formData.append('file', input.files[0]);

    fetch('/api/v2/user/profile-picture', {
        method: 'PUT',
        body: formData,
    })
    .then(res => res.json())
    .then(result => {
        if (result.status === 'success') {
            const newSrc = '/api/v2/media/static/' + result.data.filename;
            document.getElementById('profile-picture-preview').src = newSrc;
            const headerImg = document.getElementById('header-profile-picture');
            if (headerImg) headerImg.src = newSrc;
            showSnackbar('settings', true, 'success', result.message, null, false);
        } else {
            showSnackbar('settings', true, 'error', result.message, result, true);
        }
    })
    .catch(error => {
        if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
        showSnackbar('settings', true, 'error', error, null, false);
    });
}

// --- Edit Dialog ---
function hideAllEditFields() {
    document.getElementById('edit-field-text').style.display = 'none';
    document.getElementById('edit-field-date').style.display = 'none';
    document.getElementById('edit-field-select').style.display = 'none';
    document.getElementById('edit-field-required-hint').style.display = 'none';
}

function closeEditDialogIfAllowed() {
    if (requiredDateMode) return;
    closeEditDialog();
}

function closeEditDialog() {
    requiredDateMode = false;
    pendingRequiredDates = [];
    document.getElementById('cancel-setting').style.display = '';
    callUi('#dialog-edit-settings');
    document.getElementById('save-setting').removeAttribute('onclick');
}

function editSetting(setting, type) {
    hideAllEditFields();

    const labelName = document.getElementById(setting + '-name').textContent;
    document.getElementById('dialog-edit-title').textContent = labelName;

    if (setting === 'relationship_status') {
        const select = document.getElementById('input-edit-setting-select');
        const currentValue = document.getElementById(setting + '-value').getAttribute('data-value')
            || document.getElementById(setting + '-value').textContent.trim();
        select.innerHTML = '';
        relationshipStatuses.forEach(status => {
            const option = document.createElement('option');
            option.value = status.id;
            option.textContent = status.name;
            if (String(status.id) === String(currentValue)) option.selected = true;
            select.appendChild(option);
        });
        document.getElementById('label-edit-setting-select').textContent = labelName;
        document.getElementById('edit-field-select').style.display = '';
        document.getElementById('save-setting').setAttribute('onclick', `saveSettingSelect('${setting}')`);

    } else if (type === 'language') {
        const select = document.getElementById('input-edit-setting-select');
        const currentValue = document.getElementById(setting + '-value').textContent.trim();
        select.innerHTML = '';
        supportedLanguages.forEach(lang => {
            const option = document.createElement('option');
            option.value = lang;
            option.textContent = lang;
            if (lang === currentValue) option.selected = true;
            select.appendChild(option);
        });
        document.getElementById('label-edit-setting-select').textContent = labelName;
        document.getElementById('edit-field-select').style.display = '';
        document.getElementById('save-setting').setAttribute('onclick', `saveSettingSelect('${setting}')`);

    } else if (type === 'date') {
        const currentValue = document.getElementById(setting + '-value').textContent.trim();
        let dateValue = '';
        if (currentValue && currentValue !== '-') {
            const parts = currentValue.split('.');
            if (parts.length === 3) {
                dateValue = `${parts[2]}-${parts[1]}-${parts[0]}`;
            } else {
                dateValue = currentValue;
            }
        }
        document.getElementById('input-edit-setting-date').value = dateValue;
        document.getElementById('label-edit-setting-date').textContent = labelName;
        document.getElementById('edit-field-date').style.display = '';
        document.getElementById('save-setting').setAttribute('onclick', `saveSettingDate('${setting}')`);

    } else {
        const currentValue = document.getElementById(setting + '-value').textContent.trim();
        document.getElementById('input-edit-setting-value').value = currentValue;
        document.getElementById('input-edit-setting-value').setAttribute('type', type || 'text');
        document.getElementById('label-edit-setting-name').textContent = labelName;
        document.getElementById('edit-field-text').style.display = '';
        document.getElementById('save-setting').setAttribute('onclick', `saveSetting('${setting}')`);
    }

    callUi('#dialog-edit-settings');
}

// --- Save Functions ---
function saveSetting(setting) {
    const value = document.getElementById('input-edit-setting-value').value;
    sendSettingUpdate(setting, value);
}

function saveSettingDate(setting) {
    const value = document.getElementById('input-edit-setting-date').value;

    if (requiredDateMode && !value) {
        showSnackbar('settings', true, 'error', _('Please enter a date.'), null, false);
        return;
    }

    if (requiredDateMode) {
        sendSettingUpdateWithCallback(setting, value, function () {
            pendingRequiredDates = pendingRequiredDates.filter(d => d !== setting);
            openNextRequiredDate();
        });
    } else {
        sendSettingUpdate(setting, value);
    }
}

function saveSettingSelect(setting) {
    const value = document.getElementById('input-edit-setting-select').value;
    sendSettingUpdate(setting, value);
}

function sendSettingUpdate(setting, value) {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const formData = new FormData();
    formData.append("setting", setting);
    formData.append("value", value);

    fetch("/api/v2/" + settingsType, {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === "success") {
                    closeEditDialog();

                    if (setting === 'relationship_status') {
                        const status = relationshipStatuses.find(s => String(s.id) === String(result.data.value));
                        const displayEl = document.getElementById(setting + '-value');
                        displayEl.textContent = status ? status.name : result.data.value;
                        displayEl.setAttribute('data-value', result.data.value);
                        checkRequiredDatesAfterStatusSave(result.data.value);
                    } else if (setting === 'title') {
                        document.getElementById(setting + '-value').textContent = result.data.value;
                        document.title = result.data.value;
                        const headerTitle = document.querySelector('header nav a h6');
                        if (headerTitle) headerTitle.textContent = result.data.value;
                    } else {
                        document.getElementById(setting + '-value').textContent = result.data.value;
                    }

                    showSnackbar('settings', true, 'green', result.message, null, false);

                    if (setting === 'language') {
                        location.reload();
                    }
                } else {
                    showSnackbar('settings', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('settings', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (error == "TypeError: Failed to fetch") {
                error = _('Server not reachable');
            }
            showSnackbar('settings', true, 'error', error, null, false);
        });
}

function sendSettingUpdateWithCallback(setting, value, callback) {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const formData = new FormData();
    formData.append("setting", setting);
    formData.append("value", value);

    fetch("/api/v2/" + settingsType, {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === "success") {
                    callUi('#dialog-edit-settings');
                    document.getElementById('save-setting').removeAttribute('onclick');
                    document.getElementById(setting + '-value').textContent = result.data.value;
                    showSnackbar('settings', true, 'green', result.message, null, false);
                    if (callback) callback();
                } else {
                    showSnackbar('settings', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('settings', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
            showSnackbar('settings', true, 'error', error, null, false);
        });
}

// --- Darkmode ---
function toggleDarkmode() {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const toggle = document.getElementById('darkmode-toggle');
    toggle.checked = !toggle.checked;
    const value = toggle.checked ? 'TRUE' : 'FALSE';

    document.body.classList.toggle('dark', toggle.checked);

    const formData = new FormData();
    formData.append("setting", "darkmode");
    formData.append("value", value);

    fetch("/api/v2/user-settings", {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            const result = await response.json();
            if (result.status === "success") {
                showSnackbar('settings', true, 'green', result.message, null, false);
            } else {
                showSnackbar('settings', true, 'error', result.message, result, true);
                toggle.checked = !toggle.checked;
                document.body.classList.toggle('dark', toggle.checked);
            }
        })
        .catch((error) => {
            if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
            showSnackbar('settings', true, 'error', error, null, false);
            toggle.checked = !toggle.checked;
            document.body.classList.toggle('dark', toggle.checked);
        });
}

// --- Share Tracking ---
function toggleShareTracking() {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const toggle = document.getElementById('share-tracking-toggle');
    toggle.checked = !toggle.checked;
    const value = toggle.checked ? 'True' : 'False';

    const formData = new FormData();
    formData.append("setting", "share_tracking");
    formData.append("value", value);

    fetch("/api/v2/settings", {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            const result = await response.json();
            if (result.status === "success") {
                showSnackbar('settings', true, 'green', result.message, null, false);
            } else {
                showSnackbar('settings', true, 'error', result.message, result, true);
                toggle.checked = !toggle.checked;
            }
        })
        .catch((error) => {
            if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
            showSnackbar('settings', true, 'error', error, null, false);
            toggle.checked = !toggle.checked;
        });
}

// --- Edition ---
function editEdition() {
    const select = document.getElementById('input-edition-select');
    select.innerHTML = '';
    editions.forEach(ed => {
        const option = document.createElement('option');
        option.value = ed.id;
        option.textContent = ed.name;
        if (ed.id === currentEdition) option.selected = true;
        select.appendChild(option);
    });
    document.getElementById('edition-info-box').style.display = 'none';
    select.onchange = function () {
        document.getElementById('edition-info-box').style.display = this.value !== currentEdition ? '' : 'none';
    };
    callUi('#dialog-edition-confirm');
}

function closeEditionDialog() {
    callUi('#dialog-edition-confirm');
}

function saveEdition() {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const value = document.getElementById('input-edition-select').value;
    const formData = new FormData();
    formData.append("setting", "sm_edition");
    formData.append("value", value);

    fetch("/api/v2/settings", {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            const result = await response.json();
            if (result.status === "success") {
                closeEditionDialog();
                location.reload();
            } else {
                showSnackbar('settings', true, 'error', result.message, result, true);
            }
        })
        .catch((error) => {
            if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
            showSnackbar('settings', true, 'error', error, null, false);
        });
}

// --- Required Dates after Relationship Status Change ---
const dateRequirements = {
    '1': ['anniversary_date'],
    '2': ['anniversary_date', 'engaged_date'],
    '3': ['wedding_date'],
    '4': ['anniversary_date'],
    '5': ['anniversary_date']
};

function checkRequiredDatesAfterStatusSave(statusValue) {
    const required = dateRequirements[String(statusValue)];
    if (!required) return;

    const missing = [];
    for (const dateSetting of required) {
        const dateEl = document.getElementById(dateSetting + '-value');
        if (dateEl) {
            const dateValue = dateEl.textContent.trim();
            if (!dateValue || dateValue === '-' || dateValue === '') {
                missing.push(dateSetting);
            }
        }
    }

    if (missing.length === 0) return;

    pendingRequiredDates = missing;
    openNextRequiredDate();
}

function openNextRequiredDate() {
    if (pendingRequiredDates.length === 0) {
        requiredDateMode = false;
        document.getElementById('cancel-setting').style.display = '';
        return;
    }

    const dateSetting = pendingRequiredDates[0];
    requiredDateMode = true;

    setTimeout(() => {
        editSetting(dateSetting, 'date');
        document.getElementById('cancel-setting').style.display = 'none';
        const hint = document.getElementById('edit-field-required-hint');
        hint.textContent = _('This date is required for your relationship status.');
        hint.style.display = '';
    }, 500);
}

// --- PWA Settings ---

function togglePwaSetting(settingName) {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const toggle = document.getElementById('pwa-toggle-' + settingName);
    toggle.checked = !toggle.checked;
    const value = toggle.checked ? 'TRUE' : 'FALSE';

    const formData = new FormData();
    formData.append("setting", settingName);
    formData.append("value", value);

    fetch("/api/v2/user-settings", {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            const result = await response.json();
            if (result.status === "success") {
                showSnackbar('settings', true, 'green', result.message, null, false);
                syncAllPwaSettings();
                // If pwa_offline_all was toggled ON, preload all content
                if (settingName === 'pwa_offline_all' && toggle.checked) {
                    localStorage.setItem('pwa_offline_all', 'true');
                    window._pwaPreloadManual = true;
                    if (typeof preloadAllContent === 'function') preloadAllContent();
                } else if (settingName === 'pwa_offline_all' && !toggle.checked) {
                    localStorage.removeItem('pwa_offline_all');
                }
            } else {
                showSnackbar('settings', true, 'error', result.message, result, true);
                toggle.checked = !toggle.checked;
            }
        })
        .catch((error) => {
            if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
            showSnackbar('settings', true, 'error', error, null, false);
            toggle.checked = !toggle.checked;
        });
}

async function forceUpdatePWA() {
    if (!('serviceWorker' in navigator)) {
        showSnackbar('settings', true, 'error', _('Service Worker not supported'), null, false);
        return;
    }
    try {
        const registration = await navigator.serviceWorker.ready;
        showSnackbar('settings', true, 'green', _('Checking for updates...'), null, false);
        await registration.update();

        if (registration.waiting) {
            // Neue Version gefunden — sofort aktivieren
            registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        } else if (registration.installing) {
            // SW wird gerade installiert — auf fertig warten
            registration.installing.addEventListener('statechange', (e) => {
                if (e.target.state === 'installed') {
                    e.target.postMessage({ type: 'SKIP_WAITING' });
                }
            });
        } else {
            showSnackbar('settings', true, 'green', _('App is up to date'), null, false);
        }
    } catch (err) {
        showSnackbar('settings', true, 'error', String(err), null, false);
    }
}

function clearPwaCache() {
    if (typeof clearOfflineCache === 'function') {
        clearOfflineCache().then(() => {
            localStorage.removeItem('pwa_offline_all');
            localStorage.removeItem('pwa_pinned_items');
            // Toggle in UI zurücksetzen
            const toggle = document.getElementById('pwa-toggle-pwa_offline_all');
            if (toggle) toggle.checked = false;
            // Server-Setting auch auf FALSE setzen
            const formData = new FormData();
            formData.append('setting', 'pwa_offline_all');
            formData.append('value', 'FALSE');
            fetch('/api/v2/user-settings', { method: 'PUT', body: formData }).catch(() => {});
            // Pin-Icons aktualisieren
            if (typeof initPinButtons === 'function') initPinButtons();
            // Seiten erneut cachen
            if (typeof cacheAllPages === 'function') cacheAllPages();
            showSnackbar('settings', true, 'green', _('Cache cleared'), null, false);
            updateStorageDisplay();
        });
    }
}

async function updateStorageDisplay() {
    const el = document.getElementById('pwa-storage-usage');
    if (!el) return;
    if (typeof getStorageEstimate === 'function') {
        const estimate = await getStorageEstimate();
        if (estimate) {
            el.textContent = estimate.usageMB + ' MB / ' + estimate.quotaMB + ' MB';
        } else {
            el.textContent = _('Not available');
        }
    }
}

function syncAllPwaSettings() {
    if (typeof syncPwaSettingsToSW !== 'function') return;
    const settings = {};
    const toggleNames = ['pwa_offline_all', 'pwa_wifi_only_upload', 'pwa_preload_on_wifi'];
    toggleNames.forEach(name => {
        const toggle = document.getElementById('pwa-toggle-' + name);
        if (toggle) settings[name] = toggle.checked;
    });
    const numberNames = ['pwa_auto_cache_count', 'pwa_cache_expiry_days'];
    numberNames.forEach(name => {
        const el = document.getElementById(name + '-value');
        if (el) settings[name] = parseInt(el.textContent.trim(), 10) || 0;
    });
    syncPwaSettingsToSW(settings);
}

// PWA-Toggles mit localStorage synchronisieren (gecachte HTML kann veraltet sein)
function syncPwaTogglesFromLocalStorage() {
    const toggle = document.getElementById('pwa-toggle-pwa_offline_all');
    if (toggle) {
        const localState = localStorage.getItem('pwa_offline_all') === 'true';
        toggle.checked = localState;
    }
}

// Init storage display on page load
if (settingsType === 'user-settings') {
    document.addEventListener('DOMContentLoaded', () => {
        syncPwaTogglesFromLocalStorage();
        updateStorageDisplay();
        syncAllPwaSettings();
    });
}
