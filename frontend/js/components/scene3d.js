/**
 * FounderReach 3D Autonomous Agent Universe (Three.js)
 * 
 * Persistent full-screen 3D spatial network:
 * Central Target Domain Node connected to Search, AEO, Generative AI, and Customer Demand Satellites.
 * Camera pans, zooms, and rotates smoothly in sync with window scroll position.
 */

import * as THREE from "../../vendor/three.module.js";

export class Scene3D {
  constructor(containerId = "webgl-canvas-container") {
    this.container = document.getElementById(containerId);
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.masterGroup = null;
    this.centralNode = null;
    this.orbitRing = null;
    this.satellites = [];
    this.connectionLines = null;
    this.dustParticles = null;

    this.mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    this.scrollProgress = 0;
    this.targetScrollProgress = 0;
    this.rotationSpeed = 0.002;
    this.isInitialized = false;

    if (this.container) {
      this.init();
    }
  }

  init() {
    try {
      const width = window.innerWidth;
      const height = window.innerHeight;

      // 1. Scene
      this.scene = new THREE.Scene();

      // 2. Camera
      this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
      this.camera.position.set(0, 0, 26);

      // 3. Renderer with transparent background
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setSize(width, height);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      this.container.appendChild(this.renderer.domElement);

      // 4. Master Group
      this.masterGroup = new THREE.Group();
      this.scene.add(this.masterGroup);

      // 5. Central Target Domain Node (Icosahedron + Inner Core)
      const coreGeom = new THREE.IcosahedronGeometry(3.6, 2);
      const wireframeMat = new THREE.MeshBasicMaterial({
        color: 0x4f46e5,
        wireframe: true,
        transparent: true,
        opacity: 0.35
      });
      this.centralNode = new THREE.Mesh(coreGeom, wireframeMat);
      this.masterGroup.add(this.centralNode);

      const innerGlowGeom = new THREE.SphereGeometry(2.4, 16, 16);
      const innerGlowMat = new THREE.MeshBasicMaterial({
        color: 0x6366f1,
        transparent: true,
        opacity: 0.15
      });
      const innerGlow = new THREE.Mesh(innerGlowGeom, innerGlowMat);
      this.centralNode.add(innerGlow);

      // 6. Orbital Halo Rings
      const ringGeom = new THREE.TorusGeometry(8.5, 0.035, 16, 120);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x0284c7,
        transparent: true,
        opacity: 0.4
      });
      this.orbitRing = new THREE.Mesh(ringGeom, ringMat);
      this.orbitRing.rotation.x = Math.PI / 3;
      this.masterGroup.add(this.orbitRing);

      const ringGeom2 = new THREE.TorusGeometry(12.5, 0.03, 16, 120);
      const ringMat2 = new THREE.MeshBasicMaterial({
        color: 0x8b5cf6,
        transparent: true,
        opacity: 0.3
      });
      const orbitRing2 = new THREE.Mesh(ringGeom2, ringMat2);
      orbitRing2.rotation.x = -Math.PI / 4;
      this.masterGroup.add(orbitRing2);

      // 7. Satellite Nodes: [Google, AEO, GEO, Customer Demand]
      const satelliteConfig = [
        { name: "search", color: 0x3b82f6, dist: 9.0, angle: 0 },
        { name: "aeo", color: 0x10b981, dist: 9.5, angle: Math.PI * 0.55 },
        { name: "geo", color: 0x8b5cf6, dist: 10.0, angle: Math.PI * 1.15 },
        { name: "demand", color: 0xf59e0b, dist: 11.0, angle: Math.PI * 1.7 }
      ];

      satelliteConfig.forEach((cfg) => {
        const satGeom = new THREE.SphereGeometry(0.7, 16, 16);
        const satMat = new THREE.MeshBasicMaterial({
          color: cfg.color,
          transparent: true,
          opacity: 0.75
        });
        const satMesh = new THREE.Mesh(satGeom, satMat);

        satMesh.position.x = Math.cos(cfg.angle) * cfg.dist;
        satMesh.position.y = Math.sin(cfg.angle) * cfg.dist * 0.45;
        satMesh.position.z = Math.sin(cfg.angle) * 3;

        this.masterGroup.add(satMesh);
        this.satellites.push({ mesh: satMesh, config: cfg, currentAngle: cfg.angle });
      });

