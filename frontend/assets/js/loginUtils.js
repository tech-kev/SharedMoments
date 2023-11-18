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

function getCookie(name) {
	const cookieValue = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
	return cookieValue ? cookieValue.pop() : '';
}

function checkSessionID() {
	const sessionId = getCookie('session_id');
	if (sessionId) {
		fetch(API_ENDPOINTS.checkSessionID + '?session_id=' + sessionId)
			.then(response => response.json())
			.then(data => {
				if (data.status === 'success') {
					if (window.location.pathname === '/login') {
						// Das Session-ID-Cookie ist gültig und die aktuelle URL ist "/login"
						// Leite auf "/" weiter
						window.location.href = '/';
					} else {
						// Das Session-ID-Cookie ist gültig, aber die aktuelle URL ist nicht "/login"
						document.body.style.display = 'block';
					}
				} else {
					// Das Session-ID-Cookie ist nicht gesetzt oder ungültig
					// Session Cookie löschen, da nach Aufruf der Setup-Seite und anschließendem Abschließen des Setups auf einem anderen Gerät das Cookie hängen bleiben kann.
					document.cookie = "session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
					window.location.href = '/login';
				}
			})
			.catch(error => {
				console.error(LCsessionIDError, error);
				// Bei einem Fehler leite ebenfalls auf "/login" um
				window.location.href = '/login';
			});
	} else {
		if (window.location.pathname === '/login') {
			// Das Session-ID-Cookie ist nicht gesetzt und die aktuelle URL ist "/login"
			document.body.style.display = 'block';
		} else if (window.location.pathname === '/setup') {
			// Kein Session-ID-Cookie gesetzt ist
		} else {
			// Das Session-ID-Cookie ist nicht gesetzt und die aktuelle URL ist nicht "/login"
			// Leite auf "/login" um
			window.location.href = '/login';
		}
	}
}

window.addEventListener('load', function() {
	checkSetupState();
})

function checkPassword() {
	const password = document.getElementById('password-input').value;
	//const username = document.getElementById('username-input').value;
	const username = "admin";

	if (password.trim() === '') {
		callToast('error', LCnoPasswordEnterd);
		return false;
	}

	const formData = new FormData();
	formData.append('username', username);
	formData.append('password', password);

	fetch(API_ENDPOINTS.checkPassword, {
			method: 'POST',
			body: formData
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				errmessage = response.status + ": " + LCloginFailed + LCcheckConsole;
				callToast('error', errmessage);
			}
		})
		.then(data => {
			if (data.status === 'success') {
				// Set the session_id cookie
				var expirationDate = new Date(data.data.expiration);
				document.cookie = `session_id=${data.data.session_id}; expires=${expirationDate.toUTCString()}`;
				callToast('info', data.message);
				// Redirect to /
				window.location.href = '/';
			} else {
				errmessage = LCwrongPassword;
				callToast('error', errmessage);
			}
		})
		.catch(error => {
			errmessage = response.status + ": " + LCloginFailed + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}

function checkSetupState() {
	fetch(API_ENDPOINTS.setup, {
			method: 'GET',
		})
		.then(response => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error(response.status + ": " + LCloginFailed + LCcheckConsole);
			}
		})
		.then(data => {
			if (data.status === 'success') {
				if (window.location.pathname === '/setup') {
					window.location.href = '/login';
				} else {
					checkSessionID();
				}
			} else if (data.status === 'error') {
				var currentDate = new Date();
				currentDate.setTime(currentDate.getTime() + (24 * 60 * 60 * 1000)); // Ablaufzeit von 24 Stunden

				document.cookie = "session_id=setup_session; expires=" + currentDate.toUTCString() + "; path=/;";

				if (window.location.pathname !== '/setup') {
					window.location.href = '/setup';
				}
			}
		})
		.catch(error => {
			var errmessage = LCcheckSetupStateError + " " + LCcheckConsole;
			callToast('error', errmessage);
			console.error(error);
		});
}