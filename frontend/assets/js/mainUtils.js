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

async function fetchMainTitle() {

	fetch(API_ENDPOINTS.mainTitle, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadMainTitleError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const title = data.data.mainTitle;

				if (window.location.pathname === "/settings" || window.location.pathname === "/setup") {
					document.getElementById("mainTitle").value = title;

				} else {
					document.getElementById("headTitle").textContent = title;
					document.getElementById("mainTitle").innerHTML = "<a href='/'>" + title + "</a>";
				}
			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);

			}
		})
		.catch(error => {
			var errmessage = LCloadMainTitleError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function fetchAnniversaryDate() {

	fetch(API_ENDPOINTS.anniversaryDate, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadAnniversaryDateError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const anniversaryDate = data.data.anniversary_date;

				const date = new Date(anniversaryDate);
				const options = {
					year: 'numeric',
					month: '2-digit',
					day: '2-digit'
				};
				const anniversaryDateFormatted = date.toLocaleDateString(LClocale, options);

				if (window.location.pathname === "/settings" || window.location.pathname === "/setup") {
					document.getElementById("anniversary_date").value = anniversaryDate;
				} else {
					document.getElementById("anniversary_date").textContent = anniversaryDateFormatted;
				}
			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadAnniversaryDateError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function fetchSpecialDays() {

	fetch(API_ENDPOINTS.specialDay, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadSpecialDayError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const day_text = data.data.day_text;
				const day = data.data.day;

				if (day !== 'None') {
					document.getElementById("specialDayText").textContent = day_text;
					document.getElementById("specialDayText").style.display = "block";
				} else {
					document.getElementById("specialDayText").style.display = "none";
				}

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadSpecialDayError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function fetchDaysTogether() {

	fetch(API_ENDPOINTS.daysTogether, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadDaysTogetherError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const text = data.data.text;
				document.getElementById("tage_zusammen").textContent = text;

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadDaysTogetherError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function uploadStockItem(option) {
	const inputElement = document.createElement('input');
	inputElement.type = 'file';

	if (option === 'banner') {
		inputElement.accept = 'image/*';
	} else if (option === 'music') {
		inputElement.accept = 'audio/*';
	}

	inputElement.addEventListener('change', async (event) => {
		const file = event.target.files[0];

		if (file) {

			let filename;

			if (option === 'banner') {
				filename = 'banner';
				item_type = 'stock_item';
			} else if (option === 'music') {
				filename = 'song';
				item_type = 'stock_item';
			}

			const fileExtension = file.name.split('.').pop();
			filename += `.${fileExtension}`;


			const formData = new FormData();
			formData.append('file', file, filename);
			formData.append('item_type', item_type);
			formData.append('option', option);

			fetch(API_ENDPOINTS.upload, {
					method: "POST",
					body: formData
				})
				.then(response => response.json())
				.then(data => {
					const status = data.status;

					if (status === "success") {

						if (location.pathname === '/settings' && option === 'music') {
							document.getElementById("useSong").disabled = false;
							document.getElementById("useSong").checked = true;
						}

						const message = data.message;
						callToast('info', message);
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

	})
	inputElement.click();
}

function generatePicture() {
	// HTML-Element, das als Bild heruntergeladen werden soll
	document.getElementById('share_fab').style.display = 'none';

	const element = document.getElementById('render_image');

	// HTML zu Canvas rendern
	html2canvas(element).then(function(canvas) {
		// Canvas als Bild speichern
		const link = document.createElement('a');
		const currentDate = new Date().toISOString().slice(0, 10);
		link.href = canvas.toDataURL('image/png');
		link.download = `sharedmoments_${currentDate}.png`;
		link.click();
	});
	document.getElementById('share_fab').style.display = 'block';
}

function fetchBannerPicture() {

	fetch(API_ENDPOINTS.settings + '/banner', {
			method: 'GET',

		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadBannerError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const banner = data.data.value;
				document.getElementById('bannersrc').src = banner;

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadBannerError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

function loadCustomMenu() {

	fetch(API_ENDPOINTS.sidemenu, {
			method: 'GET'
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === 'success') {
				const sidemenu = data.data.sidemenu;
				const customMenu = document.getElementById('customMenu');

				sidemenu.forEach(item => {
					const listItem = document.createElement('li');

					// Edit-Button für Menü, aktuell noch WIP -> auch an style.css denken

					//const editLink = document.createElement('a');
					//editLink.classList.add('sidemenu-edit-link');
					//editLink.href = '#';
					//
					//const editIcon = document.createElement('i');
					//editIcon.classList.add('material-icons', 'icon-edit-sidemenu');
					//editIcon.textContent = 'edit';
					//
					//editLink.appendChild(editIcon); 
					//listItem.appendChild(editLink);

					const link = document.createElement('a');
					link.href = item.href;
					link.classList.add('sidemenu-link');

					const icon = document.createElement('i');
					icon.classList.add('material-icons');
					icon.textContent = item.icon;
					link.appendChild(icon);

					const text = document.createTextNode(item.menu);

					link.appendChild(text);

					listItem.appendChild(link);

					customMenu.appendChild(listItem);
				});
			} else {
				const message = data.message;
				callToast('error', message);
			}
		})
		.catch(error => {
			const errmessage = error + '! ' + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});

}

document.addEventListener('DOMContentLoaded', async function() {
	const elems = document.querySelectorAll('.sidenav');
	const instances = M.Sidenav.init(elems);

});