/**
 * P.H.A.S.S SPHERE — 3D Three.js WebGL Simulation & Spherical Visualizer.
 * Renders the spherical robot, rotating mechanical rings, 360 LiDAR raycasts,
 * camera field-of-view cone, and laboratory arena obstacles.
 */

class PHASSSimulation3D {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.robotMesh = null;
    this.innerRingMesh = null;
    this.lidarPointsMesh = null;
    this.lidarLinesMesh = null;
    this.fovConeMesh = null;
    this.obstacleMeshes = {};
    this.targetPos = { x: 0, y: 0, z: 0.35 };
    this.targetHeading = 0;
    this.statusLedMaterial = null;

    this.init();
  }

  init() {
    if (!this.container) return;

    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    // 1. Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x060913);
    this.scene.fog = new THREE.FogExp2(0x060913, 0.04);

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    this.camera.position.set(0, -9, 8);
    this.camera.lookAt(0, 0, 0.5);

    // 3. Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.container.appendChild(this.renderer.domElement);

    // 4. Lighting
    const ambientLight = new THREE.AmbientLight(0x1e293b, 1.5);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x00f0ff, 2.0);
    dirLight.position.set(5, -5, 10);
    dirLight.castShadow = true;
    this.scene.add(dirLight);

    const pointLight = new THREE.PointLight(0x3b82f6, 1.5, 15);
    pointLight.position.set(0, 0, 4);
    this.scene.add(pointLight);

    // 5. Grid Floor
    const gridHelper = new THREE.GridHelper(20, 20, 0x00f0ff, 0x1e293b);
    gridHelper.rotation.x = Math.PI / 2;
    this.scene.add(gridHelper);

    // Arena Floor Plane
    const floorGeo = new THREE.PlaneGeometry(20, 20);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x070d1a,
      roughness: 0.8,
      metalness: 0.2,
    });
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.receiveShadow = true;
    this.scene.add(floorMesh);

    // 6. Build P.H.A.S.S Spherical Robot Model
    this.buildRobotModel();

    // 7. LiDAR and FOV Visualizers
    this.buildSensorVisualizers();

    // 8. Event Listeners
    window.addEventListener("resize", () => this.onResize());

    // 9. Animation Loop
    this.animate();
  }

  buildRobotModel() {
    this.robotMesh = new THREE.Group();

    // Outer Shell Sphere (Sleek Metallic Matte with seams)
    const sphereGeo = new THREE.SphereGeometry(0.5, 32, 32);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0,
      metalness: 0.85,
      roughness: 0.25,
      wireframe: false,
    });
    const outerSphere = new THREE.Mesh(sphereGeo, sphereMat);
    outerSphere.castShadow = true;
    this.robotMesh.add(outerSphere);

    // Inner Gyro & Omni Ring
    const ringGeo = new THREE.TorusGeometry(0.52, 0.02, 16, 64);
    const ringMat = new THREE.MeshStandardMaterial({
      color: 0x00f0ff,
      emissive: 0x0088aa,
      emissiveIntensity: 0.5,
      metalness: 0.9,
    });
    this.innerRingMesh = new THREE.Mesh(ringGeo, ringMat);
    this.robotMesh.add(this.innerRingMesh);

    // Central AI Camera Eye / Lens
    const eyeGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.15, 32);
    const eyeMat = new THREE.MeshStandardMaterial({
      color: 0x020617,
      metalness: 0.95,
      roughness: 0.1,
    });
    const eye = new THREE.Mesh(eyeGeo, eyeMat);
    eye.rotation.x = Math.PI / 2;
    eye.position.set(0, 0.45, 0);
    this.robotMesh.add(eye);

    // Camera Lens Glow
    const lensGeo = new THREE.CircleGeometry(0.08, 32);
    const lensMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
    const lens = new THREE.Mesh(lensGeo, lensMat);
    lens.position.set(0, 0.526, 0);
    this.robotMesh.add(lens);

    // Status LED Halo
    const haloGeo = new THREE.RingGeometry(0.14, 0.18, 32);
    this.statusLedMaterial = new THREE.MeshBasicMaterial({
      color: 0x10b981,
      side: THREE.DoubleSide,
    });
    const halo = new THREE.Mesh(haloGeo, this.statusLedMaterial);
    halo.position.set(0, 0.527, 0);
    this.robotMesh.add(halo);

    this.robotMesh.position.set(0, 0, 0.5);
    this.scene.add(this.robotMesh);
  }

  buildSensorVisualizers() {
    // LiDAR Ray Points (Points Cloud)
    const pointsGeo = new THREE.BufferGeometry();
    const posArray = new Float32Array(64 * 3);
    pointsGeo.setAttribute("position", new THREE.BufferAttribute(posArray, 3));
    const pointsMat = new THREE.PointsMaterial({
      color: 0x00f0ff,
      size: 0.15,
      transparent: true,
      opacity: 0.85,
    });
    this.lidarPointsMesh = new THREE.Points(pointsGeo, pointsMat);
    this.scene.add(this.lidarPointsMesh);

    // Camera FOV Visualizer Cone
    const coneGeo = new THREE.ConeGeometry(2.5, 4.0, 16, 1, true);
    const coneMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.08,
      wireframe: true,
      side: THREE.DoubleSide,
    });
    this.fovConeMesh = new THREE.Mesh(coneGeo, coneMat);
    this.fovConeMesh.rotation.x = -Math.PI / 2;
    this.fovConeMesh.position.set(0, 2.0, 0);
    this.robotMesh.add(this.fovConeMesh);
  }

  updateRobotPose(telemetry) {
    if (!telemetry || !telemetry.position) return;
    const pos = telemetry.position;
    this.targetPos.x = pos.x;
    this.targetPos.y = pos.y;
    this.targetPos.z = 0.5;
    this.targetHeading = (telemetry.heading_deg || 0) * (Math.PI / 180.0);

    // Update Status LED color
    if (this.statusLedMaterial) {
      if (telemetry.status === "EMERGENCY_STOP") {
        this.statusLedMaterial.color.setHex(0xf43f5e);
      } else if (telemetry.status === "EXECUTING" || telemetry.status === "REASONING") {
        this.statusLedMaterial.color.setHex(0x00f0ff);
      } else if (telemetry.battery_percentage < 20) {
        this.statusLedMaterial.color.setHex(0xf59e0b);
      } else {
        this.statusLedMaterial.color.setHex(0x10b981);
      }
    }
  }

  updateLidarCloud(lidarData) {
    if (!lidarData || !lidarData.points || !this.lidarPointsMesh) return;
    const pts = lidarData.points;
    const posAttr = this.lidarPointsMesh.geometry.attributes.position;
    for (let i = 0; i < pts.length && i < 64; i++) {
      posAttr.setXYZ(i, pts[i].x, pts[i].y, 0.5);
    }
    posAttr.needsUpdate = true;
  }

  syncArenaObstacles(obstacles) {
    if (!obstacles) return;
    const currentIds = new Set(obstacles.map((o) => o.id));

    // Remove deleted
    for (let id in this.obstacleMeshes) {
      if (!currentIds.has(id)) {
        this.scene.remove(this.obstacleMeshes[id]);
        delete this.obstacleMeshes[id];
      }
    }

    // Add / Update
    obstacles.forEach((obs) => {
      if (!this.obstacleMeshes[obs.id]) {
        const geo = new THREE.CylinderGeometry(
          obs.radius_m,
          obs.radius_m,
          obs.height_m,
          24
        );
        const mat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(obs.color || "#00e5ff"),
          metalness: 0.6,
          roughness: 0.3,
        });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.rotation.x = Math.PI / 2;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
        this.scene.add(mesh);
        this.obstacleMeshes[obs.id] = mesh;
      }
      const m = this.obstacleMeshes[obs.id];
      m.position.set(obs.position.x, obs.position.y, obs.height_m / 2.0);
    });
  }

  onResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // Interpolate robot position & rotation
    if (this.robotMesh) {
      this.robotMesh.position.x += (this.targetPos.x - this.robotMesh.position.x) * 0.15;
      this.robotMesh.position.y += (this.targetPos.y - this.robotMesh.position.y) * 0.15;
      this.robotMesh.rotation.z += (this.targetHeading - this.robotMesh.rotation.z) * 0.15;

      // Subtle mechanical inner gyro spin
      if (this.innerRingMesh) {
        this.innerRingMesh.rotation.x += 0.02;
        this.innerRingMesh.rotation.y += 0.01;
      }

      // Camera follow with smooth damping
      this.camera.position.x += (this.robotMesh.position.x - this.camera.position.x) * 0.05;
      this.camera.position.y += (this.robotMesh.position.y - 8.0 - this.camera.position.y) * 0.05;
      this.camera.lookAt(this.robotMesh.position.x, this.robotMesh.position.y, 0.5);
    }

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }
}
