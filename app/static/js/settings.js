// --- State ---
// These are set from inline <script> in settings.html:
// relationshipStatuses, supportedLanguages, editions, currentEdition, settingsType

let requiredDateMode = false;
let pendingRequiredDates = [];

// --- Profile Picture ---
function _rowSpinnerOn(row) {
    if (!row) return null;
    const icon = row.querySelector('i:last-of-type');
    if (icon) {
        icon._origText = icon.textContent;
        const spinner = Object.assign(document.createElement('progress'), {className:'circle small'});
        icon.replaceWith(spinner);
        return { spinner, origText: icon._origText };
    }
    return null;
}

function _rowSpinnerOff(ref) {
    if (!ref) return;
    const i = document.createElement('i');
    i.textContent = ref.origText;
    ref.spinner.replaceWith(i);
}

function updateProfilePicture(input) {
    if (!input.files || !input.files[0]) return;
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }

    const row = document.getElementById('profile-picture-preview')?.closest('a');
    const ref = _rowSpinnerOn(row);

    const formData = new FormData();
    formData.append('file', input.files[0]);

    fetch('/api/v2/user/profile-picture', {
        method: 'PUT',
        body: formData,
    })
    .then(res => res.json())
    .then(result => {
        _rowSpinnerOff(ref);
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
        _rowSpinnerOff(ref);
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
    const btn = document.getElementById('save-setting');
    btnLoading(btn);

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
                btnReset(btn);
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
            btnReset(btn);
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
    const btn = document.getElementById('save-setting');
    btnLoading(btn);

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
                btnReset(btn);
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
            btnReset(btn);
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

    // Re-apply accent color theme for new mode
    const accentHex = document.getElementById('input-custom-accent-color')?.value
        || document.querySelector('meta[name="theme-color"]')?.content;
    if (accentHex && typeof window.applyTheme === 'function') {
        window.applyTheme(accentHex);
    }

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
    const btn = document.getElementById('save-edition-btn');
    btnLoading(btn);

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
                btnReset(btn);
                closeEditionDialog();
                location.reload();
            } else {
                btnReset(btn);
                showSnackbar('settings', true, 'error', result.message, result, true);
            }
        })
        .catch((error) => {
            btnReset(btn);
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

async function forceUpdatePWA(btn) {
    if (!('serviceWorker' in navigator)) {
        showSnackbar('settings', true, 'error', _('Service Worker not supported'), null, false);
        return;
    }
    btnLoading(btn);
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
        btnReset(btn);
    } catch (err) {
        btnReset(btn);
        showSnackbar('settings', true, 'error', String(err), null, false);
    }
}

function clearPwaCache(btn) {
    btnLoading(btn);
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
            btnReset(btn);
            showSnackbar('settings', true, 'green', _('Cache cleared'), null, false);
            updateStorageDisplay();
        });
    } else {
        btnReset(btn);
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

// --- Banner Image ---
function uploadBannerImage(input) {
    if (!input.files || !input.files[0]) return;
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }

    const row = document.getElementById('banner_image-value')?.closest('a');
    const ref = _rowSpinnerOn(row);

    const formData = new FormData();
    formData.append('file', input.files[0]);

    fetch('/api/v2/upload', {
        method: 'POST',
        body: formData,
    })
    .then(res => res.json())
    .then(result => {
        if (result.status === 'success') {
            const filename = result.data.filename;
            const settingForm = new FormData();
            settingForm.append('setting', 'banner_image');
            settingForm.append('value', filename);

            return fetch('/api/v2/settings', {
                method: 'PUT',
                body: settingForm,
            }).then(res => res.json());
        } else {
            throw new Error(result.message);
        }
    })
    .then(result => {
        _rowSpinnerOff(ref);
        if (result && result.status === 'success') {
            document.getElementById('banner_image-value').textContent = result.data.value;
            showSnackbar('settings', true, 'green', result.message, null, false);
            location.reload();
        } else if (result) {
            showSnackbar('settings', true, 'error', result.message, result, true);
        }
    })
    .catch(error => {
        _rowSpinnerOff(ref);
        if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
        showSnackbar('settings', true, 'error', String(error), null, false);
    })
    .finally(() => {
        input.value = '';
    });
}

