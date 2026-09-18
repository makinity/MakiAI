/**
 * MakiAI — Stark Solar Arc 3D Reactor & Holographic Core
 * Inspired by Stark Industries Arc Reactor & Holographic Solar Core (Golden Amber & Fiery Orange).
 * 
 * Features & Visual Indicators:
 *  - 3D Geodesic Icosahedron Wireframe with depth sorting and glowing vertices
 *  - Speaking Mode: Radiant Solar Singularity with vocal harmonic modulation, acoustic shockwave ripples, and radial flare spires
 *  - Listening Mode: Inward Accretion Vortex (particles stream into singularity), mic-reactive HUD brackets, bright electric nodes
 *  - Thinking Mode: Counter-rotating gyroscope acceleration, quantum synaptic data pulses traveling across edges
 *  - Searching Mode: 360° luminous holographic radar sweep beam and expanding sonar radar pings
 *  - Idle Mode: Hypnotic cosmic breathing cycle, orbital ember dust rings
 *  - Error Mode: Fiery crimson-amber alert pulse
 */

(function () {
    "use strict";

    const STATE_CONFIG = {
        idle: {
            speedX: 0.007,
            speedY: 0.010,
            speedZ: 0.004,
            ringSpeed: 0.006,
            energy: 0.45,
            coreScale: 0.17,
            coreColor: "#FFF285",
            glowColor: "rgba(255, 140, 0, 0.42)",
            wireColor: "rgba(255, 175, 45, 0.60)",
            needleLen: 1.45,
            inwardFlow: false,
        },
        listening: {
            speedX: 0.012,
            speedY: 0.018,
            speedZ: 0.009,
            ringSpeed: 0.022,
            energy: 0.95,
            coreScale: 0.22,
            coreColor: "#FFF9B8",
            glowColor: "rgba(255, 195, 20, 0.75)",
            wireColor: "rgba(255, 225, 90, 0.85)",
            needleLen: 1.80,
            inwardFlow: true,
        },
        thinking: {
            speedX: 0.028,
            speedY: -0.032,
            speedZ: 0.018,
            ringSpeed: -0.025,
            energy: 0.88,
            coreScale: 0.20,
            coreColor: "#FFDA33",
            glowColor: "rgba(255, 120, 0, 0.70)",
            wireColor: "rgba(255, 165, 30, 0.82)",
            needleLen: 1.65,
            inwardFlow: false,
        },
        searching: {
            speedX: 0.015,
            speedY: 0.020,
            speedZ: 0.008,
            ringSpeed: 0.030,
            energy: 0.80,
            coreScale: 0.19,
            coreColor: "#FFE866",
            glowColor: "rgba(255, 160, 20, 0.65)",
            wireColor: "rgba(255, 190, 50, 0.75)",
            needleLen: 1.70,
            inwardFlow: false,
        },
        processing: {
            speedX: 0.022,
            speedY: 0.026,
            speedZ: 0.014,
            ringSpeed: 0.020,
            energy: 0.85,
            coreScale: 0.20,
            coreColor: "#FFD033",
            glowColor: "rgba(255, 130, 10, 0.68)",
            wireColor: "rgba(255, 175, 40, 0.80)",
            needleLen: 1.65,
            inwardFlow: false,
        },
        speaking: {
            speedX: 0.014,
            speedY: 0.016,
            speedZ: 0.008,
            ringSpeed: 0.014,
            energy: 1.05,
            coreScale: 0.26,
            coreColor: "#FFFFFF",
            glowColor: "rgba(255, 165, 0, 0.88)",
            wireColor: "rgba(255, 210, 70, 0.95)",
            needleLen: 2.25,
            inwardFlow: false,
        },
        error: {
            speedX: 0.009,
            speedY: 0.012,
            speedZ: 0.005,
            ringSpeed: 0.008,
            energy: 0.65,
            coreScale: 0.18,
            coreColor: "#FF5533",
            glowColor: "rgba(255, 45, 10, 0.65)",
            wireColor: "rgba(255, 85, 40, 0.75)",
            needleLen: 1.35,
            inwardFlow: false,
        }
    };

    // ─── 3D Geodesic Icosahedron Geometry ────────────────────────────────────
    function createIcosahedron() {
        const phi = (1 + Math.sqrt(5)) / 2;
        const rawVertices = [
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
        ];

        const vertices = rawVertices.map(([x, y, z]) => {
            const len = Math.sqrt(x * x + y * y + z * z);
            return [x / len, y / len, z / len];
        });

        const edges = [
            [0, 11], [0, 5], [0, 1], [0, 7], [0, 10],
            [1, 5], [1, 9], [1, 8], [1, 7],
            [2, 11], [2, 4], [2, 3], [2, 6], [2, 10],
            [3, 9], [3, 4], [3, 8], [3, 6],
            [4, 5], [4, 9], [4, 11],
            [5, 9], [5, 11],
            [6, 7], [6, 8], [6, 10],
            [7, 8], [7, 10],
            [8, 9],
            [10, 11]
        ];

        const spires = vertices.map(v => [...v]);
        return { vertices, edges, spires };
    }

    // ─── Planetary Accretion Particle Rings ──────────────────────────────────
    function createParticles(count) {
        return Array.from({ length: count }, () => {
            const baseDist = 1.15 + Math.random() * 1.1;
            return {
                angle: Math.random() * Math.PI * 2,
                dist: baseDist,
                originalDist: baseDist,
                speed: (0.003 + Math.random() * 0.008),
                size: 0.8 + Math.random() * 2.2,
                alpha: 0.35 + Math.random() * 0.55,
                ringPlane: Math.random() > 0.35 ? 1 : 2, // 1 = main tilted disk, 2 = polar loop
                inwardProgress: Math.random(),
            };
        });
    }

    // ─── Synaptic Sparks for Thinking Mode ───────────────────────────────────
    function createSynapticSparks(count, edgesCount) {
        return Array.from({ length: count }, () => ({
            edgeIndex: Math.floor(Math.random() * edgesCount),
            progress: Math.random(),
            speed: 0.015 + Math.random() * 0.035,
            size: 1.6 + Math.random() * 1.8,
            alpha: 0.6 + Math.random() * 0.4,
        }));
    }

    // ─── Soundwave Ripple Shockwaves for Speaking Mode ───────────────────────
    function createSoundwaveRipples() {
        return [];
    }

    // ─── Main Maki Orb Controller ────────────────────────────────────────────
    function initializeMakiOrb(canvas) {
        if (!canvas || typeof canvas.getContext !== "function") {
            return { setState() {}, setSpeaking() {}, resize() {} };
        }

        const ctx = canvas.getContext("2d");
        const geometry = createIcosahedron();
        const particles = createParticles(120);
        const synapticSparks = createSynapticSparks(10, geometry.edges.length);
        const soundwaveRipples = createSoundwaveRipples();

        let width = 0;
        let height = 0;
        let pixelRatio = 1;

        let currentState = "idle";
        let isSpeaking = false;
        let speechPulse = 0.0;
        let lastRippleSpawn = 0;

        let rotX = 0.45;
        let rotY = 0.65;
        let rotZ = 0.20;
        let ringRot = 0.0;
        let radarAngle = 0.0;
        let sonarRadius = 0.0;
        let animId = 0;

        function resize() {
            const bounds = canvas.getBoundingClientRect();
            pixelRatio = window.devicePixelRatio || 1;
            width = Math.max(1, Math.floor(bounds.width * pixelRatio));
            height = Math.max(1, Math.floor(bounds.height * pixelRatio));
            canvas.width = width;
            canvas.height = height;
        }

        function setState(state) {
            const normalized = (state || "").toLowerCase();
            currentState = normalized in STATE_CONFIG ? normalized : "idle";
        }

        function setSpeaking(active) {
            isSpeaking = Boolean(active);
        }

        // 3D Point Rotation & Perspective Projection
        function project3D(x, y, z, rx, ry, rz, scale) {
            // Yaw (Y)
            let cosY = Math.cos(ry), sinY = Math.sin(ry);
            let x1 = x * cosY + z * sinY;
            let z1 = -x * sinY + z * cosY;

            // Pitch (X)
            let cosX = Math.cos(rx), sinX = Math.sin(rx);
            let y2 = y * cosX - z1 * sinX;
            let z2 = y * sinX + z1 * cosX;

            // Roll (Z)
            let cosZ = Math.cos(rz), sinZ = Math.sin(rz);
            let x3 = x1 * cosZ - y2 * sinZ;
            let y3 = x1 * sinZ + y2 * cosZ;

            const perspective = 3.6;
            const factor = scale / (perspective - z2 * 0.6);
            return {
                x: x3 * factor,
                y: y3 * factor,
                z: z2,
                scale: factor
            };
        }

        function draw(timestamp) {
            const effectiveState = isSpeaking ? "speaking" : currentState;
            const cfg = STATE_CONFIG[effectiveState] || STATE_CONFIG.idle;

            // Speech Cadence & Vocal Resonance Simulation
            if (isSpeaking) {
                const vocalHarmonic = Math.sin(timestamp * 0.015) * 0.35 + Math.sin(timestamp * 0.032) * 0.20 + Math.cos(timestamp * 0.008) * 0.15;
                speechPulse = Math.max(0.35, 0.70 + vocalHarmonic * 0.45);

                // Spawn acoustic shockwave ripples
                if (timestamp - lastRippleSpawn > 180 && soundwaveRipples.length < 6) {
                    soundwaveRipples.push({
                        radiusRatio: 0.25,
                        alpha: 0.85,
                        speed: 0.007 + Math.random() * 0.004,
                    });
                    lastRippleSpawn = timestamp;
                }
            } else {
                speechPulse *= 0.90;
            }

            // Update Rotational Physics
            rotX += cfg.speedX;
            rotY += cfg.speedY;
            rotZ += cfg.speedZ;
            ringRot += cfg.ringSpeed;
            radarAngle += 0.035;

            const cx = width / 2;
            const cy = height / 2;
            const minDim = Math.min(width, height);
            const baseScale = minDim * (0.22 + speechPulse * 0.045);

            ctx.clearRect(0, 0, width, height);
            ctx.save();
            ctx.translate(cx, cy);

            // ─── 1. Layered Ambient Solar Corona Glow ────────────────────────
            // Max safe glow radius within canvas bounds to eliminate box edges
            const maxSafeRadius = minDim * 0.44;
            const coronaRadius = Math.min(maxSafeRadius, baseScale * (2.4 + speechPulse * 0.6));
            
            const coronaGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, coronaRadius);
            if (effectiveState === "speaking") {
                coronaGrad.addColorStop(0, "rgba(255, 185, 40, 0.45)");
                coronaGrad.addColorStop(0.25, "rgba(255, 130, 0, 0.25)");
                coronaGrad.addColorStop(0.60, "rgba(255, 70, 0, 0.08)");
                coronaGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
            } else if (effectiveState === "listening") {
                coronaGrad.addColorStop(0, "rgba(255, 210, 50, 0.38)");
                coronaGrad.addColorStop(0.30, "rgba(255, 160, 0, 0.18)");
                coronaGrad.addColorStop(0.70, "rgba(255, 90, 0, 0.04)");
                coronaGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
            } else if (effectiveState === "thinking") {
                coronaGrad.addColorStop(0, "rgba(255, 150, 0, 0.35)");
                coronaGrad.addColorStop(0.35, "rgba(255, 95, 0, 0.15)");
                coronaGrad.addColorStop(0.75, "rgba(200, 45, 0, 0.03)");
                coronaGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
            } else {
                // Idle
                const breath = 0.5 + 0.5 * Math.sin(timestamp * 0.002);
                coronaGrad.addColorStop(0, `rgba(255, 150, 20, ${0.22 + breath * 0.08})`);
                coronaGrad.addColorStop(0.35, `rgba(255, 95, 0, ${0.08 + breath * 0.04})`);
                coronaGrad.addColorStop(0.75, "rgba(200, 45, 0, 0.02)");
                coronaGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
            }

            ctx.fillStyle = coronaGrad;
            ctx.beginPath();
            ctx.arc(0, 0, coronaRadius, 0, Math.PI * 2);
            ctx.fill();

            // ─── 2. Searching Mode: Holographic Radar Sweep Beam ─────────────
            if (effectiveState === "searching") {
                drawRadarSweep(minDim * 0.40, radarAngle, pixelRatio);
            }

            // ─── 3. Acoustic Soundwave Ripples (Speaking Mode) ───────────────
            drawSoundwaveRipples(minDim, pixelRatio);

            // ─── 4. Project 3D Vertices (Geodesic Wireframe Sphere) ──────────
            const wireframeScale = baseScale * 1.35;
            const projectedVertices = geometry.vertices.map(([vx, vy, vz]) => {
                return project3D(vx, vy, vz, rotX, rotY, rotZ, wireframeScale);
            });

            // ─── 5. Planetary Accretion Particle Rings (Back-half) ───────────
            drawParticles(particles, ringRot, baseScale, pixelRatio, true, timestamp, cfg.inwardFlow);

            // ─── 6. Floating Holographic HUD Arc Brackets ────────────────────
            drawArcBrackets(baseScale, ringRot, effectiveState, speechPulse, timestamp);

            // ─── 7. 3D Wireframe Back-Half Edges (avgZ <= 0) ─────────────────
            ctx.lineWidth = pixelRatio * (1.1 + speechPulse * 0.4);
            geometry.edges.forEach(([i, j]) => {
                const p1 = projectedVertices[i];
                const p2 = projectedVertices[j];
                const avgZ = (p1.z + p2.z) / 2;
                if (avgZ <= 0) {
                    const alpha = Math.max(0.12, 0.35 + avgZ * 0.25 + speechPulse * 0.25);
                    ctx.strokeStyle = `rgba(255, 145, 20, ${alpha})`;
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                }
            });

            // ─── 8. Thinking Mode: Quantum Synaptic Sparks along Edges ───────
            if (effectiveState === "thinking" || effectiveState === "processing") {
                drawSynapticSparks(projectedVertices, synapticSparks, pixelRatio);
            }

            // ─── 9. Radial Energy Needles (Lasers shooting outward) ──────────
            const needleMultiplier = cfg.needleLen + speechPulse * 0.85;
            geometry.spires.forEach((spire, idx) => {
                const pCore = project3D(0, 0, 0, rotX, rotY, rotZ, baseScale);
                const pTip = project3D(
                    spire[0] * needleMultiplier,
                    spire[1] * needleMultiplier,
                    spire[2] * needleMultiplier,
                    rotX, rotY, rotZ, baseScale
                );

                const needleGrad = ctx.createLinearGradient(pCore.x, pCore.y, pTip.x, pTip.y);
                needleGrad.addColorStop(0, "rgba(255, 255, 230, 0.95)");
                needleGrad.addColorStop(0.35, effectiveState === "speaking" ? "rgba(255, 200, 40, 0.85)" : "rgba(255, 160, 0, 0.70)");
                needleGrad.addColorStop(1, "rgba(255, 70, 0, 0)");

                ctx.lineWidth = pixelRatio * (1.4 + (idx % 2 === 0 ? 1.0 : 0.3) + speechPulse * 0.9);
                ctx.strokeStyle = needleGrad;
                ctx.beginPath();
                ctx.moveTo(pCore.x, pCore.y);
                ctx.lineTo(pTip.x, pTip.y);
                ctx.stroke();
            });

            // ─── 10. Central Singularity / Solar Reactor Core ────────────────
            const coreRadius = baseScale * (cfg.coreScale + speechPulse * 0.09);
            const coreGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, coreRadius * 2.0);
            coreGrad.addColorStop(0, "#FFFFFF");
            coreGrad.addColorStop(0.22, cfg.coreColor);
            coreGrad.addColorStop(0.55, "#FF8C00");
            coreGrad.addColorStop(0.85, "rgba(255, 60, 0, 0.35)");
            coreGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = coreGrad;
            ctx.beginPath();
            ctx.arc(0, 0, coreRadius * 2.0, 0, Math.PI * 2);
            ctx.fill();

            // Inner core bright disk
            ctx.fillStyle = "#FFFFFF";
            ctx.beginPath();
            ctx.arc(0, 0, coreRadius * 0.65, 0, Math.PI * 2);
            ctx.fill();

            // ─── 11. 3D Wireframe Front-Half Edges (avgZ > 0) ────────────────
            ctx.lineWidth = pixelRatio * (1.5 + speechPulse * 0.7);
            geometry.edges.forEach(([i, j]) => {
                const p1 = projectedVertices[i];
                const p2 = projectedVertices[j];
                const avgZ = (p1.z + p2.z) / 2;
                if (avgZ > 0) {
                    const alpha = Math.min(0.98, 0.55 + avgZ * 0.45 + speechPulse * 0.30);
                    ctx.strokeStyle = `rgba(255, 195, 45, ${alpha})`;
                    ctx.beginPath();
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                }
            });

            // ─── 12. Vertices Glowing Nodes ─────────────────────────────────
            projectedVertices.forEach(p => {
                const nodeSize = pixelRatio * (1.8 + (p.z + 1) * 1.5 + speechPulse * 1.4);
                const nodeAlpha = Math.max(0.3, 0.70 + p.z * 0.30);
                ctx.fillStyle = p.z > 0 ? `rgba(255, 245, 165, ${nodeAlpha})` : `rgba(255, 175, 45, ${nodeAlpha * 0.65})`;
                ctx.beginPath();
                ctx.arc(p.x, p.y, nodeSize, 0, Math.PI * 2);
                ctx.fill();
            });

            // ─── 13. Planetary Accretion Particle Rings (Front-half) ─────────
            drawParticles(particles, ringRot, baseScale, pixelRatio, false, timestamp, cfg.inwardFlow);

            ctx.restore();
            animId = window.requestAnimationFrame(draw);
        }

        // ─── Particles & Accretion Inward Vortex ─────────────────────────────
        function drawParticles(partList, rRot, scale, pRatio, isBack, time, isInward) {
            partList.forEach(p => {
                p.angle += p.speed;

                // Inward flow for listening accretion vortex
                if (isInward) {
                    p.dist -= 0.008;
                    if (p.dist < 0.25) {
                        p.dist = 1.6 + Math.random() * 0.8;
                    }
                } else {
                    // Smoothly ease back to original distance
                    p.dist += (p.originalDist - p.dist) * 0.04;
                }

                let px, py, pz;
                if (p.ringPlane === 1) {
                    const rad = p.dist * scale;
                    const rawX = Math.cos(p.angle + rRot) * rad;
                    const rawZ = Math.sin(p.angle + rRot) * rad;
                    const rawY = Math.sin(p.angle * 2 + time * 0.002) * (scale * 0.08);
                    const proj = project3D(rawX / scale, rawY / scale, rawZ / scale, 0.65, ringRot * 0.5, 0.35, scale);
                    px = proj.x; py = proj.y; pz = proj.z;
                } else {
                    const rad = (p.dist * 0.88) * scale;
                    const rawY = Math.sin(p.angle - rRot) * rad;
                    const rawZ = Math.cos(p.angle - rRot) * rad;
                    const rawX = Math.cos(p.angle * 3) * (scale * 0.06);
                    const proj = project3D(rawX / scale, rawY / scale, rawZ / scale, 0.25, 0.75, ringRot * 0.7, scale);
                    px = proj.x; py = proj.y; pz = proj.z;
                }

                if ((isBack && pz > 0) || (!isBack && pz <= 0)) {
                    return;
                }

                const size = pRatio * (p.size * (1 + (pz + 1) * 0.5) + speechPulse * 0.6);
                const alpha = Math.min(1.0, Math.max(0.12, p.alpha * (0.65 + (pz + 1) * 0.35)));

                const pGrad = ctx.createRadialGradient(px, py, 0, px, py, size * 2.6);
                pGrad.addColorStop(0, `rgba(255, 245, 175, ${alpha})`);
                pGrad.addColorStop(0.38, `rgba(255, 145, 0, ${alpha * 0.75})`);
                pGrad.addColorStop(1, "rgba(255, 60, 0, 0)");

                ctx.fillStyle = pGrad;
                ctx.beginPath();
                ctx.arc(px, py, size * 2.6, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        // ─── Soundwave Ripples for Speaking ──────────────────────────────────
        function drawSoundwaveRipples(dim, pRatio) {
            for (let i = soundwaveRipples.length - 1; i >= 0; i--) {
                const rip = soundwaveRipples[i];
                rip.radiusRatio += rip.speed;
                rip.alpha -= 0.012;

                if (rip.alpha <= 0 || rip.radiusRatio > 0.44) {
                    soundwaveRipples.splice(i, 1);
                    continue;
                }

                const r = dim * rip.radiusRatio;
                ctx.beginPath();
                ctx.arc(0, 0, r, 0, Math.PI * 2);
                ctx.strokeStyle = `rgba(255, 185, 40, ${rip.alpha * 0.65})`;
                ctx.lineWidth = pRatio * (1.5 + (1 - rip.radiusRatio) * 2.0);
                ctx.stroke();
            }
        }

        // ─── Synaptic Sparks for Thinking ────────────────────────────────────
        function drawSynapticSparks(projVerts, sparks, pRatio) {
            sparks.forEach(sp => {
                sp.progress += sp.speed;
                if (sp.progress >= 1.0) {
                    sp.progress = 0;
                    sp.edgeIndex = Math.floor(Math.random() * geometry.edges.length);
                }

                const [i, j] = geometry.edges[sp.edgeIndex];
                const p1 = projVerts[i];
                const p2 = projVerts[j];

                const sx = p1.x + (p2.x - p1.x) * sp.progress;
                const sy = p1.y + (p2.y - p1.y) * sp.progress;
                const sz = p1.z + (p2.z - p1.z) * sp.progress;

                const sparkSize = pRatio * (sp.size + (sz + 1) * 1.2);
                const sparkAlpha = Math.min(1.0, sp.alpha * (0.8 + (sz + 1) * 0.2));

                const sparkGrad = ctx.createRadialGradient(sx, sy, 0, sx, sy, sparkSize * 2.5);
                sparkGrad.addColorStop(0, `rgba(255, 255, 255, ${sparkAlpha})`);
                sparkGrad.addColorStop(0.4, `rgba(255, 210, 50, ${sparkAlpha * 0.8})`);
                sparkGrad.addColorStop(1, "rgba(255, 120, 0, 0)");

                ctx.fillStyle = sparkGrad;
                ctx.beginPath();
                ctx.arc(sx, sy, sparkSize * 2.5, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        // ─── Holographic Radar Sweep for Searching ───────────────────────────
        function drawRadarSweep(radius, angle, pRatio) {
            ctx.save();
            const sweepGrad = ctx.createRadialGradient(0, 0, 0, 0, 0, radius);
            sweepGrad.addColorStop(0, "rgba(255, 200, 50, 0.25)");
            sweepGrad.addColorStop(0.7, "rgba(255, 140, 0, 0.08)");
            sweepGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

            ctx.fillStyle = sweepGrad;
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.arc(0, 0, radius, angle, angle + 0.65);
            ctx.closePath();
            ctx.fill();

            // Leading scanning beam line
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(Math.cos(angle + 0.65) * radius, Math.sin(angle + 0.65) * radius);
            ctx.strokeStyle = "rgba(255, 230, 100, 0.65)";
            ctx.lineWidth = pRatio * 1.8;
            ctx.stroke();
            ctx.restore();
        }

        // ─── Floating Holographic HUD Arc Brackets ───────────────────────────
        function drawArcBrackets(scale, rRot, state, pulse, time) {
            const bracketRadius = scale * (1.45 + (state === "listening" ? 0.12 : 0) + pulse * 0.08);
            const segments = [
                { start: rRot * 1.2, span: 0.95 },
                { start: rRot * 1.2 + Math.PI, span: 0.75 },
                { start: -rRot * 0.8 + Math.PI * 0.5, span: 0.55 }
            ];

            segments.forEach(seg => {
                ctx.beginPath();
                ctx.arc(0, 0, bracketRadius, seg.start, seg.start + seg.span);
                ctx.strokeStyle = state === "speaking" ? "rgba(255, 185, 40, 0.55)" : "rgba(255, 160, 20, 0.35)";
                ctx.lineWidth = pixelRatio * (2.2 + pulse * 1.0);
                ctx.stroke();

                // Bright glowing reticle nodes
                ctx.beginPath();
                ctx.arc(0, 0, bracketRadius, seg.start, seg.start + 0.04);
                ctx.strokeStyle = "rgba(255, 245, 140, 0.95)";
                ctx.lineWidth = pixelRatio * 4.8;
                ctx.stroke();
            });
        }

        resize();
        animId = window.requestAnimationFrame(draw);
        window.addEventListener("resize", resize);

        return {
            setState,
            setSpeaking,
            resize,
            destroy() {
                window.cancelAnimationFrame(animId);
                window.removeEventListener("resize", resize);
            }
        };
    }

    window.MakiOrb = {
        init: initializeMakiOrb
    };
})();
