// Curated Material Symbols for icon autocomplete
const MATERIAL_ICONS = [
    // Navigation & Actions
    'home', 'menu', 'search', 'settings', 'add', 'edit', 'delete', 'close', 'check', 'arrow_back',
    'arrow_forward', 'expand_more', 'expand_less', 'more_vert', 'more_horiz', 'refresh', 'done',
    // Content
    'favorite', 'star', 'bookmark', 'flag', 'label', 'push_pin', 'lightbulb', 'info', 'help',
    'announcement', 'campaign', 'new_releases', 'tips_and_updates',
    // Communication
    'chat', 'mail', 'call', 'message', 'forum', 'contacts', 'group', 'person', 'people',
    'notifications', 'send', 'share',
    // Media
    'photo', 'image', 'camera', 'videocam', 'movie', 'music_note', 'headphones', 'mic',
    'play_arrow', 'pause', 'volume_up',
    // Places & Travel
    'place', 'map', 'explore', 'flight', 'hotel', 'restaurant', 'local_cafe', 'beach_access',
    'hiking', 'directions_car', 'train', 'sailing',
    // Shopping & Finance
    'shopping_cart', 'store', 'payments', 'credit_card', 'receipt', 'sell', 'redeem',
    // Social & Activities
    'celebration', 'cake', 'sports_esports', 'fitness_center', 'pool', 'sports_soccer',
    'emoji_events', 'workspace_premium',
    // Objects
    'book', 'menu_book', 'auto_stories', 'school', 'science', 'psychology', 'palette',
    'brush', 'create', 'build', 'handyman', 'key', 'lock', 'vpn_key',
    // Nature & Weather
    'pets', 'eco', 'park', 'forest', 'water_drop', 'wb_sunny', 'nights_stay', 'cloud',
    // Health & Wellness
    'health_and_safety', 'medical_services', 'spa', 'self_improvement', 'volunteer_activism',
    // Food & Drink
    'lunch_dining', 'dinner_dining', 'bakery_dining', 'local_bar', 'wine_bar', 'coffee',
    // Home & Living
    'cottage', 'apartment', 'bed', 'chair', 'kitchen', 'yard',
    // Lists & Organization
    'checklist', 'task_alt', 'assignment', 'inventory', 'category', 'folder', 'archive',
    'list', 'view_list', 'format_list_bulleted', 'sort',
];

const RESERVED_PATHS = ['home', 'settings', 'login', 'logout', 'setup', 'user-settings', 'manage-translations', 'gallery', 'api', 'static', 'admin'];

let pathManuallyEdited = false;

function openCreateListType() {
    document.getElementById('manage-list-type-id').value = '';
    document.getElementById('manage-list-type-title').value = '';
    document.getElementById('manage-list-type-main-title').value = '';
    document.getElementById('manage-list-type-path').value = '';
    document.getElementById('manage-list-type-icon').value = 'list';
    document.getElementById('manage-list-type-icon-preview').textContent = 'list';
    document.getElementById('manage-list-type-dialog-title').textContent = _('Create new list');
    document.getElementById('manage-list-type-delete-btn').style.display = 'none';
    document.getElementById('manage-list-type-path-helper').textContent = _('Only lowercase letters, numbers and hyphens');
    document.getElementById('manage-list-type-path-helper').className = 'helper';
    pathManuallyEdited = false;
    callUi('#dialog-manage-list-type');
}

function openEditListTypeFromElement(el) {
    document.getElementById('manage-list-type-id').value = el.dataset.id;
    document.getElementById('manage-list-type-title').value = el.dataset.title;
    document.getElementById('manage-list-type-main-title').value = el.dataset.maintitle;
    document.getElementById('manage-list-type-path').value = el.dataset.contenturl;
    document.getElementById('manage-list-type-icon').value = el.dataset.icon;
    document.getElementById('manage-list-type-icon-preview').textContent = el.dataset.icon;
    document.getElementById('manage-list-type-dialog-title').textContent = _('Edit list');
    document.getElementById('manage-list-type-delete-btn').style.display = '';
    document.getElementById('manage-list-type-path-helper').textContent = _('Only lowercase letters, numbers and hyphens');
    document.getElementById('manage-list-type-path-helper').className = 'helper';
    pathManuallyEdited = true; // In edit mode, don't auto-generate path
    callUi('#dialog-manage-list-type');
}