function deleteBannerImage(btn) {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }

    btnLoading(btn);

    const formData = new FormData();
    formData.append('setting', 'banner_image');
    formData.append('value', '');

    fetch('/api/v2/settings', {
        method: 'PUT',
        body: formData,
    })
    .then(res => res.json())
    .then(result => {
        if (result.status === 'success') {
            document.getElementById('banner_image-value').textContent = _('No image');
            showSnackbar('settings', true, 'green', result.message, null, false);
            btnReset(btn);
            location.reload();
        } else {
            btnReset(btn);
            showSnackbar('settings', true, 'error', result.message, result, true);
        }
    })
    .catch(error => {
        btnReset(btn);
        if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
        showSnackbar('settings', true, 'error', String(error), null, false);
    });
}

// --- Banner Song ---
function uploadBannerSong(input) {
    if (!input.files || !input.files[0]) return;
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }

    const row = document.getElementById('banner_song-value')?.closest('a');
    const ref = _rowSpinnerOn(row);

    const formData = new FormData();
    formData.append('file', input.files[0]);

    fetch('/api/v2/upload', {
        method: 'POST',
        body: formData,
    })
    .then(res => res.json())
    .then(result => {
        if (result.status === 'success') {
            const filename = result.data.filename;
            const settingForm = new FormData();
            settingForm.append('setting', 'banner_song');
            settingForm.append('value', filename);

            return fetch('/api/v2/settings', {
                method: 'PUT',
                body: settingForm,
            }).then(res => res.json());
        } else {
            throw new Error(result.message);
        }
    })
    .then(result => {
        _rowSpinnerOff(ref);
        if (result && result.status === 'success') {
            document.getElementById('banner_song-value').textContent = result.data.value;
            showSnackbar('settings', true, 'green', result.message, null, false);
            location.reload();
        } else if (result) {
            showSnackbar('settings', true, 'error', result.message, result, true);
        }
    })
    .catch(error => {
        _rowSpinnerOff(ref);
        if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
        showSnackbar('settings', true, 'error', String(error), null, false);
    })
    .finally(() => {
        input.value = '';
    });
}

function deleteBannerSong(btn) {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }

    btnLoading(btn);

    const formData = new FormData();
    formData.append('setting', 'banner_song');
    formData.append('value', '');

    fetch('/api/v2/settings', {
        method: 'PUT',
        body: formData,
    })
    .then(res => res.json())
    .then(result => {
        if (result.status === 'success') {
            document.getElementById('banner_song-value').textContent = _('No song');
            showSnackbar('settings', true, 'green', result.message, null, false);
            btnReset(btn);
            location.reload();
        } else {
            btnReset(btn);
            showSnackbar('settings', true, 'error', result.message, result, true);
        }
    })
    .catch(error => {
        btnReset(btn);
        if (String(error) == "TypeError: Failed to fetch") error = _('Server not reachable');
        showSnackbar('settings', true, 'error', String(error), null, false);
    });
}

// --- Notification Channels ---

function togglePush(enabled) {
    const toggle = document.getElementById('toggle-push');
    if (toggle) toggle.checked = enabled;
    saveNotificationSetting('notification_push_enabled', enabled ? 'True' : 'False');
    if (enabled && Notification.permission === 'default') {
        requestPushPermission();
    } else if (enabled && Notification.permission === 'granted') {
        subscribeToPush();
    } else if (!enabled) {
        unsubscribeFromPush();
    }
}

function toggleEmail(enabled) {
    const toggle = document.getElementById('toggle-email');
    if (toggle) toggle.checked = enabled;
    saveNotificationSetting('notification_email_enabled', enabled ? 'True' : 'False');
    const testSection = document.getElementById('email-test-section');
    if (testSection) testSection.style.display = enabled ? '' : 'none';
}