      // 8. Connecting Line Lattice (Central Domain to Satellites)
      const linePositions = new Float32Array(this.satellites.length * 2 * 3);
      const lineGeom = new THREE.BufferGeometry();
      lineGeom.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x6366f1,
        transparent: true,
        opacity: 0.35
      });
      this.connectionLines = new THREE.LineSegments(lineGeom, lineMat);
      this.masterGroup.add(this.connectionLines);

      // 9. Data Dust Particles
      const dustCount = 350;
      const dustGeom = new THREE.BufferGeometry();
      const dustPos = new Float32Array(dustCount * 3);
      for (let i = 0; i < dustCount; i++) {
        dustPos[i * 3] = (Math.random() - 0.5) * 45;
        dustPos[i * 3 + 1] = (Math.random() - 0.5) * 45;
        dustPos[i * 3 + 2] = (Math.random() - 0.5) * 25;
      }
      dustGeom.setAttribute("position", new THREE.BufferAttribute(dustPos, 3));
      const dustMat = new THREE.PointsMaterial({
        color: 0x4f46e5,
        size: 0.14,
        transparent: true,
        opacity: 0.45
      });
      this.dustParticles = new THREE.Points(dustGeom, dustMat);
      this.scene.add(this.dustParticles);

      // 10. Event Listeners
      window.addEventListener("resize", () => this.onResize());
      window.addEventListener("mousemove", (e) => this.onMouseMove(e));
      window.addEventListener("scroll", () => this.onScroll(), { passive: true });

      this.isInitialized = true;
      this.onScroll();
      this.animate();
    } catch (err) {
      console.warn("Three.js Agent Universe error:", err);
    }
  }

  onResize() {
    if (!this.camera || !this.renderer) return;
    const width = window.innerWidth;
    const height = window.innerHeight;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  onMouseMove(e) {
    this.mouse.targetX = (e.clientX / window.innerWidth - 0.5) * 2;
    this.mouse.targetY = -(e.clientY / window.innerHeight - 0.5) * 2;
  }

  onScroll() {
    const maxScroll = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    this.targetScrollProgress = Math.min(1, Math.max(0, window.scrollY / maxScroll));
  }

  pulse() {
    if (!this.centralNode) return;
    this.rotationSpeed = 0.015;
    this.centralNode.scale.set(1.15, 1.15, 1.15);
    setTimeout(() => {
      this.rotationSpeed = 0.0025;
      if (this.centralNode) this.centralNode.scale.set(1, 1, 1);
    }, 700);
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (!this.masterGroup || !this.renderer || !this.scene || !this.camera) return;

    // Smooth mouse & scroll lerping
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.06;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.06;
    this.scrollProgress += (this.targetScrollProgress - this.scrollProgress) * 0.08;

    // Scroll-driven 3D choreo (shifts position, angle, and camera zoom through the sections)
    const scrollAngle = this.scrollProgress * Math.PI * 1.5;
    this.masterGroup.rotation.y = scrollAngle + this.mouse.x * 0.35;
    this.masterGroup.rotation.x = Math.sin(scrollAngle * 0.5) * 0.35 + this.mouse.y * 0.35;
    this.masterGroup.position.y = -this.scrollProgress * 6.5 + this.mouse.y * 1.5;
    this.masterGroup.position.z = -this.scrollProgress * 4;

    // Continuous spin
    if (this.centralNode) {
      this.centralNode.rotation.y += this.rotationSpeed;
      this.centralNode.rotation.z += this.rotationSpeed * 0.5;
    }

    // Orbit satellites and update connecting lines
    const lineArr = this.connectionLines.geometry.attributes.position.array;
    this.satellites.forEach((sat, i) => {
      sat.currentAngle += 0.004 * (1 + i * 0.2);
      sat.mesh.position.x = Math.cos(sat.currentAngle) * sat.config.dist;
      sat.mesh.position.y = Math.sin(sat.currentAngle) * sat.config.dist * 0.45;
      sat.mesh.position.z = Math.sin(sat.currentAngle) * 3;

      // Update line from central core (0,0,0) to satellite
      const idx = i * 6;
      lineArr[idx] = 0;
      lineArr[idx + 1] = 0;
      lineArr[idx + 2] = 0;
      lineArr[idx + 3] = sat.mesh.position.x;
      lineArr[idx + 4] = sat.mesh.position.y;
      lineArr[idx + 5] = sat.mesh.position.z;
    });
    this.connectionLines.geometry.attributes.position.needsUpdate = true;

    // Slow drifting dust
    if (this.dustParticles) {
      this.dustParticles.rotation.y += 0.0004;
    }

    this.renderer.render(this.scene, this.camera);
  }
}
