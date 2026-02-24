// --- Tab Switching ---
function showAdminTab(tab) {
    document.getElementById('tab-users').style.display = tab === 'users' ? '' : 'none';
    document.getElementById('tab-roles').style.display = tab === 'roles' ? '' : 'none';
    document.getElementById('tab-shares').style.display = tab === 'shares' ? '' : 'none';
    document.getElementById('tab-users-btn').classList.toggle('active', tab === 'users');
    document.getElementById('tab-roles-btn').classList.toggle('active', tab === 'roles');
    document.getElementById('tab-shares-btn').classList.toggle('active', tab === 'shares');
    document.getElementById('fab-create-user').style.display = tab === 'users' ? '' : 'none';
    document.getElementById('fab-create-role').style.display = tab === 'roles' ? '' : 'none';
}

// --- User Create / Edit ---
function openCreateUser() {
    document.getElementById('edit-user-id').value = '';
    document.getElementById('edit-user-firstName').value = '';
    document.getElementById('edit-user-lastName').value = '';
    document.getElementById('edit-user-email').value = '';
    document.getElementById('edit-user-birthDate').value = '';
    document.getElementById('edit-user-password').value = '';
    document.getElementById('edit-user-passwordConfirm').value = '';
    document.getElementById('edit-user-password-label').textContent = _('Password');
    document.getElementById('edit-user-password-confirm-field').style.display = '';
    document.getElementById('edit-user-profilePicture').value = '';
    document.getElementById('edit-user-profilePicture-preview').style.display = 'none';
    document.getElementById('edit-user-title').textContent = _('Create user');
    document.getElementById('btn-delete-user').style.display = 'none';

    // Roles: default Adult checked
    renderRoleCheckboxes('edit-user-roles-checkboxes', [3]);

    callUi('#dialog-edit-user');
}

function editUser(userId, firstName, lastName, email, birthDate) {
    document.getElementById('edit-user-id').value = userId;
    document.getElementById('edit-user-firstName').value = firstName;
    document.getElementById('edit-user-lastName').value = lastName;
    document.getElementById('edit-user-email').value = email;
    document.getElementById('edit-user-birthDate').value = birthDate;
    document.getElementById('edit-user-password').value = '';
    document.getElementById('edit-user-passwordConfirm').value = '';
    document.getElementById('edit-user-password-label').textContent = _('New password (leave empty to keep)');
    document.getElementById('edit-user-password-confirm-field').style.display = '';
    document.getElementById('edit-user-profilePicture').value = '';
    document.getElementById('edit-user-profilePicture-preview').style.display = 'none';
    document.getElementById('edit-user-title').textContent = _('Edit user');
    document.getElementById('btn-delete-user').style.display = '';

    // Roles
    const currentRoles = userRolesMap[userId] || [];
    renderRoleCheckboxes('edit-user-roles-checkboxes', currentRoles);

    callUi('#dialog-edit-user');
}

function renderRoleCheckboxes(containerId, selectedRoleIds) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    allRoles.forEach(roleId => {
        const checked = selectedRoleIds.includes(roleId) ? 'checked' : '';
        container.innerHTML += `
            <label class="checkbox" style="display: inline-block; margin: 4px 12px 4px 0;">
                <input type="checkbox" value="${roleId}" ${checked}>
                <span>${allRoleNames[roleId]}</span>
            </label>
        `;
    });
}