function toggleTelegram(enabled) {
    const toggle = document.getElementById('toggle-telegram');
    if (toggle) toggle.checked = enabled;
    saveNotificationSetting('notification_telegram_enabled', enabled ? 'True' : 'False');
    const configSection = document.getElementById('telegram-config-section');
    if (configSection) configSection.style.display = enabled ? '' : 'none';
}

function saveTelegramConfig() {
    const chatId = document.getElementById('input-telegram-chat-id')?.value || '';
    saveNotificationSetting('notification_telegram_chat_id', chatId);
    const statusEl = document.getElementById('telegram-status-text');
    if (statusEl) statusEl.textContent = chatId || _('Not configured');
    showSnackbar('settings', true, 'success', _('Telegram Chat-ID saved'), null, false);
}

async function requestPushPermission() {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
        await subscribeToPush();
    }
    updatePushStatus();
}

async function subscribeToPush() {
    try {
        const reg = await navigator.serviceWorker.ready;
        const keyResp = await fetch('/api/v2/push/vapid-key');
        const keyData = await keyResp.json();
        if (keyData.status !== 'success') {
            console.error('VAPID key fetch failed:', keyData);
            showSnackbar('settings', true, 'error', _('Failed to get push key from server'), null, false);
            return;
        }

        // Unsubscribe existing subscription if key changed
        const existingSub = await reg.pushManager.getSubscription();
        if (existingSub) {
            await existingSub.unsubscribe();
        }

        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(keyData.data.publicKey)
        });

        const subJson = sub.toJSON();
        const saveResp = await fetch('/api/v2/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                endpoint: subJson.endpoint,
                keys: subJson.keys
            })
        });
        const saveResult = await saveResp.json();
        if (saveResult.status === 'success') {
            showSnackbar('settings', true, 'success', _('Push notifications enabled'), null, false);
        } else {
            console.error('Push subscribe save failed:', saveResult);
            showSnackbar('settings', true, 'error', saveResult.message || _('An error occurred'), null, false);
        }
    } catch (e) {
        console.error('Push subscription failed:', e);
        showSnackbar('settings', true, 'error', _('Push subscription failed'), null, false);
    }
}

async function subscribeToPushSilent() {
    try {
        const reg = await navigator.serviceWorker.ready;
        const keyResp = await fetch('/api/v2/push/vapid-key');
        const keyData = await keyResp.json();
        if (keyData.status !== 'success') return;

        const existingSub = await reg.pushManager.getSubscription();
        if (existingSub) {
            // Already subscribed, just ensure server knows
            const subJson = existingSub.toJSON();
            await fetch('/api/v2/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ endpoint: subJson.endpoint, keys: subJson.keys })
            });
            return;
        }

        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(keyData.data.publicKey)
        });
        const subJson = sub.toJSON();
        await fetch('/api/v2/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endpoint: subJson.endpoint, keys: subJson.keys })
        });
    } catch (e) {
        console.error('Silent push subscription failed:', e);
    }
}

async function unsubscribeFromPush() {
    try {
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) {
            const subJson = sub.toJSON();
            await sub.unsubscribe();
            await fetch('/api/v2/push/subscribe', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ endpoint: subJson.endpoint })
            });
        }
    } catch (e) {
        console.error('Push unsubscribe failed:', e);
    }
}

async function updatePushStatus() {
    const statusEl = document.getElementById('push-status-text');
    const permSection = document.getElementById('push-permission-section');
    const testSection = document.getElementById('push-test-section');
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        if (statusEl) statusEl.textContent = _('Not supported by browser');
        return;
    }

    const permission = Notification.permission;
    if (permission === 'granted') {
        if (statusEl) statusEl.textContent = _('Active');
        if (permSection) permSection.style.display = 'none';
        if (testSection) testSection.style.display = '';
    } else if (permission === 'denied') {
        if (statusEl) statusEl.textContent = _('Blocked by browser');
        if (permSection) permSection.style.display = 'none';
        if (testSection) testSection.style.display = 'none';
    } else {
        if (statusEl) statusEl.textContent = _('Permission required');
        if (permSection) permSection.style.display = '';
        if (testSection) testSection.style.display = 'none';
    }
}