function onListTypeTitleInput(value) {
    // Auto-generate path from title only in create mode and if path wasn't manually edited
    if (!pathManuallyEdited && !document.getElementById('manage-list-type-id').value) {
        const sanitized = sanitizePath(value);
        document.getElementById('manage-list-type-path').value = sanitized;
        validatePath(sanitized);
    }
}

function onListTypePathInput(value) {
    pathManuallyEdited = true;
    const sanitized = sanitizePath(value);
    document.getElementById('manage-list-type-path').value = sanitized;
    validatePath(sanitized);
}

function sanitizePath(input) {
    let path = input.toLowerCase();
    // Remove leading slashes
    path = path.replace(/^\/+/, '');
    // Replace spaces with hyphens
    path = path.replace(/\s+/g, '-');
    // Remove everything except a-z, 0-9, hyphens
    path = path.replace(/[^a-z0-9-]/g, '');
    // Collapse multiple hyphens
    path = path.replace(/-{2,}/g, '-');
    // Remove trailing hyphens
    path = path.replace(/-+$/, '');
    return path;
}

function validatePath(path) {
    const helper = document.getElementById('manage-list-type-path-helper');
    const input = document.getElementById('manage-list-type-path');

    if (RESERVED_PATHS.includes(path)) {
        helper.textContent = _('This path is reserved and cannot be used');
        helper.className = 'helper error';
        input.classList.add('invalid');
        return false;
    }
    if (path.length === 0) {
        helper.textContent = _('Only lowercase letters, numbers and hyphens');
        helper.className = 'helper';
        input.classList.remove('invalid');
        return false;
    }
    helper.textContent = _('Only lowercase letters, numbers and hyphens');
    helper.className = 'helper';
    input.classList.remove('invalid');
    return true;
}

function onListTypeIconInput(value) {
    document.getElementById('manage-list-type-icon-preview').textContent = value || 'help';
    showIconSuggestions(value);
}

