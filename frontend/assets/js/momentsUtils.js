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

async function fetchMomentsItems() {
	const timeline = document.getElementById("timeline");

	fetch(API_ENDPOINTS.moments, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadMomentsError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				timeline.innerHTML = '';

				if (data.data.length === 0) {
					timeline.style.justifyContent = "center";
					timeline.innerHTML = `
             <a class="waves-effect waves-light btn-small modal-trigger" href="#newmomentitemmodal">${LCcreateNewMoment}</a>
             `;
				} else {
					const momentList = data.data.map((moment, index) => {
						const date = new Date(moment.date);
						const options = {
							year: 'numeric',
							month: '2-digit',
							day: '2-digit'
						};
						const formattedDate = date.toLocaleDateString(LClocale, options);

						const hasNext = index + 1 < data.data.length;
						const nextLink = hasNext ?
							"" :
							`<a class="slick-next slick-arrow slick-disabled modal-trigger" style="display: block;" href="#newmomentitemmodal"></a>`;
						return `
                     <li class="li complete">
                     <a class="editbtnMoments" style="display: none">
                     <i class="material-icons">edit</i>
                     </a>
                         <div class="timestamp">
                             <span class="date">${formattedDate}</span>
                         </div>
                         <div class="status">
                             <p>${moment.title}</p>
                             ${nextLink}
                         </div>
                     </li>
                 `;

					}).join("");

					timeline.innerHTML = momentList;


					const editButtons = document.querySelectorAll('.editbtnMoments');
					editButtons.forEach((editButton, index) => {
						editButton.addEventListener('click', () => {
							editMomentItem(data.data[index].id);
						});
					});
				}

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
			var errmessage = LCloadMomentsError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);

			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active'); // Loader schließen, falls aktiv
			document.body.style.overflow = "auto"; // Overflow auf auto, da beim Modal Close dieser auf hidden bleibt	
		});
}

function initNewMomentItemModal() {
	const modalElement = document.querySelector('#newmomentitemmodal');
	const modalInstance = M.Modal.init(modalElement);

	const speichernButton = document.querySelector('.modal-footer .moment_save_button');
	speichernButton.addEventListener('click', createNewMomentItem);

	const inputFieldTitle = document.getElementById('moment_titel');
	inputFieldTitle.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			createNewMomentItem(event);
		}
	})

	const inputFieldDate = document.getElementById('moment_datum');
	inputFieldDate.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			createNewMomentItem(event);
		}
	})

}

async function createNewMomentItem(event) {
	event.preventDefault();

	const title = document.getElementById('moment_titel').value;
	const date = document.getElementById('moment_datum').value;

	if (title.trim() === '') {
		callToast('error', LCenterTitle);
		return false;
	}

	if (date.trim() === '') {
		callToast('error', LCenterDate);
		return false;
	}

	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	const formData = new FormData();
	formData.append('title', title);
	formData.append('date', date);

	fetch(API_ENDPOINTS.moments, {
			method: "POST",
			body: formData
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === "success") {

				fetchMomentsItems();
				const modalElement = document.querySelector('#newmomentitemmodal');
				const modalInstance = M.Modal.init(modalElement);
				modalInstance.close();

				document.getElementById('moment_titel').value = ''; // Titel leeren
				document.getElementById('moment_datum').value = ''; // Datum leeren
				document.body.style.overflow = "auto";
				scrollMoments();

			} else {
				const message = data.message;
				callToast('error', message);

				const loaderContainer = document.querySelector('.loader-container');
				loaderContainer.classList.remove('active');
				document.body.style.overflow = "auto";
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);

			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active');
			document.body.style.overflow = "auto";
		});
}

function initUpdateMomentItemModal() {
	const modalElement = document.querySelector('#updatemomentitemmodal');
	const modalInstance = M.Modal.init(modalElement);

	const speichernButton = document.querySelector('.modal-footer .update_moment_save_button');
	speichernButton.addEventListener('click', updateMomentItem);

	const deleteButton = document.querySelector('.modal-footer .update_moment_delete_button');
	deleteButton.addEventListener('click', deleteMomentItem);

	const inputFieldTitle = document.getElementById('update_moment_titel');
	inputFieldTitle.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			updateMomentItem(event);
		}
	})

	const inputFieldDate = document.getElementById('update_moment_datum');
	inputFieldDate.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			updateMomentItem(event);
		}
	})

}

function editMomentItem(itemId) {
	const updateMomentItemModal = document.getElementById('updatemomentitemmodal');
	const momentTitelInput = document.getElementById('update_moment_titel');
	const momentDatumInput = document.getElementById('update_moment_datum');
	const momentItemID = document.getElementById('update_momentItemID');

	fetch(API_ENDPOINTS.moments + '/' + itemId)
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadMomentsError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {
				const momentItem = data.data[0];

				momentTitelInput.value = momentItem.title;
				momentDatumInput.value = momentItem.date;
				momentItemID.value = itemId;

				const modalInstance = M.Modal.getInstance(updateMomentItemModal);
				modalInstance.open();

			} else if (data.status === 'error') {
				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			const errmessage = LCloadMomentsError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});

}

async function updateMomentItem(event) {
	event.preventDefault();

	const title = document.getElementById('update_moment_titel').value;
	const date = document.getElementById('update_moment_datum').value;
	const itemId = document.getElementById('update_momentItemID').value;


	if (title.trim() === '') {
		callToast('error', LCenterTitle);
		return false;
	}

	if (date.trim() === '') {
		callToast('error', LCenterDate);
		return false;
	}

	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	const formdata = new FormData();
	formdata.append('title', title);
	formdata.append('date', date);

	fetch(API_ENDPOINTS.moments + '/' + itemId, {
			method: 'PUT',
			body: formdata
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === 'success') {

				fetchMomentsItems();
				const modalElement = document.querySelector('#updatemomentitemmodal');
				const modalInstance = M.Modal.init(modalElement);
				modalInstance.close();

				document.body.style.overflow = "auto";
				scrollMoments();

			} else {
				const message = data.message;
				callToast('error', message);

				const loaderContainer = document.querySelector('.loader-container');
				loaderContainer.classList.remove('active');
				document.body.style.overflow = "auto";
			}

		})
		.catch(error => {
			const errmessage = error + '! ' + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);

			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active');
			document.body.style.overflow = "auto";
		});
}

async function deleteMomentItem(event) {

	const itemId = document.getElementById('update_momentItemID').value;

	const confirmed = window.confirm(LCwantDeleteEntry);
	if (!confirmed) {
		return;
	}

	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	fetch(API_ENDPOINTS.moments + '/' + itemId, {
			method: 'DELETE',
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === 'success') {

				fetchMomentsItems();
				const modalElement = document.querySelector('#updatemomentitemmodal');
				const modalInstance = M.Modal.init(modalElement);
				modalInstance.close();

				document.body.style.overflow = "auto";
				scrollMoments();

			} else {
				const message = data.message;
				callToast('error', message);

				const loaderContainer = document.querySelector('.loader-container');
				loaderContainer.classList.remove('active');
				document.body.style.overflow = "auto";
			}

		})
		.catch(error => {
			const errmessage = error + '! ' + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);

			const loaderContainer = document.querySelector('.loader-container');
			loaderContainer.classList.remove('active');
			document.body.style.overflow = "auto";
		});
}