async function testNotification(channel, btn) {
    btnLoading(btn);
    try {
        const resp = await fetch('/api/v2/notifications/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel: channel })
        });
        const result = await resp.json();
        btnReset(btn);
        if (result.status === 'success') {
            showSnackbar('settings', true, 'success', result.message, null, false);
        } else {
            showSnackbar('settings', true, 'error', result.message || _('An error occurred'), null, false);
        }
    } catch (e) {
        btnReset(btn);
        showSnackbar('settings', true, 'error', _('An error occurred'), null, false);
    }
}

function saveNotificationSetting(name, value) {
    const formData = new FormData();
    formData.append('setting', name);
    formData.append('value', value);
    fetch('/api/v2/user-settings', { method: 'PUT', body: formData });
}

function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

function initNotificationSettings() {
    const pushToggle = document.getElementById('toggle-push');
    if (pushToggle) pushToggle.checked = window.pushEnabled || false;

    const emailToggle = document.getElementById('toggle-email');
    if (emailToggle && emailToggle.checked) {
        const testSection = document.getElementById('email-test-section');
        if (testSection) testSection.style.display = '';
    }

    const telegramToggle = document.getElementById('toggle-telegram');
    if (telegramToggle && telegramToggle.checked) {
        const configSection = document.getElementById('telegram-config-section');
        if (configSection) configSection.style.display = '';
    }

    updatePushStatus();

    // Auto-subscribe silently if push enabled and permission granted
    if (window.pushEnabled && Notification.permission === 'granted') {
        subscribeToPushSilent();
    }
}

// --- Accent Color ---

async function selectAccentColor(hex) {
   if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) return;
   await previewAccentColor(hex);
   document.querySelectorAll('.accent-swatch').forEach(btn => {
      btn.style.borderColor = btn.dataset.color === hex.toUpperCase() ? 'var(--on-surface)' : 'transparent';
   });
   const ti = document.getElementById('input-custom-accent-color');
   if (ti) ti.value = hex;
   const ps = document.getElementById('color-preview-swatch');
   if (ps) ps.style.background = hex;
   saveAccentColor(hex);
}

async function previewAccentColor(hex) {
   if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) return;
   if (typeof window.applyTheme === 'function') {
      await window.applyTheme(hex);
   } else if (typeof ui === 'function') {
      await ui('theme', hex);
   }
   document.querySelector('meta[name="theme-color"]')?.setAttribute('content', hex);
}

function applyCustomAccentColor() {
   const input = document.getElementById('input-custom-accent-color');
   if (!input) return;
   let v = input.value.trim().toUpperCase();
   if (!v.startsWith('#')) v = '#' + v;
   if (!/^#[0-9A-Fa-f]{6}$/.test(v)) {
      showSnackbar('settings', true, 'error', _('Invalid color code'), null, false);
      return;
   }
   selectAccentColor(v);
}

function saveAccentColor(hex) {
   if (!navigator.onLine) {
      showSnackbar('settings', true, 'error', _('You are offline'), null, false);
      return;
   }
   const fd = new FormData();
   fd.append('setting', 'accent_color');
   fd.append('value', hex);
   fetch('/api/v2/user-settings', { method: 'PUT', body: fd })
      .then(async r => {
         const res = await r.json();
         if (res.status === 'success') {
            showSnackbar('settings', true, 'green', res.message, null, false);
         } else {
            showSnackbar('settings', true, 'error', res.message, res, true);
         }
      })
      .catch(e => {
         showSnackbar('settings', true, 'error',
            String(e) === 'TypeError: Failed to fetch' ? _('Server not reachable') : e, null, false);
      });
}

// --- Data Export/Import ---

