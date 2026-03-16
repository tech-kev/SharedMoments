function updateListItem(id, value) {
    if (!navigator.onLine) {
        revertCheckbox(id, value ? 1 : 0);
        showSnackbar('list', true, 'error', _('You are offline'), null, false);
        return;
    }

    var value = value ? 1 : 0;

    var formData = new FormData();
    formData.append("content", value);
    formData.append("listType", window.listType);

    fetch("/api/v2/item/" + id, {
        method: "PUT",
        body: formData,
    })
        .then(async (response) => {
            try {
                const result = await response.json();
                if (result.status === "success") {
                    document.getElementById("div-render-list-items").innerHTML = result.data.rendered_items;
                    showSnackbar('list', true, 'green', result.message, result, false);
                } else {
                    // Revert checkbox: re-render from server response if available, otherwise toggle back
                    if (result.data && result.data.rendered_items) {
                        document.getElementById("div-render-list-items").innerHTML = result.data.rendered_items;
                    } else {
                        revertCheckbox(id, value);
                    }
                    showSnackbar('list', true, 'error', result.message, result, true);
                }
            } catch (error) {
                revertCheckbox(id, value);
                showSnackbar('list', true, 'error', _('Server not reachable'), null, false);
            }
        })
        .catch((error) => {
            revertCheckbox(id, value);
            if (error == "TypeError: Failed to fetch") {
                error = _('Server not reachable');
            }
            showSnackbar('list', true, 'error', error, null, false);
        });
}

function revertCheckbox(id, failedValue) {
    // Find the checkbox for this item and revert it
    const links = document.querySelectorAll('#div-render-list-items a.row');
    links.forEach(link => {
        if (link.getAttribute('onclick') && link.getAttribute('onclick').includes("'" + id + "'")) {
            const checkbox = link.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = failedValue === 1 ? false : true;
            }
        }
    });
}
