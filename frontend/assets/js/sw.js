'use strict';

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

self.addEventListener('push', function(event) {
	//console.log('[Service Worker] Push Received.');
	//console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

	const pushData = event.data.json();
	const title = pushData.title;
	const options = {
		body: pushData.message,
		icon: '/icon.png',
		badge: '/icon.png',
		requireInteraction: true,
		data: {
			url: pushData.url
		}
	};

	event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
	console.log('[Service Worker] Notification clicked.');

	const notification = event.notification;
	const url = event.notification.data.url;

	event.waitUntil(
		clients.openWindow(url)
		.then(function(windowClient) {
			notification.close();
		})
	);
});

self.addEventListener('pushsubscriptionchange', function(event) {
	const applicationServerPublicKey = localStorage.getItem('applicationServerPublicKey');
	const applicationServerKey = urlB64ToUint8Array(applicationServerPublicKey);
	event.waitUntil(
		self.registration.pushManager.subscribe({
			userVisibleOnly: true,
			applicationServerKey: applicationServerKey
		})
	);
});