function startDataExport(row) {
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }
    const ref = _rowSpinnerOn(row);

    fetch('/api/v2/data/export', { method: 'POST' })
        .then(res => res.json())
        .then(result => {
            _rowSpinnerOff(ref);
            if (result.status === 'success') {
                const exportId = result.data.export_id;
                document.getElementById('export-progress-container').style.display = '';
                document.getElementById('export-download-link').style.display = 'none';
                document.getElementById('export-progress-bar').value = 0;
                document.getElementById('export-progress-text').textContent = '0%';
                pollExportStatus(exportId);
            } else {
                showSnackbar('settings', true, 'error', result.message, result, true);
            }
        })
        .catch(error => {
            _rowSpinnerOff(ref);
            if (String(error) === 'TypeError: Failed to fetch') error = _('Server not reachable');
            showSnackbar('settings', true, 'error', String(error), null, false);
        });
}

function pollExportStatus(exportId) {
    const interval = setInterval(() => {
        fetch('/api/v2/data/export/status/' + exportId)
            .then(res => res.json())
            .then(result => {
                if (result.status === 'success') {
                    const data = result.data;
                    document.getElementById('export-progress-bar').value = data.progress;
                    document.getElementById('export-progress-text').textContent = data.progress + '%';

                    if (data.export_status === 'done') {
                        clearInterval(interval);
                        const link = document.getElementById('export-download-link');
                        link.href = '/api/v2/media/export/' + data.filename;
                        link.setAttribute('download', data.filename);
                        link.style.display = '';
                        showSnackbar('settings', true, 'green', _('Export completed'), null, false);
                    } else if (data.export_status === 'error') {
                        clearInterval(interval);
                        showSnackbar('settings', true, 'error', data.error || _('Export failed'), null, false);
                    }
                }
            })
            .catch(() => {
                clearInterval(interval);
                showSnackbar('settings', true, 'error', _('Server not reachable'), null, false);
            });
    }, 1000);
}

