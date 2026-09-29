document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    container.appendChild(renderer.domElement);

    // 3D Wireframe Cyber Sphere
    const geometry = new THREE.IcosahedronGeometry(3, 3);
    const material = new THREE.MeshBasicMaterial({ color: 0x00f2ff, wireframe: true });
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    // Inner Glowing Core
    const coreGeo = new THREE.SphereGeometry(1.8, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0x0284c7, wireframe: true });
    const core = new THREE.Mesh(coreGeo, coreMat);
    scene.add(core);

    camera.position.z = 7;

    function animate() {
        requestAnimationFrame(animate);
        sphere.rotation.x += 0.003;
        sphere.rotation.y += 0.005;
        core.rotation.y -= 0.008;
        renderer.render(scene, camera);
    }
    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
});