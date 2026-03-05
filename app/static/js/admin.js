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
        // Hide Child role for Couples edition
        if (typeof currentEdition !== 'undefined' && currentEdition === 'couples' && allRoleNames[roleId] === 'Child') return;
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

function saveUser(btn) {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
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

    btnLoading(btn);

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
                    btnReset(btn);
                    callUi('#dialog-edit-user');
                    showAdminSnackbar(result.message, false);
                    location.reload();
                });
            } else {
                btnReset(btn);
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            btnReset(btn);
            console.error('Error saving user:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

function deleteUser() {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
    const userId = document.getElementById('edit-user-id').value;
    if (!userId) return;

    if (!confirm(_('Do you really want to delete this entry? All associated entries will also be deleted.'))) {
        return;
    }

    const btn = document.getElementById('btn-delete-user');
    btnLoading(btn);

    fetch(`/api/v2/admin/users/${userId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                btnReset(btn);
                callUi('#dialog-edit-user');
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                btnReset(btn);
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            btnReset(btn);
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

function saveUserRoles(btn) {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
    const userId = document.getElementById('edit-user-roles-user-id').value;
    const checkboxes = document.querySelectorAll('#edit-user-roles-only-checkboxes input[type="checkbox"]:checked');
    const roleIds = Array.from(checkboxes).map(cb => parseInt(cb.value));

    if (roleIds.length === 0) {
        showAdminSnackbar(_('User must have at least one role'), true);
        return;
    }

    btnLoading(btn);

    const formData = new FormData();
    formData.append('roleIds', JSON.stringify(roleIds));

    fetch(`/api/v2/admin/users/${userId}/roles`, { method: 'PUT', body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                userRolesMap[userId] = roleIds;
                btnReset(btn);
                callUi('#dialog-edit-user-roles');
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                btnReset(btn);
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            btnReset(btn);
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

    const actions = ['View', 'Create', 'Update', 'Delete'];
    const listPerms = {};
    const globalPerms = [];

    allPermissions.forEach(perm => {
        if (perm.listTypeID) {
            if (!listPerms[perm.listTypeID]) listPerms[perm.listTypeID] = {};
            const action = perm.name.split(' ', 1)[0];
            listPerms[perm.listTypeID][action] = perm;
        } else {
            globalPerms.push(perm);
        }
    });

    // --- One unified table ---
    const cols = ['View', 'Create', 'Update', 'Delete'];
    let html = `<table class="border permission-matrix" style="width: 100%;">`;
    html += `<thead><tr><th style="text-align: left;"></th>`;
    cols.forEach(c => { html += `<th style="text-align: center;">${_(c)}</th>`; });
    html += `</tr></thead><tbody>`;

    // Helper: find View/Read perm for same entity
    const findViewPerm = (perm) => {
        const entity = perm.name.split(' ').slice(1).join(' ');
        return allPermissions.find(p =>
            p.listTypeID === perm.listTypeID &&
            p.name.split(' ').slice(1).join(' ') === entity &&
            (p.name.split(' ', 1)[0] === 'View' || p.name.split(' ', 1)[0] === 'Read')
        );
    };

    // Helper for checkbox cell
    const cell = (perm) => {
        if (!perm) return '<td></td>';
        const checked = currentPerms.includes(perm.id) ? 'checked' : '';
        const action = perm.name.split(' ', 1)[0];
        const needsView = ['Create', 'Update', 'Delete'].includes(action);
        const viewPerm = needsView ? findViewPerm(perm) : null;
        const disabled = needsView && viewPerm && !currentPerms.includes(viewPerm.id) ? 'disabled' : '';
        return `<td style="text-align: center;">
            <label class="checkbox">
                <input type="checkbox" value="${perm.id}" ${checked} ${disabled}
                    onchange="togglePermission(${roleId}, ${perm.id}, this.checked)">
                <span></span>
            </label>
        </td>`;
    };

    // Section: Lists
    html += `<tr><td colspan="5" style="padding-top: 16px;"><strong>${_('Lists')}</strong></td></tr>`;
    const sortedIds = Object.keys(listPerms).sort((a, b) => {
        const nameA = listPerms[a].View ? listPerms[a].View.name.split(' ').slice(1).join(' ') : '';
        const nameB = listPerms[b].View ? listPerms[b].View.name.split(' ').slice(1).join(' ') : '';
        return nameA.localeCompare(nameB);
    });
    sortedIds.forEach(ltId => {
        const p = listPerms[ltId];
        const name = p.View ? p.View.name.split(' ').slice(1).join(' ')
            : (p.Create ? p.Create.name.split(' ').slice(1).join(' ') : '?');
        html += `<tr><td style="padding-left: 16px;">${_(name)}</td>`;
        cols.forEach(action => { html += cell(p[action]); });
        html += `</tr>`;
    });

    // Section: General (CRUD-based global perms)
    const crudGroups = {};
    const standalonePerms = [];
    globalPerms.forEach(perm => {
        const action = perm.name.split(' ', 1)[0];
        if (['Create', 'Read', 'Update', 'Delete'].includes(action)) {
            const entity = perm.name.split(' ').slice(1).join(' ');
            if (!crudGroups[entity]) crudGroups[entity] = {};
            crudGroups[entity][action] = perm;
        } else {
            standalonePerms.push(perm);
        }
    });

    if (Object.keys(crudGroups).length > 0) {
        html += `<tr><td colspan="5" style="padding-top: 16px;"><strong>${_('General')}</strong></td></tr>`;
        Object.keys(crudGroups).sort().forEach(entity => {
            const g = crudGroups[entity];
            html += `<tr><td style="padding-left: 16px;">${entity}</td>`;
            // Map Read→View column position
            html += cell(g['View'] || g['Read']);
            html += cell(g['Create']);
            html += cell(g['Update']);
            html += cell(g['Delete']);
            html += `</tr>`;
        });
    }

    // Section: Special (standalone perms)
    if (standalonePerms.length > 0) {
        html += `<tr><td colspan="5" style="padding-top: 16px;"><strong>${_('Special')}</strong></td></tr>`;
        standalonePerms.sort((a, b) => a.name.localeCompare(b.name)).forEach(perm => {
            const checked = currentPerms.includes(perm.id) ? 'checked' : '';
            html += `<tr><td style="padding-left: 16px;">${_(perm.name)}</td>`;
            html += `<td colspan="4" style="text-align: center;">
                <label class="checkbox">
                    <input type="checkbox" value="${perm.id}" ${checked}
                        onchange="togglePermission(${roleId}, ${perm.id}, this.checked)">
                    <span></span>
                </label>
            </td></tr>`;
        });
    }

    html += `</tbody></table>`;
    container.innerHTML = html;

    callUi('#dialog-edit-role-permissions');
}

function togglePermission(roleId, permId, checked) {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
    const currentPerms = rolePermissionsMap[roleId] || [];

    // Find the toggled permission
    const perm = allPermissions.find(p => p.id === permId);
    if (perm) {
        const action = perm.name.split(' ', 1)[0];
        const entity = perm.name.split(' ').slice(1).join(' ');
        const siblings = allPermissions.filter(p =>
            p.listTypeID === perm.listTypeID &&
            p.name.split(' ').slice(1).join(' ') === entity
        );

        if (checked && (action === 'View' || action === 'Read')) {
            // Enabling View → enable CUD checkboxes
            siblings.forEach(p => {
                const a = p.name.split(' ', 1)[0];
                if (['Create', 'Update', 'Delete'].includes(a)) {
                    const cb = document.querySelector(`#edit-role-permissions-checkboxes input[value="${p.id}"]`);
                    if (cb) cb.disabled = false;
                }
            });
        } else if (!checked && (action === 'View' || action === 'Read')) {
            // Deactivating View/Read → uncheck + disable CUD
            siblings.forEach(p => {
                const a = p.name.split(' ', 1)[0];
                if (['Create', 'Update', 'Delete'].includes(a)) {
                    const cb = document.querySelector(`#edit-role-permissions-checkboxes input[value="${p.id}"]`);
                    if (cb) { cb.checked = false; cb.disabled = true; }
                }
            });
        }
    }

    // Collect all checked checkboxes as new permission set
    const allChecked = document.querySelectorAll('#edit-role-permissions-checkboxes input[type="checkbox"]:checked');
    const newPerms = Array.from(allChecked).map(cb => parseInt(cb.value));

    const formData = new FormData();
    formData.append('permissionIds', JSON.stringify(newPerms));

    fetch(`/api/v2/admin/roles/${roleId}/permissions`, { method: 'PUT', body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                rolePermissionsMap[roleId] = newPerms;
            } else {
                showAdminSnackbar(result.message, true);
                editRolePermissions(roleId, document.getElementById('edit-role-permissions-title').textContent);
            }
        })
        .catch(error => {
            showAdminSnackbar(_('Server not reachable'), true);
            editRolePermissions(roleId, document.getElementById('edit-role-permissions-title').textContent);
        });
}