function startDataImport(input) {
    if (!input.files || !input.files[0]) return;
    if (!navigator.onLine) {
        showSnackbar('settings', true, 'error', _('You are offline'), null, false);
        return;
    }

    const file = input.files[0];
    const row = document.getElementById('import-data-row');
    const ref = _rowSpinnerOn(row);
    const progressContainer = document.getElementById('import-progress-container');
    const progressBar = document.getElementById('import-progress-bar');
    const progressText = document.getElementById('import-progress-text');
    const progressPhase = document.getElementById('import-progress-phase');

    progressContainer.style.display = '';
    document.getElementById('import-summary-container').style.display = 'none';
    progressBar.value = 0;
    progressText.textContent = '0%';
    progressPhase.textContent = _('Uploading...');

    const CHUNK_SIZE = 100 * 1024 * 1024;
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    const uploadId = Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const totalMB = (file.size / (1024 * 1024)).toFixed(1);
    const uploadStart = Date.now();

    function formatTime(seconds) {
        if (seconds < 60) return Math.round(seconds) + 's';
        const m = Math.floor(seconds / 60);
        const s = Math.round(seconds % 60);
        return m + 'min ' + s + 's';
    }

    function updateProgress(loaded) {
        const pct = Math.round(loaded / file.size * 100);
        const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
        progressBar.value = pct;
        progressText.textContent = pct + '%';
        const elapsed = (Date.now() - uploadStart) / 1000;
        let eta = '';
        if (elapsed > 1 && loaded > 0) {
            const remaining = (elapsed / loaded) * (file.size - loaded);
            eta = ' — ' + formatTime(remaining) + ' ' + _('remaining');
        }
        progressPhase.textContent = loadedMB + ' / ' + totalMB + ' MB' + eta;
    }

    function sendChunk(index) {
        return new Promise((resolve, reject) => {
            const start = index * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, file.size);
            const chunk = file.slice(start, end);

            const xhr = new XMLHttpRequest();
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) updateProgress(start + e.loaded);
            });
            xhr.addEventListener('load', () => {
                try { resolve(JSON.parse(xhr.responseText)); }
                catch (e) { reject(new Error('HTTP ' + xhr.status + ': ' + xhr.responseText.substring(0, 200))); }
            });
            xhr.addEventListener('error', () => reject(new Error(_('Server not reachable'))));
            xhr.open('POST', '/api/v2/data/import-chunk');
            xhr.setRequestHeader('X-Upload-ID', uploadId);
            xhr.setRequestHeader('X-Chunk-Index', index);
            xhr.setRequestHeader('X-Total-Chunks', totalChunks);
            xhr.send(chunk);
        });
    }

    const phaseLabels = {
        extracting: _('Extracting ZIP...'),
        importing: _('Importing items...'),
        copying_media: _('Copying media files...')
    };

    function pollImportStatus(importId) {
        let failCount = 0;
        const interval = setInterval(() => {
            fetch('/api/v2/data/import/status/' + importId)
                .then(res => {
                    if (!res.ok) throw new Error('HTTP ' + res.status);
                    return res.json();
                })
                .then(result => {
                    failCount = 0;
                    if (result.status !== 'success') return;
                    const d = result.data;
                    progressBar.value = d.progress;
                    progressText.textContent = d.progress + '%';
                    progressPhase.textContent = phaseLabels[d.phase] || d.phase;

                    if (d.import_status === 'done') {
                        clearInterval(interval);
                        _rowSpinnerOff(ref);
                        input.value = '';
                        progressContainer.style.display = 'none';
                        const r = d.result;
                        const summaryEl = document.getElementById('import-summary-text');
                        summaryEl.innerHTML =
                            `<p>${_('Items imported')}: ${r.imported}</p>` +
                            `<p>${_('Skipped (duplicate)')}: ${r.skipped_duplicate}</p>` +
                            `<p>${_('Skipped (error)')}: ${r.skipped_error}</p>` +
                            `<p>${_('Users imported')}: ${r.users_imported}</p>` +
                            `<p>${_('User settings imported')}: ${r.user_settings_imported}</p>` +
                            `<p>${_('Reminders imported')}: ${r.reminders_imported}</p>` +
                            `<p>${_('Media files copied')}: ${r.media_copied}</p>` +
                            `<p>${_('Settings updated')}: ${r.settings_updated}</p>`;
                        document.getElementById('import-summary-container').style.display = '';
                        showSnackbar('settings', true, 'green', _('Import completed successfully! Redirecting...'), null, false);
                        setTimeout(() => { window.location.href = '/logout'; }, 3000);
                    } else if (d.import_status === 'error') {
                        clearInterval(interval);
                        _rowSpinnerOff(ref);
                        input.value = '';
                        progressContainer.style.display = 'none';
                        showSnackbar('settings', true, 'error', d.error || _('Import failed'), null, false);
                    }
                })
                .catch(() => {
                    failCount++;
                    if (failCount >= 30) {
                        clearInterval(interval);
                        _rowSpinnerOff(ref);
                        input.value = '';
                        progressContainer.style.display = 'none';
                        showSnackbar('settings', true, 'error', _('Server not reachable'), null, false);
                    }
                });
        }, 2000);
    }

    (async () => {
        try {
            for (let i = 0; i < totalChunks; i++) {
                const result = await sendChunk(i);
                if (result.status !== 'success') {
                    _rowSpinnerOff(ref);
                    input.value = '';
                    progressContainer.style.display = 'none';
                    showSnackbar('settings', true, 'error', result.message, result, true);
                    return;
                }
                // Last chunk returns import_id — start polling
                if (i === totalChunks - 1) {
                    progressBar.value = 0;
                    progressText.textContent = '0%';
                    progressPhase.textContent = phaseLabels.extracting;
                    pollImportStatus(result.data.import_id);
                }
            }
        } catch (e) {
            _rowSpinnerOff(ref);
            input.value = '';
            progressContainer.style.display = 'none';
            showSnackbar('settings', true, 'error', String(e.message || e), null, false);
        }
    })();
}

// Init
if (settingsType === 'user-settings') {
    document.addEventListener('DOMContentLoaded', () => {
        syncPwaTogglesFromLocalStorage();
        updateStorageDisplay();
        syncAllPwaSettings();
        initNotificationSettings();
        document.getElementById('input-custom-accent-color')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') applyCustomAccentColor();
        });
    });
}
