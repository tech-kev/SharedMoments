'use strict';

let isSubscribed = false;
let swRegistration = null;

function urlB64ToUint8Array(base64String) {
	const padding = '='.repeat((4 - base64String.length % 4) % 4);
	const base64 = (base64String + padding)
		.replace(/\-/g, '+')
		.replace(/_/g, '/');

	const rawData = window.atob(base64);
	const outputArray = new Uint8Array(rawData.length);

	for (let i = 0; i < rawData.length; ++i) {
		outputArray[i] = rawData.charCodeAt(i);
	}
	return outputArray;
}

function updateSubscriptionOnServer(subscription) {
	if (subscription) {

		const data = new FormData();
		data.append("token", JSON.stringify(subscription));

		fetch(API_ENDPOINTS.pushToken, {
				method: "POST",
				body: data
			})
			.then(response => response.json())
			.then(data => {
				const status = data.status;

				if (status === "success") {

				} else {
					console.log(error);
				}
			})
			.catch(error => {
				const errmessage = error + "! " + LCcheckConsole;
				callToast('error', errmessage);
				console.error(error);
			});

		localStorage.setItem('sub_token', JSON.stringify(subscription));
	}
}

function deleteSubscriptionOnServer(subscription) {
	if (subscription) {

		const data = new FormData();
		data.append("token", JSON.stringify(subscription));

		fetch(API_ENDPOINTS.pushToken, {
				method: "DELETE",
				body: data
			})
			.then(response => response.json())
			.then(data => {
				const status = data.status;

				if (status === "success") {

				} else {
					console.log(error);
				}
			})
			.catch(error => {
				const errmessage = error + "! " + LCcheckConsole;
				callToast('error', errmessage);
				console.error(error);
			});
	}
}

function subscribeUser() {
	const applicationServerPublicKey = localStorage.getItem('applicationServerPublicKey');
	const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
	swRegistration.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: applicationServerKey
		})
		.then(function(subscription) {
			updateSubscriptionOnServer(subscription);
			isSubscribed = true;
		})
		.catch(function(err) {
			unsubscribeUser();
		});
}

function unsubscribeUser() {
	swRegistration.pushManager.getSubscription()
		.then(function(subscription) {
			if (subscription) {
				return subscription.unsubscribe();
			}
		})
		.then(function() {
			const subscription = localStorage.getItem('sub_token');
			deleteSubscriptionOnServer(JSON.parse(subscription));
			isSubscribed = false;
		});
}

function initializeNotifications() {

	// Calls the Notifcation Popup
	swRegistration.pushManager.getSubscription()
		.then()
	subscribeUser();

}

if ('serviceWorker' in navigator && 'PushManager' in window) {

	navigator.serviceWorker.register("/js/sw.js")
		.then(function(swReg) {

			swRegistration = swReg;

		})
		.catch(function(error) {
			console.error('Service Worker Error', error);
		});
} else {
	console.warn('Push meapplicationServerPublicKeyssaging is not supported');
}

$(document).ready(function() {

		fetch(API_ENDPOINTS.pushPublicKey, {
				method: 'GET',
			})
			.then(response => {
				if (response.ok) {
					return response.json();
				} else {
					throw new Error(response.status + ": " + LCloadPushKeyError + " " + LCcheckConsole);
				}
			})
			.then(data => {

				localStorage.setItem('applicationServerPublicKey', data.public_key)

			})
	}

)