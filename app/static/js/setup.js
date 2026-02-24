// --- Setup State ---
var sm_edition = 'Couples';
var relationship_status = 1;
var users = [];
var settings = [];
let passkeyRegistered = false;

// --- Tab Navigation ---
function nextSetupTab() {
    var activeTab = document.querySelector('.page.active[id^="setup-tab-"]');
    var nextTab = activeTab.nextElementSibling;

    while (nextTab && !nextTab.classList.contains('page')) {
        nextTab = nextTab.nextElementSibling;
    }

    if (nextTab) {
        activeTab.classList.remove('active');
        nextTab.classList.add('active');
        document.getElementById('button-previous-setting-tab').style.display = '';
    }

    if (!nextTab || !nextTab.nextElementSibling || !nextTab.nextElementSibling.classList.contains('page')) {
        document.getElementById('button-next-setting-tab').style.display = 'none';
    }
}

function previousSetupTab() {
    var activeTab = document.querySelector('.page.active[id^="setup-tab-"]');
    var previousTab = activeTab.previousElementSibling;
    if (previousTab) {
        activeTab.classList.remove('active');
        previousTab.classList.add('active');
        document.getElementById('button-next-setting-tab').style.display = '';
    }

    if (!previousTab.previousElementSibling) {
        document.getElementById('button-previous-setting-tab').style.display = 'none';
    }
}

// --- Edition Selection ---
function showInfo(value) {
    var infoCouples = document.getElementById('info-couples');
    var infoFamily = document.getElementById('info-family');
    var infoFriends = document.getElementById('info-friends');

    sm_edition = value;

    if (value === 'Couples') {
        infoCouples.classList.add('active');
        infoFamily.classList.remove('active');
        infoFriends.classList.remove('active');
    } else if (value === 'Family') {
        infoCouples.classList.remove('active');
        infoFamily.classList.add('active');
        infoFriends.classList.remove('active');
    } else if (value === 'Friends') {
        infoCouples.classList.remove('active');
        infoFamily.classList.remove('active');
        infoFriends.classList.add('active');
    }
}

// --- Setup Completion ---
async function exitSetup() {
    if (users.length === 0) {
        showSnackbar('setup', true, 'error', _('Please add at least one user.'), null, false);
        return;
    }
    if (settings.length === 0) {
        showSnackbar('setup', true, 'error', _('Please save the settings first.'), null, false);
        return;
    }
    if (!confirm(_('Do you want to complete the setup?'))) {
        return;
    }

    for (let i = 0; i < users.length; i++) {
        let user = users[i];
        if (user.profilePicture instanceof File) {
            user.profilePicture = await uploadImage(user.profilePicture);
        }
    }

    var setupData = {
        sm_edition: sm_edition,
        users: users,
        settings: settings
    };

    var formData = new FormData();
    formData.append('setupData', JSON.stringify(setupData));

    fetch("/api/v2/setup", {
        method: "POST",
        body: formData,
    })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === "success") {
                    window.location.href = '/login';
                } else {
                    showSnackbar('setup', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('setup', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (error == "TypeError: Failed to fetch") {
                error = _('Server not reachable');
            }
            showSnackbar('setup', true, 'error', error, null, false);
        });
}

// --- Dialog Toggle (Setup-specific) ---
function callUi(id) {
    if (document.querySelector(id).classList.contains("active")) {
        document.querySelector(id).classList.remove("active");
        if (id === '#dialog-add-user') {
            document.getElementById("div-overlay-setup-add-user").classList.remove("active");
        } else if (id === '#edit-settings') {
            document.getElementById("div-overlay-setup-edit-settings").classList.remove("active");
            document.getElementById('title').closest('.s12').classList.add('hidden');
            document.getElementById('relationship-status').closest('.s6').classList.add('hidden');
            document.getElementById('anniversary').closest('.s6').classList.add('hidden');
            document.getElementById('engagement').closest('.s6').classList.add('hidden');
            document.getElementById('wedding-anniversary').closest('.s6').classList.add('hidden');
            document.getElementById('family-name').closest('.s12').classList.add('hidden');
            document.getElementById('friend-group-name').closest('.s12').classList.add('hidden');
        }
        document.body.style.overflow = "auto";
    } else {
        document.querySelector(id).classList.add("active");
        if (id === '#dialog-add-user') {
            document.getElementById("div-overlay-setup-add-user").classList.add("active");
            // Reset form fields
            ['firstname', 'lastname', 'email', 'birthdate', 'password', 'password-confirm'].forEach(f => document.getElementById('add-user-' + f).value = '');
            document.getElementById('add-user-profile-picture').value = '';
            document.getElementById('add-user-render-profile-picture').src = 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png';
            // First user defaults to Admin, subsequent users to Adult
            document.getElementById("add-user-role").value = users.length === 0 ? 'Admin' : 'Adult';
        } else if (id === '#edit-settings') {
            document.getElementById("div-overlay-setup-edit-settings").classList.add("active");
            if (sm_edition === 'Couples') {
                document.getElementById('title').closest('.hidden').classList.remove('hidden');
                document.getElementById('relationship-status').closest('.hidden').classList.remove('hidden');
                document.getElementById('anniversary').closest('.hidden').classList.remove('hidden');
            } else if (sm_edition === 'Family') {
                document.getElementById('family-name').closest('.hidden').classList.remove('hidden');
            } else if (sm_edition === 'Friends') {
                document.getElementById('friend-group-name').closest('.hidden').classList.remove('hidden');
            }
        }
        document.body.style.overflow = "hidden";
    }
}

