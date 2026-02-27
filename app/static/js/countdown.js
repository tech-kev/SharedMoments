let countdownIntervals = [];

function initCountdowns() {
    // Clear previous intervals
    countdownIntervals.forEach(id => clearInterval(id));
    countdownIntervals = [];

    document.querySelectorAll('.countdown-timer[data-target]').forEach(el => {
        startCountdown(el);
    });
}

function startCountdown(el) {
    const targetDate = new Date(el.dataset.target).getTime();
    const daysEl = el.querySelector('[data-unit="days"]');
    const hoursEl = el.querySelector('[data-unit="hours"]');
    const minutesEl = el.querySelector('[data-unit="minutes"]');
    const secondsEl = el.querySelector('[data-unit="seconds"]');

    function update() {
        const now = Date.now();
        const diff = targetDate - now;

        if (diff <= 0) {
            daysEl.textContent = '0';
            hoursEl.textContent = '0';
            minutesEl.textContent = '0';
            secondsEl.textContent = '0';
            return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        daysEl.textContent = days;
        hoursEl.textContent = hours;
        minutesEl.textContent = minutes;
        secondsEl.textContent = seconds;
    }

    update();
    const intervalId = setInterval(update, 1000);
    countdownIntervals.push(intervalId);
}

function saveNewCountdown() {
    if (!navigator.onLine) {
        showSnackbar('home', true, 'error', _('You are offline'), null, false);
        return;
    }

    const title = document.getElementById('input-create-countdown-title').value;
    const date = document.getElementById('input-create-countdown-date').value;

    if (!title || !date) {
        showSnackbar('home', true, 'error', _('Please fill in all fields'), null, false);
        return;
    }

    const formData = new FormData();
    formData.append('title', title);
    formData.append('contentType', 'countdown');
    formData.append('listType', window.countdownListTypeId);
    formData.append('dateCreated', date);

    fetch('/api/v2/items', { method: 'POST', body: formData })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === 'success') {
                    callUi('#dialog-create-countdown');
                    document.getElementById('div-render-countdown-card').innerHTML = result.data.rendered_items;
                    document.getElementById('input-create-countdown-title').value = '';
                    document.getElementById('input-create-countdown-date').value = '';
                    initCountdowns();
                    showSnackbar('home', true, 'green', result.message, null, false);
                } else {
                    showSnackbar('home', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('home', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (String(error) === 'TypeError: Failed to fetch') {
                error = _('Server not reachable');
            }
            showSnackbar('home', true, 'error', error, null, false);
        });
}

function editCountdown(btn) {
    document.getElementById('input-edit-countdown-id').value = btn.dataset.id;
    document.getElementById('input-edit-countdown-title').value = btn.dataset.title;
    document.getElementById('input-edit-countdown-date').value = btn.dataset.date;
    callUi('#dialog-edit-countdown');
}

function saveEditedCountdown() {
    if (!navigator.onLine) {
        showSnackbar('home', true, 'error', _('You are offline'), null, false);
        return;
    }

    const id = document.getElementById('input-edit-countdown-id').value;
    const formData = new FormData();
    formData.append('title', document.getElementById('input-edit-countdown-title').value);
    formData.append('contentType', 'countdown');
    formData.append('listType', window.countdownListTypeId);
    formData.append('dateCreated', document.getElementById('input-edit-countdown-date').value);

    fetch(`/api/v2/item/${id}`, { method: 'PUT', body: formData })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === 'success') {
                    callUi('#dialog-edit-countdown');
                    document.getElementById('div-render-countdown-card').innerHTML = result.data.rendered_items;
                    initCountdowns();
                    showSnackbar('home', true, 'green', result.message, null, false);
                } else {
                    showSnackbar('home', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('home', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (String(error) === 'TypeError: Failed to fetch') {
                error = _('Server not reachable');
            }
            showSnackbar('home', true, 'error', error, null, false);
        });
}

function deleteCountdown() {
    if (!navigator.onLine) {
        showSnackbar('home', true, 'error', _('You are offline'), null, false);
        return;
    }

    const id = document.getElementById('input-edit-countdown-id').value;
    const formData = new FormData();
    formData.append('ids', id);
    formData.append('listType', window.countdownListTypeId);

    fetch('/api/v2/items', { method: 'DELETE', body: formData })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === 'success') {
                    callUi('#dialog-edit-countdown');
                    document.getElementById('div-render-countdown-card').innerHTML = result.data.rendered_items;
                    initCountdowns();
                    showSnackbar('home', true, 'green', result.message, null, false);
                } else {
                    showSnackbar('home', true, 'error', result.message, result, true);
                }
            } catch (error) {
                showSnackbar('home', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            if (String(error) === 'TypeError: Failed to fetch') {
                error = _('Server not reachable');
            }
            showSnackbar('home', true, 'error', error, null, false);
        });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initCountdowns);