function previewUserImage(input) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById('edit-user-profilePicture-preview');
            preview.src = e.target.result;
            preview.style.display = '';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function saveUser() {
    const userId = document.getElementById('edit-user-id').value;
    const isEdit = !!userId;

    const firstName = document.getElementById('edit-user-firstName').value.trim();
    const lastName = document.getElementById('edit-user-lastName').value.trim();
    const email = document.getElementById('edit-user-email').value.trim();
    const birthDate = document.getElementById('edit-user-birthDate').value;
    const password = document.getElementById('edit-user-password').value;
    const passwordConfirm = document.getElementById('edit-user-passwordConfirm').value;
    const profilePicFile = document.getElementById('edit-user-profilePicture').files[0];

    if (!firstName || !email) {
        showAdminSnackbar(_('First name and e-mail are required'), true);
        return;
    }
    if (!isEdit && !password) {
        showAdminSnackbar(_('Password is required'), true);
        return;
    }
    if (password && password !== passwordConfirm) {
        showAdminSnackbar(_('Passwords do not match.'), true);
        return;
    }

    // Get selected roles
    const roleCheckboxes = document.querySelectorAll('#edit-user-roles-checkboxes input[type="checkbox"]:checked');
    const roleIds = Array.from(roleCheckboxes).map(cb => parseInt(cb.value));
    if (roleIds.length === 0) {
        showAdminSnackbar(_('User must have at least one role'), true);
        return;
    }

    const formData = new FormData();
    formData.append('firstName', firstName);
    formData.append('lastName', lastName);
    formData.append('email', email);
    if (birthDate) formData.append('birthDate', birthDate);
    if (password) formData.append('password', password);
    if (profilePicFile) formData.append('profilePicture', profilePicFile);
    if (!isEdit) formData.append('roleId', roleIds[0]); // Primary role for creation

    const url = isEdit ? `/api/v2/admin/users/${userId}` : '/api/v2/admin/users';
    const method = isEdit ? 'PUT' : 'POST';

    fetch(url, { method, body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                // If editing, also update roles
                const targetUserId = isEdit ? userId : result.data.id;
                const rolesFormData = new FormData();
                rolesFormData.append('roleIds', JSON.stringify(roleIds));

                return fetch(`/api/v2/admin/users/${targetUserId}/roles`, {
                    method: 'PUT',
                    body: rolesFormData
                }).then(r => r.json()).then(rolesResult => {
                    callUi('#dialog-edit-user');
                    showAdminSnackbar(result.message, false);
                    location.reload();
                });
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error saving user:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

function deleteUser() {
    const userId = document.getElementById('edit-user-id').value;
    if (!userId) return;

    if (!confirm(_('Do you really want to delete this entry? All associated entries will also be deleted.'))) {
        return;
    }

    fetch(`/api/v2/admin/users/${userId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                callUi('#dialog-edit-user');
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error deleting user:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

// --- User Roles (standalone dialog, kept for backwards compat) ---
function editUserRoles(userId, userName) {
    document.getElementById('edit-user-roles-user-id').value = userId;
    document.getElementById('edit-user-roles-title').textContent = userName;

    const currentRoles = userRolesMap[userId] || [];
    renderRoleCheckboxes('edit-user-roles-only-checkboxes', currentRoles);

    callUi('#dialog-edit-user-roles');
}

function saveUserRoles() {
    const userId = document.getElementById('edit-user-roles-user-id').value;
    const checkboxes = document.querySelectorAll('#edit-user-roles-only-checkboxes input[type="checkbox"]:checked');
    const roleIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    if (roleIds.length === 0) {
        showAdminSnackbar(_('User must have at least one role'), true);
        return;
    }

    const formData = new FormData();
    formData.append('roleIds', JSON.stringify(roleIds));

    fetch(`/api/v2/admin/users/${userId}/roles`, { method: 'PUT', body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                userRolesMap[userId] = roleIds;
                callUi('#dialog-edit-user-roles');
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error saving user roles:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

// --- Role Permissions ---
function editRolePermissions(roleId, roleName) {
    document.getElementById('edit-role-permissions-role-id').value = roleId;
    document.getElementById('edit-role-permissions-title').textContent = roleName;

    const currentPerms = rolePermissionsMap[roleId] || [];
    const container = document.getElementById('edit-role-permissions-checkboxes');
    container.innerHTML = '';

    // Separate per-list permissions (have listTypeID) from global permissions
    const listPerms = {}; // { listTypeID: { View: perm, Create: perm, ... } }
    const globalPerms = [];
    const actions = ['View', 'Create', 'Update', 'Delete'];

    allPermissions.forEach(perm => {
        if (perm.listTypeID) {
            if (!listPerms[perm.listTypeID]) listPerms[perm.listTypeID] = {};
            const action = perm.name.split(' ', 1)[0];
            listPerms[perm.listTypeID][action] = perm;
        } else {
            globalPerms.push(perm);
        }
    });

    // --- Per-list permissions as table ---
    if (Object.keys(listPerms).length > 0) {
        let html = `<h6 class="small">${_('List permissions')}</h6>`;
        html += `<div class="permission-table" style="overflow-x: auto;">`;
        html += `<table class="border" style="width: 100%;">`;
        html += `<thead><tr><th style="text-align: left;">${_('List')}</th>`;
        actions.forEach(action => {
            html += `<th style="text-align: center;">${_(action)}</th>`;
        });
        html += `</tr></thead><tbody>`;

        // Sort by list name
        const sortedListTypeIds = Object.keys(listPerms).sort((a, b) => {
            const nameA = listPerms[a].View ? listPerms[a].View.name.split(' ').slice(1).join(' ') : '';
            const nameB = listPerms[b].View ? listPerms[b].View.name.split(' ').slice(1).join(' ') : '';
            return nameA.localeCompare(nameB);
        });

        sortedListTypeIds.forEach(ltId => {
            const permsForList = listPerms[ltId];
            const listName = permsForList.View
                ? permsForList.View.name.split(' ').slice(1).join(' ')
                : (permsForList.Create ? permsForList.Create.name.split(' ').slice(1).join(' ') : '?');

            html += `<tr>`;
            html += `<td><strong>${listName}</strong></td>`;
            actions.forEach(action => {
                const perm = permsForList[action];
                if (perm) {
                    const checked = currentPerms.includes(perm.id) ? 'checked' : '';
                    const isView = action === 'View';
                    const viewPerm = permsForList['View'];
                    const viewChecked = viewPerm && currentPerms.includes(viewPerm.id);
                    const disabled = (!isView && !viewChecked) ? 'disabled' : '';

                    html += `<td style="text-align: center;">
                        <label class="checkbox">
                            <input type="checkbox" value="${perm.id}" ${checked} ${disabled}
                                data-list-type-id="${ltId}" data-action="${action}"
                                ${isView ? `onchange="toggleListViewDependency(this, '${ltId}')"` : ''}>
                            <span></span>
                        </label>
                    </td>`;
                } else {
                    html += `<td></td>`;
                }
            });
            html += `</tr>`;
        });

        html += `</tbody></table></div><br>`;
        container.innerHTML += html;
    }

    // --- Global permissions grouped by entity ---
    if (globalPerms.length > 0) {
        const groups = {};
        globalPerms.forEach(perm => {
            const parts = perm.name.split(' ');
            const entity = parts.length > 1 ? parts.slice(1).join(' ') : 'Other';
            if (!groups[entity]) groups[entity] = [];
            groups[entity].push(perm);
        });

        let html = `<h6 class="small">${_('General permissions')}</h6>`;
        Object.keys(groups).sort().forEach(entity => {
            html += `<div class="permission-group">`;
            html += `<p style="margin: 8px 0 4px; font-weight: 500; opacity: 0.7;">${entity}</p>`;
            groups[entity].forEach(perm => {
                const checked = currentPerms.includes(perm.id) ? 'checked' : '';
                html += `
                    <label class="checkbox" style="display: inline-block; margin: 4px 12px 4px 0;">
                        <input type="checkbox" value="${perm.id}" ${checked}>
                        <span>${perm.name}</span>
                    </label>
                `;
            });
            html += `</div>`;
        });
        container.innerHTML += html;
    }

    callUi('#dialog-edit-role-permissions');
}

function toggleListViewDependency(viewCheckbox, listTypeId) {
    const container = document.getElementById('edit-role-permissions-checkboxes');
    const dependentCheckboxes = container.querySelectorAll(
        `input[data-list-type-id="${listTypeId}"]:not([data-action="View"])`
    );

    if (!viewCheckbox.checked) {
        dependentCheckboxes.forEach(cb => {
            cb.checked = false;
            cb.disabled = true;
        });
    } else {
        dependentCheckboxes.forEach(cb => {
            cb.disabled = false;
        });
    }
}

function saveRolePermissions() {
    const roleId = document.getElementById('edit-role-permissions-role-id').value;
    const checkboxes = document.querySelectorAll('#edit-role-permissions-checkboxes input[type="checkbox"]:checked');
    const permissionIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    const formData = new FormData();
    formData.append('permissionIds', JSON.stringify(permissionIds));

    fetch(`/api/v2/admin/roles/${roleId}/permissions`, { method: 'PUT', body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                rolePermissionsMap[roleId] = permissionIds;
                callUi('#dialog-edit-role-permissions');
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error saving role permissions:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

// --- Create / Delete Roles ---
function createRole() {
    const roleName = document.getElementById('create-role-name').value.trim();
    if (!roleName) {
        showAdminSnackbar(_('Role name is required'), true);
        return;
    }

    const formData = new FormData();
    formData.append('roleName', roleName);

    fetch('/api/v2/admin/roles', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                callUi('#dialog-create-role');
                document.getElementById('create-role-name').value = '';
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error creating role:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

function deleteRole(roleId, roleName) {
    if (!confirm(_('Do you really want to delete this entry? All associated entries will also be deleted.'))) {
        return;
    }

    fetch(`/api/v2/admin/roles/${roleId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error deleting role:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

// --- Share Management ---
function revokeShareAdmin(shareId) {
    if (!confirm(_('Revoke this share link?'))) return;

    fetch(`/api/v2/admin/shares/${shareId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                const row = document.getElementById('share-row-' + shareId);
                if (row) row.remove();
                showAdminSnackbar(result.message, false);
            } else {
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            console.error('Error revoking share:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

// --- Snackbar ---
function showAdminSnackbar(message, isError) {
    const snackbar = document.getElementById('admin-snackbar');
    const text = document.getElementById('admin-snackbar-text');
    text.textContent = message;
    if (isError) {
        snackbar.className = 'snackbar error active';
    } else {
        snackbar.className = 'snackbar active';
    }
    setTimeout(() => snackbar.classList.remove('active'), 4000);
}