// --- User Validation ---
function validateUserInputs(field) {
    const errorTexts = {
        firstname: _('Please enter your First name.'),
        lastname: _('Please enter your Last name.'),
        birthdate: _('Please enter your Birthdate.'),
        password: _('Please enter your Password.'),
        "password-confirm": _('Please repeat your Password.'),
        email: _('Please enter a valid email address.'),
        passwordsNotMatch: _('Passwords do not match.')
    };

    const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;

    if (field) {
        const element = document.getElementById("add-user-" + field);
        const helper = document.getElementById(field + "-helper");

        if (field === 'email') {
            if (!emailRegex.test(element.value)) {
                showErrorMessage(helper, errorTexts[field]);
                return false;
            } else {
                hideErrorMessage(helper);
            }
        } else if (field === 'password' || field === 'password-confirm') {
            if (document.getElementById("add-user-passwordless-login").checked === true) {
                hideErrorMessage(helper);
                return true;
            } else {
                if (document.getElementById("add-user-password").value !== document.getElementById("add-user-password-confirm").value) {
                    showErrorMessage(helper, errorTexts['passwordsNotMatch']);
                    return false;
                } else {
                    hideErrorMessage(document.getElementById("password-confirm-helper"));
                    hideErrorMessage(document.getElementById("password-helper"));
                }
            }
        }

        if (element.value === "") {
            showErrorMessage(helper, errorTexts[field]);
            return false;
        } else {
            hideErrorMessage(helper);
        }
        return true;
    } else {
        const fields = ['firstname', 'lastname', 'email', 'birthdate', 'password', 'password-confirm'];
        for (const f of fields) {
            if (validateUserInputs(f) === false) {
                return false;
            }
        }
        return true;
    }
}

function showErrorMessage(element, message) {
    element.classList.remove("helper");
    element.classList.add("error");
    element.textContent = message;
}

function hideErrorMessage(element) {
    element.classList.remove("error");
    element.classList.add("helper");
    element.textContent = "";
}

// --- User CRUD ---
async function saveUser() {
    var firstname = document.getElementById("add-user-firstname").value;
    var lastname = document.getElementById("add-user-lastname").value;
    var email = document.getElementById("add-user-email").value;
    var birthdate = document.getElementById("add-user-birthdate").value;
    var password = document.getElementById("add-user-password").value;
    var passwordConfirm = document.getElementById("add-user-password-confirm").value;
    var role = document.getElementById("add-user-role").value;

    if (users.some(user => user.email === email)) {
        showSnackbar('setup', true, 'error', _('E-Mail already in use. Please choose a different one.'), null, false);
        return;
    }

    if (!validateUserInputs()) {
        return;
    }

    var userCount = users.length > 0 ? Math.max(...users.map(user => user.userCount)) : 0;
    var profilePicture = document.getElementById('add-user-profile-picture').files[0];
    var profilePictureBase64 = await renderFile(profilePicture, 'return');

    if (!profilePicture) {
        profilePicture = 'https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png';
    }

    var userDiv = document.getElementById('users');
    var chip = document.createElement('button');
    chip.className = 'chip medium-elevate round white';
    chip.id = 'user-' + (userCount + 1);
    chip.onclick = function () {
        removeUser(userCount + 1);
    };
    var img = document.createElement('img');
    img.src = profilePictureBase64;
    var span = document.createElement('span');
    span.textContent = firstname;
    var i = document.createElement('i');
    i.textContent = 'close';
    chip.appendChild(img);
    chip.appendChild(span);
    chip.appendChild(i);
    userDiv.appendChild(chip);

    users.push({
        firstname: firstname,
        lastname: lastname,
        email: email,
        birthdate: birthdate,
        password: password,
        passwordConfirm: passwordConfirm,
        profilePicture: profilePicture,
        role: role,
        userCount: userCount + 1
    });
    updateButtonLayout();
    callUi('#dialog-add-user');
}

function removeUser(userCount) {
    var userDiv = document.getElementById('users');
    var user = document.getElementById('user-' + userCount);
    userDiv.removeChild(user);
    users = users.filter(user => user.userCount !== userCount);
    updateButtonLayout();
}

