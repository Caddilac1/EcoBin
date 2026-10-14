import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js';

const canvas = document.querySelector('[data-hero-wave]');
const hero = document.querySelector('[data-hero-wave-section]');

if (canvas && hero && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let renderer;

    try {
        renderer = new THREE.WebGLRenderer({canvas, alpha: true, antialias: true, powerPreference: 'low-power'});
    } catch (error) {
        canvas.hidden = true;
    }

    if (renderer) {
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100);
        const mobile = window.matchMedia('(max-width: 700px)').matches;
        const columns = mobile ? 30 : 48;
        const rows = mobile ? 18 : 26;
        const count = columns * rows;
        const positions = new Float32Array(count * 3);
        const basePositions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);
        const colorStops = [
            new THREE.Color('#a9c37d'),
            new THREE.Color('#e5b84e'),
            new THREE.Color('#d98262'),
        ];

        let point = 0;
        for (let row = 0; row < rows; row += 1) {
            for (let column = 0; column < columns; column += 1) {
                const index = point * 3;
                const x = (column / (columns - 1) - 0.5) * 30;
                const z = (row / (rows - 1) - 0.5) * 16;
                basePositions[index] = x;
                basePositions[index + 1] = 0;
                basePositions[index + 2] = z;
                positions[index] = x;
                positions[index + 1] = 0;
                positions[index + 2] = z;

                const colorPosition = column / (columns - 1) * (colorStops.length - 1);
                const colorStart = Math.floor(colorPosition);
                const color = colorStops[colorStart].clone().lerp(colorStops[Math.min(colorStart + 1, colorStops.length - 1)], colorPosition - colorStart);
                colors[index] = color.r;
                colors[index + 1] = color.g;
                colors[index + 2] = color.b;
                point += 1;
            }
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
        const material = new THREE.PointsMaterial({
            size: mobile ? 3.2 : 4.1,
            vertexColors: true,
            transparent: true,
            opacity: 0.78,
            depthWrite: false,
            sizeAttenuation: false,
        });
        const wave = new THREE.Points(geometry, material);
        scene.add(wave);

        camera.position.set(0, 7, 23);
        camera.lookAt(0, 0, 0);
        renderer.setClearColor(0x000000, 0);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        canvas.dataset.webglReady = 'true';

        let frame = 0;
        let elapsed = 0;
        let visible = true;
        let previousTime = 0;
        let scrollProgress = 0;
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

        const resize = () => {
            const width = hero.clientWidth;
            const height = hero.clientHeight;
            if (!width || !height) return;
            camera.aspect = width / height;
            camera.updateProjectionMatrix();
            renderer.setSize(width, height, false);
        };

        const updateScroll = () => {
            const bounds = hero.getBoundingClientRect();
            scrollProgress = Math.max(0, Math.min(1, 1 - bounds.bottom / Math.max(window.innerHeight, 1)));
            if (reducedMotion.matches) renderFrame(0);
        };

        const renderFrame = (time) => {
            const delta = previousTime ? Math.min((time - previousTime) / 1000, 0.05) : 0;
            previousTime = time;
            elapsed += delta;
            camera.position.z = 23 - scrollProgress * 3.2;
            camera.position.y = 7 + Math.sin(scrollProgress * Math.PI) * 2.2;
            camera.lookAt(0, 0, 0);

            for (let index = 0; index < count; index += 1) {
                const offset = index * 3;
                const x = basePositions[offset];
                const z = basePositions[offset + 2];
                positions[offset + 1] = Math.sin(x * 0.42 + elapsed * 0.85 + scrollProgress * 2.4) * 0.62
                    + Math.cos(z * 0.62 - elapsed * 0.55) * 0.4;
            }
            geometry.attributes.position.needsUpdate = true;
            renderer.render(scene, camera);
            if (visible && !reducedMotion.matches) frame = window.requestAnimationFrame(renderFrame);
        };

        const visibilityObserver = new IntersectionObserver(([entry]) => {
            visible = entry.isIntersecting;
            if (visible && !reducedMotion.matches && !frame) frame = window.requestAnimationFrame(renderFrame);
            if (!visible && frame) {
                window.cancelAnimationFrame(frame);
                frame = 0;
            }
        });

        visibilityObserver.observe(hero);
        window.addEventListener('resize', resize, {passive: true});
        window.addEventListener('scroll', updateScroll, {passive: true});
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && frame) {
                window.cancelAnimationFrame(frame);
                frame = 0;
            } else if (!document.hidden && visible && !reducedMotion.matches && !frame) {
                frame = window.requestAnimationFrame(renderFrame);
            }
        });
        reducedMotion.addEventListener('change', () => {
            if (reducedMotion.matches && frame) {
                window.cancelAnimationFrame(frame);
                frame = 0;
                renderFrame(0);
            } else if (!reducedMotion.matches && visible && !frame) {
                frame = window.requestAnimationFrame(renderFrame);
            }
        });

        resize();
        updateScroll();
        renderFrame(0);
    }
}