function showIconSuggestions(query) {
    const container = document.getElementById('manage-list-type-icon-suggestions');
    let filtered;
    if (!query || query.trim() === '') {
        filtered = MATERIAL_ICONS.slice(0, 24);
    } else {
        filtered = MATERIAL_ICONS.filter(icon => icon.includes(query.toLowerCase())).slice(0, 30);
    }

    if (filtered.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.innerHTML = filtered.map(icon =>
        `<button class="chip small" onclick="selectIcon('${icon}')" style="margin: 2px; cursor: pointer;">
            <i>${icon}</i>
            <span>${icon.replace(/_/g, ' ')}</span>
        </button>`
    ).join('');
    container.style.display = '';
}

function selectIcon(iconName) {
    document.getElementById('manage-list-type-icon').value = iconName;
    document.getElementById('manage-list-type-icon-preview').textContent = iconName;
    document.getElementById('manage-list-type-icon-suggestions').style.display = 'none';
}

// Close icon suggestions when clicking outside
document.addEventListener('click', function(e) {
    const suggestions = document.getElementById('manage-list-type-icon-suggestions');
    const iconField = document.getElementById('manage-list-type-icon');
    if (suggestions && iconField && !suggestions.contains(e.target) && e.target !== iconField) {
        suggestions.style.display = 'none';
    }
});

function saveListType() {
    if (!navigator.onLine) {
        showSnackbar('navbar', true, 'error', _('You are offline'), null, false);
        return;
    }
    const id = document.getElementById('manage-list-type-id').value;
    const title = document.getElementById('manage-list-type-title').value.trim();
    const mainTitle = document.getElementById('manage-list-type-main-title').value.trim();
    const path = document.getElementById('manage-list-type-path').value.trim();
    const icon = document.getElementById('manage-list-type-icon').value.trim();

    if (!title) {
        showSnackbar('navbar', true, 'error', _('Please enter a sidebar name'), null, false);
        return;
    }
    if (!path || !validatePath(path)) {
        showSnackbar('navbar', true, 'error', _('Please enter a valid path'), null, false);
        return;
    }
    if (!icon) {
        showSnackbar('navbar', true, 'error', _('Please select an icon'), null, false);
        return;
    }

    const formData = new FormData();
    formData.append('title', title);
    formData.append('mainTitle', mainTitle || title);
    formData.append('contentURL', path);
    formData.append('icon', icon);
    formData.append('navbar', true);

    const isEdit = !!id;
    const url = isEdit ? `/api/v2/list_type/${id}` : '/api/v2/list_type';
    const method = isEdit ? 'PUT' : 'POST';

    fetch(url, { method, body: formData })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === 'success') {
                    callUi('#dialog-manage-list-type');
                    document.getElementById('div-render-nav-drawer').innerHTML = result.data.rendered_list_types;
                    document.body.style.overflow = 'hidden';
                    showSnackbar('navbar', true, 'green', result.message, result, false);
                } else {
                    showSnackbar('navbar', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('navbar', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (error == 'TypeError: Failed to fetch') {
                error = _('Server not reachable');
            }
            showSnackbar('navbar', true, 'error', error, null, false);
        });
}

function deleteListTypeFromDialog() {
    if (!navigator.onLine) {
        showSnackbar('navbar', true, 'error', _('You are offline'), null, false);
        return;
    }
    const id = document.getElementById('manage-list-type-id').value;
    if (!id) return;

    if (!confirm(_('Do you really want to delete this entry? All associated entries will also be deleted.'))) {
        return;
    }

    fetch(`/api/v2/list_type/${id}`, { method: 'DELETE' })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === 'success') {
                    callUi('#dialog-manage-list-type');
                    document.getElementById('div-render-nav-drawer').innerHTML = result.data.rendered_list_types;
                    showSnackbar('navbar', true, 'green', result.message, result, false);
                } else {
                    showSnackbar('navbar', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('navbar', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (error == 'TypeError: Failed to fetch') {
                error = _('Server not reachable');
            }
            showSnackbar('navbar', true, 'error', error, null, false);
        });
}

// --- Drag and Drop for reordering ---

function changeNavOrder(mode) {
    if (mode == 'edit') {
        const checkElements = document.getElementsByClassName('check');
        for (let i = 0; i < checkElements.length; i++) {
            const checkElement = checkElements[i];
            checkElement.textContent = 'drag_handle';
            checkElement.removeAttribute('onclick');

            const parentDiv = checkElement.closest('[id^="div-nav-"]');
            if (parentDiv) parentDiv.setAttribute('draggable', 'true');
        }
        document.getElementById('a-change-nav-order').textContent = _('Save order');
        document.getElementById('a-change-nav-order').setAttribute('onclick', "changeNavOrder('save')");

    } else if (mode == 'save') {
        if (!navigator.onLine) {
            showSnackbar('navbar', true, 'error', _('You are offline'), null, false);
            return;
        }
        const listTypes = document.querySelectorAll('[id^="div-nav"]');

        for (let i = 0; i < listTypes.length; i++) {
            const id = listTypes[i].id.split('-')[2];
            const formData = new FormData();
            formData.append('navbarOrder', i + 1);

            fetch(`/api/v2/list_type/${id}`, {
                method: 'PUT',
                body: formData,
            })
                .then(async (response) => {
                    try {
                        const result = await response.json();
                        if (result.status === 'success') {
                            document.getElementById('div-render-nav-drawer').innerHTML = result.data.rendered_list_types;
                            showSnackbar('navbar', true, 'green', result.message, result, false);
                        } else {
                            showSnackbar('navbar', true, 'error', result.message, result, true);
                        }
                    } catch (error) {
                        showSnackbar('navbar', true, 'error', error, null, false);
                    }
                })
                .catch((error) => {
                    if (error == 'TypeError: Failed to fetch') {
                        error = _('Server not reachable');
                    }
                    showSnackbar('navbar', true, 'error', error, null, false);
                });
        }

        const checkElements = document.getElementsByClassName('check');
        for (let i = 0; i < checkElements.length; i++) {
            const checkElement = checkElements[i];
            checkElement.textContent = 'edit';
            checkElement.setAttribute('onclick', "openEditListTypeFromElement(this.closest('a'))");

            const parentDiv = checkElement.closest('[id^="div-nav-"]');
            if (parentDiv) parentDiv.setAttribute('draggable', 'false');
        }
        document.getElementById('a-change-nav-order').textContent = _('Change order');
        document.getElementById('a-change-nav-order').setAttribute('onclick', "changeNavOrder('edit')");
    }
}

let draggedElement = null;

function dragStart(event) {
    draggedElement = event.currentTarget;
    event.dataTransfer.effectAllowed = 'move';
}

function dragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
}

function drop(event) {
    event.preventDefault();

    const target = event.currentTarget;

    if (draggedElement !== target) {
        const parent = draggedElement.parentNode;
        if (target.nextSibling === draggedElement) {
            parent.insertBefore(draggedElement, target);
        } else {
            parent.insertBefore(target, draggedElement);
            parent.insertBefore(draggedElement, target.nextSibling);
        }
    }
}