// --- File Rendering ---
function renderFile(file, action) {
    if (!file) return;
    if (action === 'return') {
        return new Promise((resolve, reject) => {
            var reader = new FileReader();
            reader.onload = function (e) {
                resolve(e.target.result);
            };
            reader.readAsDataURL(file);
        });
    } else if (action === 'preview') {
        var reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('add-user-render-profile-picture').src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
}

// --- Layout Helpers ---
function updateButtonLayout() {
    var usersDiv = document.getElementById('users');
    const buttons = usersDiv.querySelectorAll('button');

    usersDiv.querySelectorAll('br').forEach(br => br.remove());

    if (buttons.length > 1) {
        let firstButtonInRow = buttons[0];
        for (let i = 1; i < buttons.length; i++) {
            const currentButton = buttons[i];
            if (currentButton.offsetTop > firstButtonInRow.offsetTop) {
                usersDiv.insertBefore(document.createElement('br'), currentButton);
                usersDiv.insertBefore(document.createElement('br'), currentButton);
                firstButtonInRow = currentButton;
            }
        }
    }

    if (buttons.length > 0) {
        document.getElementById('p-added-users').style.display = '';
        document.getElementById('p-add-user-text').style.display = 'none';
    } else {
        document.getElementById('p-added-users').style.display = 'none';
        document.getElementById('p-add-user-text').style.display = '';
    }
    updateExitButton();
}

function updateExitButton() {
    const hasUsers = users.length > 0;
    const hasSettings = settings.length > 0;
    document.getElementById('button-exit-setup').disabled = !(hasUsers && hasSettings);
}

// --- Settings ---
function saveSettings() {
    var title = document.getElementById('title').value;
    var familyName = document.getElementById('family-name').value;
    var friendGroupName = document.getElementById('friend-group-name').value;
    var anniversary = document.getElementById('anniversary').value;
    var engagement = document.getElementById('engagement').value;
    var weddingAnniversary = document.getElementById('wedding-anniversary').value;
    var relationshipStatus = document.getElementById('relationship-status').value;

    settings = [{
        title: title,
        familyName: familyName,
        friendGroupName: friendGroupName,
        anniversary: anniversary,
        engagement: engagement,
        weddingAnniversary: weddingAnniversary,
        relationshipStatus: relationshipStatus
    }];

    updateExitButton();
    callUi('#edit-settings');
}

// --- Image Upload ---
function uploadImage(file) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("staticMedia", true);

    return fetch('/api/v2/upload', {
        method: "POST",
        body: formData,
    })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === "success") {
                    return result.data.filename;
                } else {
                    showSnackbar('setup', true, 'error', result.message, result, true);
                    return null;
                }
            } catch (error) {
                if (error == "TypeError: Failed to fetch") {
                    error = _('Server not reachable');
                }
                showSnackbar('setup', true, 'error', error, null, false);
                return null;
            }
        })
        .catch((error) => {
            if (error == "TypeError: Failed to fetch") {
                error = _('Server not reachable');
            }
            showSnackbar('setup', true, 'error', error, null, false);
            return null;
        });
}

// --- WebAuthn / Passkey ---
function base64urlToUint8Array(base64urlString) {
    const padding = '='.repeat((4 - (base64urlString.length % 4)) % 4);
    const base64 = (base64urlString + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

async function registerPasskey() {
    if (!navigator.credentials || !navigator.credentials.create) {
        var error_data = {
            data: {
                error_code: "webauthn_not_supported",
                error_message: "WebAuthn is not supported in this browser. This may be due to disabled browser settings, an insecure connection, or outdated software."
            }
        };
        showSnackbar('setup', true, 'error', "WebAuthn is not supported in this browser.", error_data, true);
        return;
    }

    const formData = new FormData();
    formData.append("email", document.getElementById("add-user-email").value);
    formData.append("name", document.getElementById("add-user-firstname").value);

    const response = await fetch("/webauthn/register", {
        method: "POST",
        body: formData,
    });
    const result = await response.json();

    if (result.status === "success") {
        const publicKeyOptions = JSON.parse(result.data);

        try {
            publicKeyOptions.challenge = base64urlToUint8Array(publicKeyOptions.challenge);
            publicKeyOptions.user.id = base64urlToUint8Array(publicKeyOptions.user.id);

            const credential = await navigator.credentials.create({ publicKey: publicKeyOptions });

            const credentialData = {
                id: credential.id,
                rawId: Array.from(new Uint8Array(credential.rawId)),
                type: credential.type,
                response: {
                    attestationObject: Array.from(new Uint8Array(credential.response.attestationObject)),
                    clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON))
                }
            };

            const verifyResponse = await fetch("/webauthn/register/verify", {
                method: "POST",
                body: JSON.stringify(credentialData),
                headers: { 'Content-Type': 'application/json' }
            });
            const verifyResult = await verifyResponse.json();

            if (verifyResult.status === "success") {
                showSnackbar('setup', true, 'green', verifyResult.message, null, false);
                passkeyRegistered = true;
            } else {
                showSnackbar('setup', true, 'error', verifyResult.message, verifyResult, true);
            }
        } catch (error) {
            var error_data = {
                data: {
                    error_code: "credential_creation_failed",
                    error_message: error
                }
            };
            showSnackbar('setup', true, 'error', "Error during credential creation.", error_data, true);
        }
    } else {
        showSnackbar('setup', true, 'error', result.message, result, true);
    }
}
