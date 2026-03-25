let currentTimelineItemId = null;

// Auto-scroll timeline to newest entry (rightmost) on initial load
window.addEventListener('load', () => {
    const timelineNav = document.querySelector('#div-render-timeline-card article nav');
    if (timelineNav) {
        timelineNav.scrollLeft = timelineNav.scrollWidth;
    }
});

function showTimelineItemDetails(btn) {
    currentTimelineItemId = btn.dataset.id;
    document.getElementById('timeline-detail-title').textContent = btn.dataset.title || '';
    document.getElementById('timeline-detail-date').textContent = btn.dataset.date || '';
    document.getElementById('div-details-timeline-item').textContent = btn.dataset.content || '';
    callUi('#dialog-details-timeline-item');
}

function editTimelineItem() {
    callUi('#dialog-details-timeline-item');

    const btn = document.querySelector(`[data-id="${currentTimelineItemId}"]`);
    document.getElementById('edit-timeline-item-id').value = currentTimelineItemId;
    document.getElementById('edit-timeline-item-title').value = btn.dataset.title || '';
    document.getElementById('edit-timeline-item-content').value = btn.dataset.content || '';
    document.getElementById('edit-timeline-item-date').value = btn.dataset.dateYmd || '';

    callUi('#dialog-edit-timeline-item');
}

function saveEditedTimelineItem(btn) {
    if (!navigator.onLine) {
        showSnackbar('home', true, 'error', _('You are offline'), null, false);
        return;
    }
    btnLoading(btn);

    const id = document.getElementById('edit-timeline-item-id').value;
    const formData = new FormData();
    formData.append('title', document.getElementById('edit-timeline-item-title').value);
    formData.append('content', document.getElementById('edit-timeline-item-content').value);
    formData.append('contentType', 'text');
    formData.append('listType', 2);
    formData.append('dateCreated', document.getElementById('edit-timeline-item-date').value);

    fetch(`/api/v2/item/${id}`, { method: 'PUT', body: formData })
        .then(async (response) => {
            try {
                const result = await response.json();
                btnReset(btn);
                if (result.status === 'success') {
                    callUi('#dialog-edit-timeline-item');
                    document.getElementById('div-render-timeline-card').innerHTML = result.data.rendered_items;
                    showSnackbar('home', true, 'green', result.message, null, false);
                } else {
                    showSnackbar('home', true, 'error', result.message, result, true);
                }
            } catch (error) {
                btnReset(btn);
                showSnackbar('home', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            btnReset(btn);
            if (error == "TypeError: Failed to fetch") {
                error = _('Server not reachable');
            }
            showSnackbar('home', true, 'error', error, null, false);
        });
}

function deleteTimelineItem(btn) {
    if (!navigator.onLine) {
        showSnackbar('home', true, 'error', _('You are offline'), null, false);
        return;
    }
    btnLoading(btn);

    const formData = new FormData();
    formData.append('ids', currentTimelineItemId);
    formData.append('listType', 2);

    fetch('/api/v2/items', { method: 'DELETE', body: formData })
        .then(async (response) => {
            try {
                const result = await response.json();
                btnReset(btn);
                if (result.status === 'success') {
                    callUi('#dialog-details-timeline-item');
                    document.getElementById('div-render-timeline-card').innerHTML = result.data.rendered_items;
                    showSnackbar('home', true, 'green', result.message, null, false);
                } else {
                    showSnackbar('home', true, 'error', result.message, result, true);
                }
            } catch (error) {
                btnReset(btn);
                showSnackbar('home', true, 'error', error, null, false);
            }
        })
        .catch((error) => {
            btnReset(btn);
            if (error == "TypeError: Failed to fetch") {
                error = _('Server not reachable');
            }
            showSnackbar('home', true, 'error', error, null, false);
        });
}
