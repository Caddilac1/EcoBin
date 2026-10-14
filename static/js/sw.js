self.addEventListener('push', (event) => {
    const data = event.data ? event.data.json() : {title: 'EcoBin Ghana', body: 'You have a new update.'};
    event.waitUntil(self.registration.showNotification(data.title, {body: data.body, icon: '/static/images/globe_with_recycle_sign.jpg'}));
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(clients.openWindow('/dashboard/'));
});