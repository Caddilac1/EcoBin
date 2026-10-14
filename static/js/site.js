document.addEventListener('DOMContentLoaded', () => {
    const loader = document.querySelector('#site-loader');
    const hideLoader = () => {
        if (loader) {
            loader.classList.add('is-hidden');
            loader.setAttribute('aria-hidden', 'true');
        }
    };
    const showLoader = () => {
        if (loader) {
            loader.classList.remove('is-hidden');
            loader.setAttribute('aria-hidden', 'false');
        }
    };

    hideLoader();

    const loginSwitch = document.querySelector('[data-login-switch]');
    if (loginSwitch) {
        const emailInput = document.querySelector('[name="email"], [name="username"]');
        if (emailInput) {
            const updateLoginSwitch = () => {
                const destination = new URL(loginSwitch.href, window.location.href);
                destination.searchParams.set('email', emailInput.value);
                loginSwitch.href = destination.toString();
            };
            emailInput.addEventListener('input', updateLoginSwitch);
            updateLoginSwitch();
        }
    }

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/sw.js').catch(() => {});
    }

    const pushButton = document.querySelector('[data-enable-push]');
    if (pushButton) {
        pushButton.addEventListener('click', async () => {
            if (!('Notification' in window) || !('PushManager' in window) || !('serviceWorker' in navigator)) {
                pushButton.textContent = 'Browser alerts unavailable';
                return;
            }
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') {
                pushButton.textContent = 'Browser alerts blocked';
                return;
            }
            const config = await fetch('/notifications/push-config/', {credentials: 'same-origin'}).then((response) => response.json());
            if (!config.public_key) {
                pushButton.textContent = 'Alerts are not configured';
                return;
            }
            const registration = await navigator.serviceWorker.ready;
            const applicationServerKey = Uint8Array.from(atob(config.public_key.replace(/-/g, '+').replace(/_/g, '/') + '=='), (character) => character.charCodeAt(0));
            const subscription = await registration.pushManager.subscribe({userVisibleOnly: true, applicationServerKey});
            const csrf = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))?.split('=')[1];
            await fetch('/notifications/push-subscription/', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf || ''}, body: JSON.stringify(subscription)});
            pushButton.textContent = 'Browser alerts enabled';
            pushButton.disabled = true;
        });
    }

    document.querySelectorAll('a[href]').forEach((link) => {
        link.addEventListener('click', (event) => {
            const href = link.getAttribute('href');
            let destination;
            try {
                destination = href ? new URL(href, window.location.href) : null;
            } catch {
                destination = null;
            }
            const isSameSiteNavigation = destination && destination.origin === window.location.origin && ['http:', 'https:'].includes(destination.protocol) && !href.startsWith('#') && !link.target && !link.hasAttribute('download') && !event.defaultPrevented;
            if (isSameSiteNavigation && event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
                showLoader();
            }
        });
    });

    document.querySelectorAll('form').forEach((form) => {
        if (!form.hasAttribute('data-otp-form')) {
            form.addEventListener('submit', () => showLoader());
        }
    });

    window.addEventListener('beforeunload', showLoader);
    window.addEventListener('pageshow', hideLoader);

    const toggle = document.querySelector('.nav-toggle');
    const menu = document.querySelector('.nav-menu');
    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            const open = menu.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', String(open));
        });
        menu.querySelectorAll('a').forEach((link) => {
            link.addEventListener('click', () => {
                menu.classList.remove('is-open');
                toggle.setAttribute('aria-expanded', 'false');
            });
        });
    }

    document.querySelectorAll('[data-runaway-form]').forEach((form) => {
        const dock = form.querySelector('.runaway-dock');
        const button = form.querySelector('[data-runaway-submit]');
        if (!dock || !button) return;

        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const isReady = () => form.checkValidity();
        const settle = () => {
            const ready = isReady();
            dock.classList.toggle('is-ready', ready);
            button.disabled = !ready;
            button.setAttribute('aria-disabled', String(!ready));
            if (ready) {
                button.classList.add('is-settled');
            } else {
                button.classList.remove('is-settled');
            }
        };
        const resetButton = () => {
            button.style.setProperty('--x', '0px');
            button.style.setProperty('--y', '0px');
            button.style.setProperty('--rot', '0deg');
        };
        const chasePointer = (event) => {
            if (reducedMotion || event.pointerType !== 'mouse' || isReady()) {
                resetButton();
                return;
            }
            const rect = button.getBoundingClientRect();
            const halfWidth = rect.width / 2;
            const halfHeight = rect.height / 2;
            const dx = event.clientX - (rect.left + halfWidth);
            const dy = event.clientY - (rect.top + halfHeight);
            const edgeX = Math.max(Math.abs(dx) - halfWidth, 0);
            const edgeY = Math.max(Math.abs(dy) - halfHeight, 0);
            const proximity = 76;
            if (edgeX > proximity || edgeY > proximity) return;

            const urgencyX = Math.max(proximity - edgeX, 0) / proximity;
            const urgencyY = Math.max(proximity - edgeY, 0) / proximity;
            const directionX = dx === 0 ? (event.clientX < rect.left ? 1 : -1) : (dx > 0 ? -1 : 1);
            const directionY = dy === 0 ? (event.clientY < rect.top ? 1 : -1) : (dy > 0 ? -1 : 1);
            const x = Math.max(-72, Math.min(72, directionX * urgencyX * (edgeX < 8 ? 60 : 38)));
            const y = Math.max(-22, Math.min(22, directionY * urgencyY * (edgeY < 8 ? 22 : 12)));
            const rotation = directionX * urgencyX * 2.5;
            button.style.setProperty('--x', `${x}px`);
            button.style.setProperty('--y', `${y}px`);
            button.style.setProperty('--rot', `${rotation}deg`);
        };

        form.addEventListener('input', settle);
        form.addEventListener('change', settle);
        button.addEventListener('pointermove', chasePointer);
        dock.addEventListener('pointermove', chasePointer);
        dock.addEventListener('pointerleave', resetButton);
        button.addEventListener('click', (event) => {
            if (!isReady()) {
                event.preventDefault();
                form.reportValidity();
                settle();
            }
        });
        settle();
    });

    document.querySelectorAll('[data-location-form]').forEach((form) => {
        const address = form.querySelector('[data-location-address]');
        const latitude = form.querySelector('[name="location_lat"]');
        const longitude = form.querySelector('[name="location_lng"]');
        const useLocation = form.querySelector('[data-use-location]');
        const status = form.querySelector('[data-location-status]');
        if (!address || !latitude || !longitude || !useLocation) return;

        const validateLocationChoice = () => {
            address.setCustomValidity(address.value.trim() || (latitude.value && longitude.value) ? '' : 'Enter an address or use your current location.');
            form.dispatchEvent(new Event('change', { bubbles: true }));
        };
        const validateAddress = () => {
            if (latitude.value && longitude.value && address.value !== `Current location (${latitude.value}, ${longitude.value})`) {
                latitude.value = '';
                longitude.value = '';
                status.textContent = 'Address changed. The typed address will be used for directions.';
            }
            validateLocationChoice();
        };
        address.addEventListener('input', validateAddress);
        address.addEventListener('change', validateAddress);
        useLocation.addEventListener('click', () => {
            if (!navigator.geolocation) {
                status.textContent = 'Location is unavailable. Please enter your address.';
                return;
            }
            useLocation.disabled = true;
            status.textContent = 'Finding your location...';
            navigator.geolocation.getCurrentPosition((position) => {
                latitude.value = position.coords.latitude.toFixed(6);
                longitude.value = position.coords.longitude.toFixed(6);
                address.value = `Current location (${latitude.value}, ${longitude.value})`;
                status.textContent = `Location selected (about ±${Math.round(position.coords.accuracy)} m accuracy). Review the location before submitting.`;
                useLocation.disabled = false;
                validateLocationChoice();
            }, () => {
                status.textContent = 'We could not access your location. Please enter your address.';
                useLocation.disabled = false;
                validateLocationChoice();
            }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
        });
        validateLocationChoice();
    });

    const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    document.querySelectorAll('[data-collector-route]').forEach((route) => {
        if (!route.querySelector('.live-route-status') || !navigator.geolocation || !csrfToken) return;
        const sendLocation = (position) => {
            const body = new URLSearchParams({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            });
            fetch(`/collector/pickups/${route.dataset.pickupId}/location/`, {
                method: 'POST',
                headers: {'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded'},
                body,
                credentials: 'same-origin',
            }).catch(() => {});
        };
        navigator.geolocation.watchPosition(sendLocation, () => {}, {enableHighAccuracy: true, maximumAge: 10000, timeout: 15000});
    });

    if (window.L) {
        document.querySelectorAll('[data-pickup-tracking].is-live').forEach((card) => {
            const mapElement = card.querySelector('.tracking-map');
            const etaElement = card.querySelector('.tracking-eta');
            const messageElement = card.querySelector('.tracking-message');
            const destinationLat = Number(card.dataset.destinationLat);
            const destinationLng = Number(card.dataset.destinationLng);
            const map = window.L.map(mapElement, {zoomControl: false}).setView(
                Number.isFinite(destinationLat) && Number.isFinite(destinationLng) ? [destinationLat, destinationLng] : [5.6037, -0.1870], 14,
            );
            window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
            let marker;
            const refresh = () => fetch(card.dataset.trackingUrl, {credentials: 'same-origin'})
                .then((response) => response.json())
                .then((data) => {
                    messageElement.textContent = data.status_label;
                    etaElement.textContent = data.eta_minutes === null ? 'Calculating ETA' : `About ${data.eta_minutes} minutes`;
                    if (data.collector_latitude && data.collector_longitude) {
                        const point = [Number(data.collector_latitude), Number(data.collector_longitude)];
                        if (!marker) marker = window.L.marker(point).addTo(map).bindTooltip('Collector', {permanent: true});
                        else marker.setLatLng(point);
                        map.setView(point, 14);
                    }
                }).catch(() => {});
            refresh();
            window.setInterval(refresh, 10000);
        });
    }

    const motionItems = document.querySelectorAll('main > section, .service-feature, .audience-grid article, .price-ribbon article, .dashboard-stat, .dashboard-panel, .record-row, .notification-row, .future-images figure, .reveal');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if ('IntersectionObserver' in window && motionItems.length && !reducedMotion) {
        document.documentElement.classList.add('motion-ready');
        const motionObserver = new IntersectionObserver((entries, currentObserver) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-motion-visible', 'is-visible');
                    currentObserver.unobserve(entry.target);
                }
            });
        }, {threshold: 0.02, rootMargin: '0px 0px -4% 0px'});
        motionItems.forEach((item, index) => {
            item.classList.add('motion-reveal');
            item.style.setProperty('--motion-delay', `${Math.min(index % 5, 4) * 65}ms`);
            motionObserver.observe(item);
        });
    } else {
        motionItems.forEach((item) => item.classList.add('is-motion-visible', 'is-visible'));
    }

    const story = document.querySelector('[data-scroll-story]');
    if (story) {
        const steps = [...story.querySelectorAll('[data-story-step]')];
        const images = [...story.querySelectorAll('[data-story-image]')];
        const index = story.querySelector('[data-story-index]');
        const title = story.querySelector('[data-story-title]');
        const activateStep = (step) => {
            const key = step.dataset.storyStep;
            const stepIndex = steps.indexOf(step);
            steps.forEach((item) => item.classList.toggle('is-active', item === step));
            images.forEach((image) => image.classList.toggle('is-active', image.dataset.storyImage === key));
            story.querySelector('[data-story-visual]').dataset.step = key;
            if (index) index.textContent = String(stepIndex + 1).padStart(2, '0');
            if (title) title.textContent = step.querySelector('h3').textContent;
        };

        if ('IntersectionObserver' in window) {
            const stepObserver = new IntersectionObserver((entries) => {
                const activeEntry = entries.filter((entry) => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
                if (activeEntry) activateStep(activeEntry.target);
            }, {threshold: [0.1, 0.35, 0.6], rootMargin: '-35% 0px -35% 0px'});
            steps.forEach((step) => stepObserver.observe(step));
        }
    }

    const otpForm = document.querySelector('[data-otp-form]');
    if (otpForm) {
        const otpBoxes = [...otpForm.querySelectorAll('.otp-box')];
        const codeInput = otpForm.querySelector('#code');
        const submitButton = otpForm.querySelector('.otp-submit');
        const setCode = (value) => {
            const digits = value.replace(/\D/g, '').slice(0, otpBoxes.length);
            otpBoxes.forEach((box, index) => {
                box.value = digits[index] || '';
                box.classList.toggle('is-filled', Boolean(box.value));
                box.closest('.otp-slot')?.classList.toggle('is-filled', Boolean(box.value));
            });
            codeInput.value = digits;
            return digits;
        };
        const syncCode = () => {
            const digits = otpBoxes.map((box) => box.value.replace(/\D/g, '').slice(0, 1)).join('');
            codeInput.value = digits;
            return digits;
        };
        const focusNextEmpty = () => {
            const nextBox = otpBoxes.find((box) => !box.value);
            (nextBox || otpBoxes[otpBoxes.length - 1]).focus();
        };

        otpBoxes.forEach((box, index) => {
            box.addEventListener('input', () => {
                box.value = box.value.replace(/\D/g, '').slice(-1);
                box.classList.toggle('is-filled', Boolean(box.value));
                box.closest('.otp-slot')?.classList.toggle('is-filled', Boolean(box.value));
                const digits = setCode(otpBoxes.map((item) => item.value).join(''));
                if (digits.length === otpBoxes.length) {
                    otpBoxes[otpBoxes.length - 1].focus();
                } else {
                    focusNextEmpty();
                }
            });
            box.addEventListener('keydown', (event) => {
                if (event.key === 'Backspace' && !box.value && index > 0) {
                    otpBoxes[index - 1].value = '';
                    otpBoxes[index - 1].classList.remove('is-filled');
                    otpBoxes[index - 1].closest('.otp-slot')?.classList.remove('is-filled');
                    syncCode();
                    otpBoxes[index - 1].focus();
                }
                if (event.key === 'ArrowLeft' && index > 0) otpBoxes[index - 1].focus();
                if (event.key === 'ArrowRight' && index < otpBoxes.length - 1) otpBoxes[index + 1].focus();
            });
            box.addEventListener('paste', (event) => {
                event.preventDefault();
                setCode(event.clipboardData.getData('text'));
                focusNextEmpty();
            });
        });

        otpForm.addEventListener('submit', (event) => {
            const digits = syncCode();
            if (digits.length !== otpBoxes.length) {
                event.preventDefault();
                focusNextEmpty();
                return;
            }
            event.preventDefault();
            otpForm.classList.add('is-complete');
            submitButton.classList.add('is-verifying');
            submitButton.disabled = true;
            window.setTimeout(() => {
                showLoader();
                otpForm.submit();
            }, 850);
        });
        otpBoxes[0].focus();
    }
});
