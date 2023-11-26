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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see
<https: //www.gnu.org/licenses />.
*/

function updateMainTitle() {
	const value = document.getElementById("mainTitle").value;

	if (!value) {
		return callToast('error', LCenterMainTitle)
	}

	const formData = new FormData();
	formData.append("value", value);

	fetch(API_ENDPOINTS.mainTitle, {
			method: "PUT",
			body: formData
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				errmessage = response.status + ": " + LCupdateMainTitleError + " " + LCcheckConsole;
				throw new Error(errmessage);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				//callToast('info', data.message);

			} else {
				errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			errmessage = LCupdateMainTitleError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

function updateAnniversaryDate() {
	const value = document.getElementById("anniversary_date").value;

	if (!value) {
		return callToast('error', LCenterAnniversaryDate)
	}

	const formData = new FormData();
	formData.append("value", value);

	fetch(API_ENDPOINTS.anniversaryDate, {
			method: "PUT",
			body: formData
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				errmessage = response.status + ": " + LCupateAnniversaryDateError + " " + LCcheckConsole;
				throw new Error(errmessage);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				//callToast('info', data.message);

			} else {
				errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			errmessage = LCupateAnniversaryDateError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

function createUser() {
	return new Promise((resolve, reject) => {
		const password = document.getElementById("password").value;
		const confirmPassword = document.getElementById("confirmPassword").value;

		if (password !== confirmPassword) {
			callToast('error', LCpasswordNoMatch);
			reject(false);
			return;
		}

		// const user = document.getElementById("user").value; // not used at the moment
		const user = "admin";

		const formData = new FormData();
		formData.append("password", password);
		formData.append("username", user);

		fetch(API_ENDPOINTS.user, {
				method: "POST",
				body: formData
			})
			.then(response => response.json())
			.then(data => {
				const status = data.status;

				if (status === "success") {
					//const message = data.message;
					//callToast('info', message);
					resolve(true);
				} else {
					const message = data.message;
					callToast('error', message);
					reject(false);
				}
			})
			.catch(error => {
				const errmessage = error + "! " + LCcheckConsole;
				callToast('error', errmessage);
				console.error(error);
				reject(false);
			});
	});
}

function updateUser() {
	return new Promise((resolve, reject) => {
		const password = document.getElementById("password").value;
		const confirmPassword = document.getElementById("confirmPassword").value;

		if (password !== confirmPassword) {
			callToast('error', LCpasswordNoMatch);
			reject(false);
			return;
		}

		// const user = document.getElementById("user").value; // not used at the moment
		const user = "admin";

		if (password !== "") {

			if (password !== confirmPassword) {
				callToast('error', LCpasswordNoMatch);
				reject(false);
				return;
			}

			const formData = new FormData();
			formData.append("password", password);
			formData.append("username", user);

			fetch(API_ENDPOINTS.user, {
					method: "PUT",
					body: formData
				})
				.then(response => response.json())
				.then(data => {

					if (window.location.pathname === "/settings") {
						const message = data.message;
						callToast('info', message);
					}
				})
				.catch(error => {
					const errmessage = error + "! " + LCcheckConsole;
					callToast('error', errmessage);
					console.error(error);
				});
		}
	})
}

function checkInputFields() {
	return new Promise((resolve, reject) => {

		nameUserA = document.getElementById('nameUserA').value;
		birthdayUserA = document.getElementById('birthdayUserA').value;

		nameUserB = document.getElementById('nameUserB').value;
		birthdayUserB = document.getElementById('birthdayUserB').value;

		mainTitle = document.getElementById('mainTitle').value;

		relationship = document.getElementById('relationship').value;

		anniversary_date = document.getElementById('anniversary_date').value;

		password = document.getElementById("password").value;
		confirmPassword = document.getElementById("confirmPassword").value;

		if (mainTitle === '') {
			callToast('error', LCenterMainTitle);
			reject(false);
			return;
		} else if (password === '' || confirmPassword === '') {
			callToast('error', LCnoPasswordEnterd);
			reject(false);
			return;
		} else if (nameUserA === '' || birthdayUserA === '' || nameUserB === '' || birthdayUserB === '') {
			callToast('error', LCnoNameOrBirthdaySet);
			reject(false);
			return;
		} else if (anniversary_date === '') {
			callToast('error', LCenterAnniversaryDate);
			reject(false);
			return;
		} else if (relationship === '') {
			callToast('error', LCenterRelationship);
			reject(false);
			return;
		}

		resolve(true);
		return;
	})
}

function exitSetup() {
	checkInputFields()
		.then(success => {
			if (success) {
				createUser()
					.then(success => {
						if (success) {
							const value = 'true';

							const formData = new FormData();
							formData.append("value", value);

							fetch(API_ENDPOINTS.setup, {
									method: "PUT",
									body: formData
								})
								.then(response => {
									if (response.ok) {
										return response.json();
									} else {
										throw new Error(response.status + ": " + LCSetupFinishError + " " + LCcheckConsole);
									}
								})
								.then(data => {
									if (data.status === 'success') {

										document.cookie = "session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
										window.location.pathname = "/login";

									} else if (data.status === 'error') {

										const errmessage = data.message;
										callToast('error', errmessage);
									}
								})
								.catch(error => {
									var errmessage = LCSetupFinishError + " " + LCcheckConsole;
									callToast('error', errmessage);
									console.error(error);
								});
						}
					});
			}
		});
}

function changeSongUse(checked) {

	const specialvalue = checked;

	const formData = new FormData();

	formData.append("value", "use_music");
	formData.append("specialvalue", specialvalue);

	fetch(API_ENDPOINTS.settings + '/music', {
			method: 'PUT',
			body: formData

		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCsettingUpdateError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				//const message = data.message;
				//callToast('info', message);

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCsettingUpdateError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function fechtUseSongState() {

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

				if (data.data.specialvalue === 'true' && data.data.value !== "") {

					document.getElementById("useSong").checked = true;

				} else if (data.data.specialvalue === 'false' && data.data.value !== "") {

					document.getElementById("useSong").checked = false;

				} else {

					document.getElementById("useSong").disabled = true;
				}


			} else if (data.status === 'error') {

				//const errmessage = data.message;
				//callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadMusicSettingError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function getBirthdays() {

	fetch(API_ENDPOINTS.settings + '/userA', {
			method: 'GET',

		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadBirthdayError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const nameUserA = data.data.value;
				const birthdayUserA = data.data.specialvalue;

				if (window.location.pathname === "/settings") {

					document.getElementById("nameUserA").innerHTML = nameUserA;
					document.getElementById("birthdayUserA").value = birthdayUserA;

				} else if (window.location.pathname === "/setup") {

					document.getElementById("nameUserA").value = nameUserA;
					document.getElementById('birthdayUserA').value = birthdayUserA;

				}

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadBirthdayError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});

	// zweiter User

	fetch(API_ENDPOINTS.settings + '/userB', {
			method: 'GET',

		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadBirthdayError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const nameUserB = data.data.value;
				const birthdayUserB = data.data.specialvalue;

				if (window.location.pathname === "/settings") {

					document.getElementById("nameUserB").innerHTML = nameUserB;
					document.getElementById("birthdayUserB").value = birthdayUserB;

				} else if (window.location.pathname === "/setup") {

					document.getElementById("nameUserB").value = nameUserB;
					document.getElementById("birthdayUserB").value = birthdayUserB;

				}

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadBirthdayError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function updateSetting(option) {
	let specialvalue;
	let value;

	if (option === 'UserA' || option === 'UserB') {

		if (window.location.pathname === "/settings") {

			value = document.getElementById('name' + option).innerHTML;
			specialvalue = document.getElementById('birthday' + option).value;

		} else if (window.location.pathname === "/setup") {

			value = document.getElementById('name' + option).value;
			specialvalue = document.getElementById('birthday' + option).value;

		}


	} else if (option === 'relationship_status') {
		value = document.getElementById("relationship").value;
		specialvalue = "";
	}


	const formData = new FormData();

	formData.append("value", value);
	formData.append("specialvalue", specialvalue);

	fetch(API_ENDPOINTS.settings + '/' + option, {
			method: 'PUT',
			body: formData

		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCsettingUpdateError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				//const message = data.message;
				//callToast('info', message);

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCsettingUpdateError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function getRelationship() {

	fetch(API_ENDPOINTS.settings + "/relationship_status", {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloadRelationshipError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const relationship_status = data.data.value;

				if (window.location.pathname === "/settings" || window.location.pathname === "/setup") {

					var userAgent = navigator.userAgent;

					var selectElement = document.getElementById("relationship");

					// The select field ist not working probably on iOS, so we use the browser-default on all mobile Devices
					if (userAgent.match(/iPhone|iPad|iPod|Android|webOS|BlackBerry|Windows Phone|IEMobile|Opera Mini/i)) {

						selectElement.classList.add("browser-default");
					}

					selectElement.value = relationship_status;
					var instance = M.FormSelect.init(selectElement);	
					
				}

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCloadRelationshipError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function importHandler(mode = 'normal') {

	const confirmed = window.confirm(LCwantImport);
	if (!confirmed) {
		return;
	}

	fetch(API_ENDPOINTS.import+"/" + mode, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCimportFailed + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const errmessage = data.message;
				callToast('info', errmessage)

				if (window.location.pathname === "/setup") {

					const value = 'true';

					const formData = new FormData();
					formData.append("value", value);

					fetch(API_ENDPOINTS.setup, {
							method: "PUT",
							body: formData
						})
						.then(response => {
							if (response.ok) {
								return response.json();
							} else {
								throw new Error(response.status + ": " + LCSetupFinishError + " " + LCcheckConsole);
							}
						})
						.then(data => {
							if (data.status === 'success') {

								document.cookie = "session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
								window.location.pathname = "/login";

							} else if (data.status === 'error') {

								const errmessage = data.message;
								callToast('error', errmessage);
							}
						})
						.catch(error => {
							var errmessage = LCSetupFinishError + " " + LCcheckConsole;
							callToast('error', errmessage);
							console.error(error);
						});

				} else {

					window.location.reload();

				}

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCimportFailed + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function exportHandler() {

	const confirmed = window.confirm(LCwantExport);
	if (!confirmed) {
		return;
	}

	fetch(API_ENDPOINTS.export, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCexportFailed + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const errmessage = data.message;
				callToast('info', errmessage)

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCexportFailed + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

async function testNotifications() {

	fetch(API_ENDPOINTS.sendPushNotifications, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCtestNotificationError + " " + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {

				const message = data.message;
				callToast('info', message);

			} else if (data.status === 'error') {

				const errmessage = data.message;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			var errmessage = LCtestNotificationError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}
