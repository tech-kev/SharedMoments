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

async function fetchFilmListItems() {

	const filmlist = document.querySelector(".filmlist_col");

	fetch(API_ENDPOINTS.filmlist, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadFilmlistError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

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
					deleteBtn.classList.add("material-icons", "small", "right", "delete-button-filmlist");
					deleteBtn.style.color = "red";
					deleteBtn.style.cursor = "pointer";
					deleteBtn.id = `delete-btn-${item.id}`;
					deleteBtn.innerText = "delete";
					listItem.appendChild(deleteBtn);

					const hiddenId = document.createElement("input");
					hiddenId.type = "hidden";
					hiddenId.value = item.id;
					listItem.appendChild(hiddenId);

					filmlist.appendChild(listItem);

					checkbox.addEventListener("change", function() {
						updateFilmListItem(item.id, item.title, this.checked);
					});

					deleteBtn.addEventListener("click", function() {
						const itemId = this.id.split("-")[2];
						removeFilmListItem(itemId);
					});
				});
			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadFilmlistError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

function initNewFilmListItemModal() {
	const modalElement = document.querySelector('#newfilmlistitemmodal');
	const modalInstance = M.Modal.init(modalElement);

	const speichernButton = document.querySelector('.modal-footer .filmlist_save_button');
	speichernButton.addEventListener('click', createNewFilmListItem);

	const inputField = document.getElementById('filmlist_titel');
	inputField.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			createNewFilmListItem(event);
		}
	})
}

async function createNewFilmListItem(event) {
	event.preventDefault();
	const title = document.querySelector('#filmlist_titel').value;

	if (title.trim() === '') {
		callToast('error', LCenterFilmname);
		return false;
	}

	const formdata = new FormData();
	formdata.append('title', title);

	fetch(API_ENDPOINTS.filmlist, {
			method: "POST",
			body: formdata
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === "success") {

				location.reload();

			} else {
				const message = data.message;
				callToast('error', message);
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
			reject(false);
		});
}

async function updateFilmListItem(itemId, title, done) {

	const formdata = new FormData();
	formdata.append('title', title);
	formdata.append('done', done ? 1 : 0);
	formdata.append('item_id', itemId);

	fetch(API_ENDPOINTS.filmlist + "/" + itemId, {
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
			reject(false);
		});
}

async function removeFilmListItem(itemId) {

	const confirmed = window.confirm(LCwantDeleteEntry);
	if (!confirmed) {
		return;
	}

	fetch(API_ENDPOINTS.filmlist + "/" + itemId, {
			method: "DELETE",
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === "success") {

				//const message = data.message;
				//callToast('info', message);
				location.reload();

			} else {
				const message = data.message;
				callToast('error', message);
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
			reject(false);
		});
}