import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export function ThreeCanvas({ pulseTrigger }) {
  const containerRef = useRef(null);
  const pulseRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });

  useEffect(() => {
    if (pulseTrigger) {
      pulseRef.current = 1.0;
    }
  }, [pulseTrigger]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene in Crisp Light Porcelain (NO BLACK, subtle elegant constellation)
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xf8faf8, 0.002);

    const camera = new THREE.PerspectiveCamera(
      52,
      window.innerWidth / window.innerHeight,
      0.1,
      1200
    );
    camera.position.set(0, 20, 175);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: "high-performance"
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0xf8faf8, 0);

    container.appendChild(renderer.domElement);

    // 2. Natural Ambient Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
    scene.add(ambientLight);

    const lightGreen = new THREE.DirectionalLight(0x5d9253, 0.9);
    lightGreen.position.set(60, 90, 70);
    scene.add(lightGreen);

    const lightCopper = new THREE.DirectionalLight(0xd46d25, 0.8);
    lightCopper.position.set(-60, 40, -40);
    scene.add(lightCopper);

    // 3. Ground Architectural Grid in Mint Aqua #8AD6D1 & Forest #5D9253 (Subtle)
    const gridHelper = new THREE.GridHelper(520, 32, 0x8ad6d1, 0x5d9253);
    gridHelper.position.y = -72;
    gridHelper.material.opacity = 0.16;
    gridHelper.material.transparent = true;
    scene.add(gridHelper);

    // 4. Luminous Constellation Nodes in 5D9253, 8AD6D1, D46D25
    const nodeCount = 38;
    const nodeGeometry = new THREE.SphereGeometry(1.0, 16, 16);
    const nodesGroup = new THREE.Group();
    const nodePositions = [];

    const colors = [
      0x5d9253, // Forest Sage Green
      0xd46d25, // Copper Terracotta
      0x8ad6d1, // Aqua Mint Teal
      0x5d9253,
      0x8ad6d1
    ];

    for (let i = 0; i < nodeCount; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: colors[i % colors.length],
        transparent: true,
        opacity: 0.7
      });
      const mesh = new THREE.Mesh(nodeGeometry, mat);
      const x = (Math.random() - 0.5) * 260;
      const y = (Math.random() - 0.5) * 90 - 15;
      const z = (Math.random() - 0.5) * 160 - 50;

      mesh.position.set(x, y, z);
      nodesGroup.add(mesh);
      nodePositions.push(new THREE.Vector3(x, y, z));
    }
    scene.add(nodesGroup);

    // 5. Connecting Filaments in Mint Aqua #8AD6D1
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x8ad6d1,
      transparent: true,
      opacity: 0.2
    });

    const linePoints = [];
    for (let i = 0; i < nodeCount; i++) {
      for (let j = i + 1; j < nodeCount; j++) {
        const dist = nodePositions[i].distanceTo(nodePositions[j]);
        if (dist < 55) {
          linePoints.push(nodePositions[i]);
          linePoints.push(nodePositions[j]);
        }
      }
    }

    const lineGeo = new THREE.BufferGeometry().setFromPoints(linePoints);
    const lineMesh = new THREE.LineSegments(lineGeo, lineMaterial);
    scene.add(lineMesh);

    // 6. Subtle Floating Amber & Mint Dust
    const particleCount = 100;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleSpeeds = [];

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 300;
      particlePositions[i + 1] = (Math.random() - 0.5) * 150;
      particlePositions[i + 2] = (Math.random() - 0.5) * 200;

      particleSpeeds.push({
        y: 0.03 + Math.random() * 0.05,
        x: (Math.random() - 0.5) * 0.02
      });
    }

    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 1.6,
      color: 0xd46d25, // Copper particles
      transparent: true,
      opacity: 0.4
    });

    const particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 7. Pulse Shockwave in Copper #D46D25
    const ringGeo = new THREE.RingGeometry(0.9, 1.3, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xd46d25,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide
    });
    const shockwave = new THREE.Mesh(ringGeo, ringMat);
    shockwave.rotation.x = Math.PI / 2;
    shockwave.position.y = -64;
    scene.add(shockwave);

    // Mouse listener
    const handleMouseMove = (e) => {
      mouseRef.current.targetX = (e.clientX / window.innerWidth - 0.5) * 20;
      mouseRef.current.targetY = -(e.clientY / window.innerHeight - 0.5) * 12;
    };
    window.addEventListener("mousemove", handleMouseMove, { passive: true });

    // Resize listener
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener("resize", handleResize);

    // Animation Loop
    let animationFrameId;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      // Mouse damping
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      camera.position.x = mouseRef.current.x;
      camera.position.y = 22 + mouseRef.current.y;
      camera.lookAt(0, 0, 0);

      nodesGroup.rotation.y = time * 0.02;
      lineMesh.rotation.y = time * 0.02;

      // Animate floating particles
      const positions = particleGeo.attributes.position.array;
      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        positions[i3 + 1] += particleSpeeds[i].y;
        positions[i3] += Math.sin(time + i) * 0.015;

        if (positions[i3 + 1] > 90) {
          positions[i3 + 1] = -70;
        }
      }
      particleGeo.attributes.position.needsUpdate = true;

      // Pulse shockwave
      if (pulseRef.current > 0) {
        pulseRef.current -= delta * 0.6;
        const progress = 1 - pulseRef.current;
        shockwave.scale.set(progress * 140, progress * 140, 1);
        ringMat.opacity = Math.max(0, pulseRef.current * 0.5);
      } else {
        ringMat.opacity = 0;
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return <div id="webgl-canvas-container" ref={containerRef} />;
}
