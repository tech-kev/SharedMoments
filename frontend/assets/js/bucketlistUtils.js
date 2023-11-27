/*
# Copyright (C) 2023 techkev
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
*/

async function fetchBucketListItems() {

	const bucketlist = document.querySelector(".bucketlist_col");
	fetch(API_ENDPOINTS.bucketlist, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadBucketlistError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				bucketlist.innerHTML = ''; // Leere Bucketlist

				data.data.forEach((item, index) => {
					const listItem = document.createElement("li");
					listItem.classList.add("collection-item");

					const label = document.createElement("label");
					const checkbox = document.createElement("input");
					checkbox.type = "checkbox";
					checkbox.checked = item.done;
					checkbox.classList.add('filled-in');
					const text = document.createElement("span");
					text.innerText = item.title;

					label.appendChild(checkbox);
					label.appendChild(text);
					listItem.appendChild(label);

					const deleteBtn = document.createElement("i");
					deleteBtn.classList.add("material-icons", "small", "right", "delete-button-bucketlist");
					deleteBtn.style.color = "red";
					deleteBtn.style.cursor = "pointer";
					deleteBtn.id = `delete-btn-${item.id}`;
					deleteBtn.innerText = "delete";
					listItem.appendChild(deleteBtn);

					const hiddenId = document.createElement("input");
					hiddenId.type = "hidden";
					hiddenId.value = item.id;
					listItem.appendChild(hiddenId);

					bucketlist.appendChild(listItem);

					checkbox.addEventListener("change", function() {
						updateBucketListItem(item.id, item.title, this.checked);
					});

					deleteBtn.addEventListener("click", function() {
						const itemId = this.id.split("-")[2];
						removeBucketListItem(itemId);
					});
				});

				const loaderContainer = document.querySelector('.loader-container');
				loaderContainer.classList.remove('active'); // Loader schließen, falls aktiv
				document.body.style.overflow = "auto"; // Overflow auf auto, da beim Modal Close dieser auf hidden bleibt

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);

				const loaderContainer = document.querySelector('.loader-container');
				loaderContainer.classList.remove('active'); // Loader schließen, falls aktiv
				document.body.style.overflow = "auto"; // Overflow auf auto, da beim Modal Close dieser auf hidden bleibt
			}
		})
		.catch(error => {
			var errmessage = LCloadBucketlistError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);

			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active'); // Loader schließen, falls aktiv
			document.body.style.overflow = "auto"; // Overflow auf auto, da beim Modal Close dieser auf hidden bleibt
		});
}

function initNewBucketListItemModal() {
	const modalElement = document.querySelector('#newbucketlistitemmodal');
	const modalInstance = M.Modal.init(modalElement);

	const speichernButton = document.querySelector('.modal-footer .bucketlist_save_button');
	speichernButton.addEventListener('click', createNewBucketListItem);

	const inputField = document.getElementById('bucketlist_titel');
	inputField.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			createNewBucketListItem(event);
		}
	})
}

async function createNewBucketListItem(event) {
	event.preventDefault();

	const title = document.querySelector('#bucketlist_titel')
		.value;

	if (title.trim() === '') {
		callToast('error', LCenterNameForEntry);
		return false;
	}

	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	const formdata = new FormData();
	formdata.append('title', title);

	fetch(API_ENDPOINTS.bucketlist, {
			method: "POST",
			body: formdata
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === "success") {

				fetchBucketListItems();
				const modalElement = document.querySelector('#newbucketlistitemmodal');
				const modalInstance = M.Modal.init(modalElement);
				modalInstance.close();

				document.getElementById('bucketlist_titel').value = ''; // Titel leeren
				document.body.style.overflow = "auto";

			} else {
				const message = data.message;
				callToast('error', message);
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active');
		});
}

async function updateBucketListItem(itemId, title, done) {
	const formdata = new FormData();
	formdata.append('title', title);
	formdata.append('done', done ? 1 : 0);
	formdata.append('item_id', itemId);

	fetch(API_ENDPOINTS.bucketlist + "/" + itemId, {
			method: "PUT",
			body: formdata
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === "success") {

				//const message = data.message;
				//callToast('info', message);
			} else {
				const message = data.message;
				callToast('error', message);
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function removeBucketListItem(itemId) {

	const confirmed = window.confirm(LCwantDeleteEntry);
	if (!confirmed) {
		return;
	}

	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	fetch(API_ENDPOINTS.bucketlist + "/" + itemId, {
			method: "DELETE",
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === "success") {

				fetchBucketListItems();

			} else {
				const message = data.message;
				callToast('error', message);
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active');
		});
}

async function loadBucketlistLocales() {

	fetch(API_ENDPOINTS.locales, {
			method: 'GET'
		})
		.then(response => response.json())
		.then(data => {

			document.getElementById('bucketlistTitle').textContent = data.bucketlist_html.title;
			document.getElementById('add-btn').textContent = data.buttons.add;
			document.getElementById('newBucketlistEntryTitle').textContent = data.bucketlist_html.new_bucketlist_entry;
			document.getElementById('bucketlistTitleLabel').textContent = data.various.title;
			document.getElementById('cancelButton').textContent = data.buttons.cancel;
			document.getElementById('saveButton').textContent = data.buttons.save;
		})
		.catch(error => {
			const errmessage = error + '! ' + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}