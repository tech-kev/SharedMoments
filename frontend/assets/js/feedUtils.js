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

async function fetchFeedItems() {
	fetch(API_ENDPOINTS.feed, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadFeedItemsError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				data.data.forEach(item => {
					const cardDiv = document.createElement("div");
					cardDiv.classList.add("card");

					const cardImageDiv = document.createElement("div");
					cardImageDiv.classList.add("card-image");

					if (item.contentType === "video") {
						const video = document.createElement("video");
						video.classList.add("responsive-video");
						video.controls = true;
						video.style.display = "block";
						video.style.margin = "0 auto";
						video.setAttribute("data-src", item.contentURL);
						video.classList.add("lazyload");

						const source = document.createElement("source");
						source.setAttribute("data-src", item.contentURL);
						source.type = "video/mp4";

						video.appendChild(source);
						cardImageDiv.appendChild(video);

					} else if (item.contentType === "picture") {
						const image = document.createElement("img");
						image.setAttribute("data-src", item.contentURL);
						image.classList.add("lazyload");
						cardImageDiv.appendChild(image);
					} else if (item.contentType === "gallery") {
						const imageUrls = item.contentURL.split(";");

						if (imageUrls.length > 0) {
							const link = document.createElement("a");
							link.href = "/galleryview?id=" + item.id;

							const image = document.createElement("img");
							image.setAttribute("data-src", imageUrls[0]);
							image.classList.add("lazyload");

							link.appendChild(image);
							cardImageDiv.appendChild(link);

						}
					}

					// Edit-Button
					const editButton = document.createElement("a");
					editButton.classList.add("btn-floating", "halfway-fab", "waves-effect", "waves-light", "green", "editbtn");
					editButton.style.display = "none";

					const editIcon = document.createElement("i");
					editIcon.classList.add("material-icons");
					editIcon.textContent = "edit";

					editButton.appendChild(editIcon);
					cardImageDiv.appendChild(editButton);

					editButton.addEventListener('click', () => {
						editFeedItem(item.id);
					});
					// End Edit-Button

					const cardContentDiv = document.createElement("div");
					cardContentDiv.classList.add("card-content");

					const titleSpan = document.createElement("span");
					titleSpan.classList.add("card-title");
					titleSpan.textContent = item.title;
					cardContentDiv.appendChild(titleSpan);

					const contentP = document.createElement("p");
					contentP.innerHTML = item.content.replace(/\n/g, "<br>"); // Zeilenumbrüche anzeigen
					cardContentDiv.appendChild(contentP);


					for (const key in item) {
						if (
							item.hasOwnProperty(key) &&
							key !== "contentType" &&
							key !== "contentURL" &&
							key !== "title" &&
							key !== "content" &&
							key !== "id" &&
							key !== "dateCreated"
						) {
							const hiddenTag = document.createElement("input");
							hiddenTag.type = "hidden";
							hiddenTag.name = key;
							hiddenTag.value = item[key];
							cardContentDiv.appendChild(hiddenTag);
						}
					}

					cardContentDiv.appendChild(document.createElement("br"));

					const dateSpan = document.createElement("span");
					dateSpan.classList.add("new", "badge");
					const date = new Date(item.dateCreated);
					const options = {
						day: '2-digit',
						month: '2-digit',
						year: 'numeric',
						timeZone: 'UTC'
					};
					const formattedDate = date.toLocaleString(LClocale, options);
					const dateText = document.createElement("p");
					dateText.textContent = formattedDate;
					dateSpan.appendChild(dateText);
					cardContentDiv.appendChild(dateSpan);


					if (item.contentType === "gallery") {
						const galleryBadgeSpan = document.createElement("span");
						galleryBadgeSpan.classList.add("new", "badge", "red");
						const galleryBadgeText = document.createElement("p");
						galleryBadgeText.textContent = LCgalleryTitle;
						galleryBadgeSpan.appendChild(galleryBadgeText);
						cardContentDiv.appendChild(galleryBadgeSpan);
					}

					cardContentDiv.appendChild(document.createElement("br"));

					cardDiv.appendChild(cardImageDiv);
					cardDiv.appendChild(cardContentDiv);

					const rowDiv = document.createElement("div");
					rowDiv.classList.add("row");
					rowDiv.appendChild(cardDiv);

					const containerDiv = document.createElement("div");
					containerDiv.classList.add("container");
					containerDiv.appendChild(rowDiv);

					document.body.appendChild(containerDiv);
				});

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadFeedItemsError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

function initNewFeedItemModal() {
	const modalElement = document.querySelector('#newfeeditemmodal');
	const modalInstance = M.Modal.init(modalElement);

	const speichernButton = document.querySelector('.modal-footer .feed_save_button');
	speichernButton.addEventListener('click', createNewFeedItem);

	const inputFieldTitle = document.getElementById('feed_titel');
	inputFieldTitle.addEventListener('keydown', function(event) {
		if (event.key === 'Enter') {
			createNewFeedItem(event);
		}
	})

	const fileInput = document.getElementById('feed_file');
	fileInput.addEventListener('change', handleFileSelect);
}

let fileOrder = [];

function handleFileSelect(event) {
	const fileList = event.target.files;
	const filePreviewContainer = document.getElementById('file-list');
	filePreviewContainer.innerHTML = '';

	fileOrder = [];

	for (let i = 0; i < fileList.length; i++) {
		const file = fileList[i];
		const fileReader = new FileReader();

		fileReader.onload = (function(file) {
			return function(event) {
				const filePreview = createFilePreviewElement(event.target.result, 'dataURL');
				filePreviewContainer.appendChild(filePreview);
				fileOrder.push(file);
			};
		})(file);

		fileReader.readAsDataURL(file);
	}
}

function createFilePreviewElement(fileDataURL, fType) {

	if (fType === 'dataURL') {

		document.getElementById('file-list-text').style.display = 'block';

	} else if (fType === 'fileName') {

		document.getElementById('update_file-list-text').style.display = 'block';

	}

	const filePreview = document.createElement('div');
	filePreview.classList.add('file-preview', 'col', 's4');

	const fileType = getFileType(fileDataURL, fType);

	if (fileType === 'image') {
		const fileImage = document.createElement('img');
		fileImage.src = fileDataURL;
		fileImage.classList.add('file-preview-image');
		filePreview.appendChild(fileImage);
	} else if (fileType === 'video') {
		const fileVideo = document.createElement('video');
		fileVideo.src = fileDataURL;
		fileVideo.classList.add('file-preview-video');
		fileVideo.controls = true;
		filePreview.appendChild(fileVideo);
	} else {
		callToast('error', LCinvalidFiletype);
	}

	const fileOrderControls = document.createElement('div');
	fileOrderControls.classList.add('file-order-controls');

	const moveUpButton = document.createElement('a');
	moveUpButton.innerHTML = '<i class="material-icons">arrow_upward</i>';
	moveUpButton.classList.add('file-order-button', 'waves-effect', 'waves-light'); //'btn-small'
	moveUpButton.addEventListener('click', moveFileUp);
	fileOrderControls.appendChild(moveUpButton);

	const moveDownButton = document.createElement('a');
	moveDownButton.innerHTML = '<i class="material-icons">arrow_downward</i>';
	moveDownButton.classList.add('file-order-button-down', 'waves-effect', 'waves-light'); //'btn-small'
	moveDownButton.addEventListener('click', moveFileDown);
	fileOrderControls.appendChild(moveDownButton);

	const deleteButton = document.createElement('a');
	deleteButton.innerHTML = '<i class="material-icons">delete</i>';
	deleteButton.classList.add('file-delete-button', 'waves-effect', 'waves-light');
	deleteButton.addEventListener('click', deleteFile);
	fileOrderControls.appendChild(deleteButton);

	filePreview.appendChild(fileOrderControls);
	const lineBreak = document.createElement('br');
	filePreview.appendChild(lineBreak);
	const lineBreak1 = document.createElement('br');
	filePreview.appendChild(lineBreak1);
	const lineBreak2 = document.createElement('br');
	filePreview.appendChild(lineBreak2);

	return filePreview;
}

function moveFileUp(event) {
	const filePreview = event.target.closest('.file-preview');
	const index = Array.from(filePreview.parentNode.children).indexOf(filePreview);

	if (index > 0) {
		filePreview.parentNode.insertBefore(filePreview, filePreview.previousSibling);
		swapFiles(index, index - 1);
	}
}

function moveFileUp(event) {
	const filePreview = event.target.closest('.file-preview');
	const index = Array.from(filePreview.parentNode.children).indexOf(filePreview);

	if (index > 0) {
		filePreview.parentNode.insertBefore(filePreview, filePreview.previousSibling);
		swapFiles(index, index - 1);
		updateFileOrder();
	}
}

function moveFileDown(event) {
	const filePreview = event.target.closest('.file-preview');
	const index = Array.from(filePreview.parentNode.children).indexOf(filePreview);

	if (index < filePreview.parentNode.children.length - 1) {
		filePreview.parentNode.insertBefore(filePreview.nextSibling, filePreview);
		swapFiles(index, index + 1);
		updateFileOrder();
	}
}

function updateFileOrder() {
	const filePreviews = document.querySelectorAll('.file-preview');
	fileOrder = Array.from(filePreviews).map(filePreview => {
		const index = Array.from(filePreview.parentNode.children).indexOf(filePreview);
		return fileOrder[index];
	});
}

function swapFiles(index1, index2) {
	const temp = fileOrder[index1];
	fileOrder[index1] = fileOrder[index2];
	fileOrder[index2] = temp;
}

function deleteFile(event) {
	const filePreview = event.target.closest('.file-preview');
	const index = Array.from(filePreview.parentNode.children).indexOf(filePreview);

	filePreview.remove();
	fileOrder.splice(index, 1);
}

function getFileType(fileURL, fType) {

	if (fType === 'dataURL') {
		const mimeType = fileURL.split(',')[0].split(':')[1].split(';')[0];
		if (mimeType.startsWith('image')) {
			return 'image';
		} else if (mimeType.startsWith('video')) {
			return 'video';
		} else {
			return LCinvalidFiletype;
		}
	} else if (fType === 'fileName') {
		const fileExtension = fileURL.split('.').pop().toLowerCase();
		if (fileExtension === 'jpg' || fileExtension === 'jpeg' || fileExtension === 'jfif' || fileExtension === 'pjpeg' || fileExtension === 'pjp' || fileExtension === 'png') {
			return 'image';
		} else if (fileExtension === 'mp4') {
			return 'video';
		} else {
			return LCinvalidFiletype;
		}
	} else {
		return LCinvalidFiletype;
	}
}

async function createNewFeedItem(event) {
	event.preventDefault();

	// Zeige den Materialize-Loader an
	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	const title = document.querySelector('#feed_titel').value;
	const content = document.querySelector('#feed_inhalt').value;
	const date = document.querySelector('#feed_datum').value;
	let contentType = 'text'; // standardmäßig wird der contentType auf text gesetzt
	let contentURL = ''; // standardmäßig ist keine Datei vorhanden

	if (title.trim() === '') {
		callToast('error', LCenterTitle);
		loaderContainer.classList.remove('active');
		return false;
	}

	if (content.trim() === '') {
		callToast('error', LCenterFeedDesc);
		loaderContainer.classList.remove('active');
		return false;
	}

	const fileInput = document.getElementById('feed_file');
	const files = fileInput.files;

	let uploadedFileCount = 0;

	for (let i = 0; i < fileOrder.length; i++) {
		const file = fileOrder[i];
		const fileName = file.name;
		const fileExtension = fileName.split('.').pop();
		if (fileExtension === 'jpg' || fileExtension === 'jpeg' || fileExtension === 'jfif' || fileExtension === 'pjpeg' || fileExtension === 'pjp' || fileExtension === 'png') {
			contentType = 'picture';
		} else if (fileExtension === 'mp4') {
			contentType = 'video';
		}

		// Bild oder Video an die API senden
		const formdata = new FormData();
		formdata.append('file', file);
		formdata.append('item_type', 'feed_item')
		formdata.append('option', 'feed')

		await fetch(API_ENDPOINTS.upload, {
				method: "POST",
				body: formdata
			})
			.then(response => response.json())
			.then(data => {
				const status = data.status;
				if (status === "success") {
					const currentURL = data.data;
					contentURL += currentURL;
					uploadedFileCount++;
					if (uploadedFileCount < fileOrder.length) {
						contentURL += ';';
					}
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


	if (files.length > 1) {
		contentType = 'gallery';
	}

	const formdata = new FormData();
	formdata.append('contentType', contentType);
	formdata.append('contentURL', contentURL);
	formdata.append('content', content);
	formdata.append('title', title);
	formdata.append('dateCreated', date);

	fetch(API_ENDPOINTS.feed, {
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
				loaderContainer.classList.remove('active');
			}
		})
		.catch(error => {
			const errmessage = error + "! " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
			loaderContainer.classList.remove('active');
			reject(false);
		});
}

function changeEditMode(trigger) {
	const editButtons = document.querySelectorAll('.editbtn, .editbtnMoments');
	const urlParams = new URLSearchParams(window.location.search);
	let editMode = urlParams.get('editmode');

	if (trigger === 'buttonklick') {
		if (editMode === 'true') {
			editMode = 'false';
		} else {
			editMode = 'true';
		}
		urlParams.set('editmode', editMode);
		const newUrl = `${window.location.pathname}?${urlParams.toString()}`;
		window.history.replaceState(null, null, newUrl);
	}

	//let mode = 'none';
	for (let i = 0; i < editButtons.length; i++) {
		if (editMode === 'true') {
			editButtons[i].style.display = 'block';
			//mode = 'block';
		} else {
			editButtons[i].style.display = 'none';
		}
	}

	if (editMode === 'true' && trigger === 'buttonklick') {
		callToast('info', LCeditModeOn);
	} else if (editMode === 'false' && trigger === 'buttonklick') {
		callToast('info', LCeditMOdeOff);
	}
}


function editFeedItem(itemId) {
	const updateFeedItemModal = document.getElementById('updatefeeditemmodal');
	const feedTitelInput = document.getElementById('feed_titel_update');
	const feedInhaltTextarea = document.getElementById('feed_inhalt_update');
	const feedDatumInput = document.getElementById('feed_datum_update');
	const feedItemID = document.getElementById('update_feedItemID');
	const filePreviewContainer = document.getElementById('update_file-list');

	let fileOrder;

	fetch(API_ENDPOINTS.feed + '/' + itemId)
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadFeedItemsError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {
				const feedItem = data.data[0];
				const convertedDateCreated = new Date(feedItem.dateCreated).toISOString().split('T')[0];

				// Fülle die Felder im Modal mit den Daten des Feed-Elements
				feedTitelInput.value = feedItem.title;
				feedInhaltTextarea.value = feedItem.content;
				feedDatumInput.value = convertedDateCreated;
				feedItemID.value = itemId;

				// Lade die Bilder und Videos in die Vorschau
				const contentURL = feedItem.contentURL;
				const fileURLs = contentURL.split(';');
				filePreviewContainer.innerHTML = '';
				fileOrder = [];

				if (contentURL) {
					fileURLs.forEach(fileURL => {
						const filePreview = createFilePreviewElement(fileURL, 'fileName');
						filePreviewContainer.appendChild(filePreview);
						fileOrder.push(fileURL);
					});
				}

				// Öffne das Modal
				const modalInstance = M.Modal.getInstance(updateFeedItemModal);
				modalInstance.open();

			} else if (data.status === 'error') {
				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			const errmessage = LCloadFeedItemsError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});

}

async function handleFileSelectOnUpdate(event) {
	const fileList = event.target.files;
	const filePreviewContainer = document.getElementById('update_file-list');

	for (let i = 0; i < fileList.length; i++) {
		const file = fileList[i];
		const fileName = file.name;
		const fileExtension = fileName.split('.').pop().toLowerCase();

		if (fileExtension === 'jpg' || fileExtension === 'jpeg' || fileExtension === 'jfif' || fileExtension === 'pjpeg' || fileExtension === 'pjp' || fileExtension === 'png' || fileExtension === 'mp4') {
			const formdata = new FormData();
			formdata.append('file', file);
			formdata.append('item_type', 'feed_item');
			formdata.append('option', 'feed');

			await fetch(API_ENDPOINTS.upload, {
					method: 'POST',
					body: formdata
				})
				.then(response => response.json())
				.then(data => {
					const status = data.status;
					if (status === 'success') {
						const currentURL = data.data;
						const filePreview = createFilePreviewElement(currentURL, 'fileName');
						filePreviewContainer.appendChild(filePreview);
						fileOrder.push(currentURL);
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
		} else {
			callToast('error', LCloadFeedItemsError + " " + LCcheckConsole);
		}
	}
}

function initUpdateFeedItemModal() {
	const modalElement = document.querySelector('#updatefeeditemmodal');
	const modalInstance = M.Modal.init(modalElement);

	const speichernButton = document.querySelector('.modal-footer .updatefeed_save_button');
	speichernButton.addEventListener('click', updateFeedItem);

	const deleteButton = document.querySelector('.modal-footer .updatefeed_delete_button');
	deleteButton.addEventListener('click', deleteFeedItem);

	const fileInput = document.getElementById('feed_file_update');
	fileInput.addEventListener('change', handleFileSelectOnUpdate);

}

async function updateFeedItem(event) {
	event.preventDefault();

	// Zeige den Materialize-Loader an
	const loaderContainer = document.querySelector('.loader-container');
	loaderContainer.classList.add('active');

	const title = document.querySelector('#feed_titel_update').value;
	const content = document.querySelector('#feed_inhalt_update').value;
	const date = document.querySelector('#feed_datum_update').value;
	const itemId = document.getElementById('update_feedItemID').value;
	let contentType = 'text'; // standardmäßig wird der contentType auf text gesetzt
	let contentURL = ''; // standardmäßig ist keine Datei vorhanden

	if (title.trim() === '') {
		callToast('error', LCenterTitle);
		loaderContainer.classList.remove('active');
		return false;
	}

	if (content.trim() === '') {
		callToast('error', LCenterFeedDesc);
		t
		loaderContainer.classList.remove('active');
		return false;
	}

	const filePreviewContainer = document.getElementById('update_file-list');
	const filePreviews = filePreviewContainer.getElementsByClassName('file-preview');

	for (let i = 0; i < filePreviews.length; i++) {
		const filePreview = filePreviews[i];
		const fileElement = filePreview.querySelector('img, video');
		const fileType = fileElement.tagName.toLowerCase();
		const fileURL = fileElement.src;

		if (fileType === 'img') {
			contentType = 'picture';
		} else if (fileType === 'video') {
			contentType = 'video';
		}

		// Datei-URLs zur contentURL hinzufügen (ohne die Basis-URL)
		const baseURL = window.location.origin; // Dynamisch die Basis-URL der aktuellen Webseite ermitteln
		const relativeURLEncoded = fileURL.replace(baseURL, '');
		const relativeURL = decodeURIComponent(relativeURLEncoded);
		contentURL += relativeURL;
		if (i < filePreviews.length - 1 || filePreviews.length > 1 && i !== filePreviews.length - 1) {
			contentURL += ';'; // Hinzufügen eines Semikolons, wenn es weitere Dateien gibt oder bereits Dateien in der Vorschau sind
		}
	}

	

	const fileInput = document.getElementById('feed_file_update');
	const files = fileInput.files;

	if (filePreviews.length > 1 || files.length > 1) {
		contentType = 'gallery';
	}

	const formdata = new FormData();
	formdata.append('contentType', contentType);
	formdata.append('contentURL', contentURL);
	formdata.append('content', content);
	formdata.append('title', title);
	formdata.append('dateCreated', date);

	fetch(API_ENDPOINTS.feed + '/' + itemId, {
			method: 'PUT',
			body: formdata
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === 'success') {
				location.reload();
			} else {
				const message = data.message;
				callToast('error', message);
			}

			loaderContainer.classList.remove('active');
		})
		.catch(error => {
			const errmessage = error + '! ' + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);

			loaderContainer.classList.remove('active');
		});
}

async function deleteFeedItem(event) {

	const itemId = document.getElementById('update_feedItemID').value;

	const confirmed = window.confirm(LCwantDeleteEntry);
	if (!confirmed) {
		return;
	}

	fetch(API_ENDPOINTS.feed + '/' + itemId, {
			method: 'DELETE',
		})
		.then(response => response.json())
		.then(data => {
			const status = data.status;

			if (status === 'success') {
				location.reload();
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


//Play Music

function musicAvailable() {

	fetch(API_ENDPOINTS.settings + '/music', {
			method: 'GET',

		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadMusicSettingError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {
				const musicURL = data.data.value;
				const isMusicAvailable = data.data.specialvalue; // Wert "true" oder "false"

				if (isMusicAvailable === "true") {
					audio.src = musicURL; // URL des Songs setzen
					document.getElementById('musicFAB').style.display = 'block'; // Musik-Button anzeigen
				}

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadMusicSettingError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}


var audio = new Audio();
var isPlaying = false;

audio.addEventListener('ended', function() {
	document.getElementById('music-icon').innerHTML = 'music_off';
	isPlaying = false;
});

audio.addEventListener('error', function() {
	var message = LCloadSongError + " " + LCcheckConsole;
	callToast('error', message);
});

function togglePlay() {
	if (isPlaying) {
		audio.pause();
		document.getElementById('music-icon').innerHTML = 'music_off';
	} else {
		audio.play();
		document.getElementById('music-icon').innerHTML = 'music_note';
	}
	isPlaying = !isPlaying;
}