// --- Create / Delete Roles ---
function createRole(btn) {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
    const roleName = document.getElementById('create-role-name').value.trim();
    if (!roleName) {
        showAdminSnackbar(_('Role name is required'), true);
        return;
    }

    btnLoading(btn);

    const formData = new FormData();
    formData.append('roleName', roleName);

    fetch('/api/v2/admin/roles', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                btnReset(btn);
                callUi('#dialog-create-role');
                document.getElementById('create-role-name').value = '';
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                btnReset(btn);
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            btnReset(btn);
            console.error('Error creating role:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

function deleteRole(roleId, roleName, btn) {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
    if (!confirm(_('Do you really want to delete this entry? All associated entries will also be deleted.'))) {
        return;
    }

    btnLoading(btn);

    fetch(`/api/v2/admin/roles/${roleId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                btnReset(btn);
                showAdminSnackbar(result.message, false);
                location.reload();
            } else {
                btnReset(btn);
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            btnReset(btn);
            console.error('Error deleting role:', error);
            showAdminSnackbar(_('Server not reachable'), true);
        });
}

// --- Share Management ---
function revokeShareAdmin(shareId, btn) {
    if (!navigator.onLine) {
        showAdminSnackbar(_('You are offline'), true);
        return;
    }
    if (!confirm(_('Revoke this share link?'))) return;

    btnLoading(btn);

    fetch(`/api/v2/admin/shares/${shareId}`, { method: 'DELETE' })
        .then(response => response.json())
        .then(result => {
            if (result.status === 'success') {
                btnReset(btn);
                const row = document.getElementById('share-row-' + shareId);
                if (row) row.remove();
                const sharesTab = document.getElementById('tab-shares');
                if (sharesTab && !sharesTab.querySelector('[id^="share-row-"]')) {
                    sharesTab.innerHTML = '<article class="medium middle-align center-align primary-container"><div>' +
                        '<i class="extra">link_off</i>' +
                        '<h5>' + _('No active shares') + '</h5>' +
                        '<p>' + _('Share links will appear here once created.') + '</p>' +
                        '</div></article>';
                }
                showAdminSnackbar(result.message, false);
            } else {
                btnReset(btn);
                showAdminSnackbar(result.message, true);
            }
        })
        .catch(error => {
            btnReset(btn);
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
