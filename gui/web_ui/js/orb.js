(function () {
    const ENERGY_BY_STATE = {
        idle: 0.32,
        ready: 0.5,
        listening: 0.95,
        processing: 0.78,
        error: 0.58,
    };

    function createParticles(count) {
        return Array.from({ length: count }, () => ({
            angle: Math.random() * Math.PI * 2,
            radius: 0.16 + Math.random() * 0.34,
            speed: 0.0015 + Math.random() * 0.0032,
            size: 0.6 + Math.random() * 2.2,
            drift: 0.5 + Math.random() * 0.8,
            alpha: 0.18 + Math.random() * 0.22,
        }));
    }

    function initializeMakiOrb(canvas) {
        if (!canvas || typeof canvas.getContext !== "function") {
            return {
                setState() {},
                setSpeaking() {},
                playSpeechPattern() {},
                resize() {},
            };
        }

        const context = canvas.getContext("2d");
        const particles = createParticles(54);
        const ripples = [];
        let width = 0;
        let height = 0;
        let pixelRatio = 1;
        let energy = ENERGY_BY_STATE.ready;
        let targetEnergy = ENERGY_BY_STATE.ready;
        let speakingActive = false;
        let speechAccent = 0;
        let speechTexture = 1;
        let nextRippleAt = 0;
        let hueShift = 0;
        let animationFrameId = 0;

        function resize() {
            const bounds = canvas.getBoundingClientRect();
            pixelRatio = window.devicePixelRatio || 1;
            width = Math.max(1, Math.floor(bounds.width * pixelRatio));
            height = Math.max(1, Math.floor(bounds.height * pixelRatio));
            canvas.width = width;
            canvas.height = height;
        }

        function setState(state) {
            targetEnergy = ENERGY_BY_STATE[state] ?? ENERGY_BY_STATE.ready;
        }

        function setSpeaking(active) {
            speakingActive = Boolean(active);
            if (speakingActive) {
                speechAccent = Math.max(speechAccent, 0.72);
            }
        }

        function playSpeechPattern(text) {
            speechAccent = 1;
            speechTexture = buildSpeechTexture(text);
            nextRippleAt = 0;
        }

        function draw(time) {
            speechAccent *= speakingActive ? 0.94 : 0.84;
            energy += (targetEnergy - energy) * 0.05;
            hueShift += 0.0015;

            if (speakingActive && (!nextRippleAt || time >= nextRippleAt)) {
                spawnRipple(ripples, time, speechTexture, speechAccent);
                nextRippleAt = time + 420 + ((1.2 - speechTexture) * 110) + Math.random() * 120;
            }

            const centerX = width / 2;
            const centerY = height / 2;
            const speakingWave = speakingActive ? (0.55 + (Math.sin(time * 0.0075) * 0.45)) : 0;
            const speakingBoost = speakingActive ? 0.24 : 0;
            const accentBoost = speechAccent * 0.28;
            const radius = Math.min(width, height) * (
                0.18 + (energy * 0.07) + (speakingBoost * 0.025) + (accentBoost * 0.015)
            );
            const pulse = 1
                + (Math.sin(time * 0.0011) * 0.04)
                + (energy * 0.02)
                + (speakingBoost * 0.05)
                + (speakingWave * 0.03)
                + (accentBoost * 0.05);
            const outerGlowRadius = radius * (1.98 + (speakingBoost * 0.45) + (accentBoost * 0.2));

            context.clearRect(0, 0, width, height);
            context.save();
            context.translate(centerX, centerY);

            drawOuterGlow(context, radius, outerGlowRadius, energy, speakingBoost, accentBoost);
            drawRipples(context, ripples, time, radius, pixelRatio, speakingActive);
            drawWaveformHalo(context, radius, time, pixelRatio, speakingBoost, accentBoost, speechTexture);
            drawTravelingHighlight(context, radius, time, pixelRatio, speakingBoost, accentBoost);
            drawAuraLayers(context, radius, pulse, time, energy, speakingBoost, accentBoost);
            drawParticles(context, particles, time, radius, pixelRatio, energy, speakingBoost, accentBoost, hueShift);

            context.restore();
            animationFrameId = window.requestAnimationFrame(draw);
        }

        resize();
        animationFrameId = window.requestAnimationFrame(draw);
        window.addEventListener("resize", resize);

        return {
            setState,
            setSpeaking,
            playSpeechPattern,
            resize,
            destroy() {
                window.cancelAnimationFrame(animationFrameId);
                window.removeEventListener("resize", resize);
            },
        };
    }

    function drawOuterGlow(context, radius, outerGlowRadius, energy, speakingBoost, accentBoost) {
        const outerGlow = context.createRadialGradient(0, 0, radius * 0.25, 0, 0, outerGlowRadius);
        outerGlow.addColorStop(0, `rgba(121, 220, 255, ${0.18 + (energy * 0.1) + (accentBoost * 0.12)})`);
        outerGlow.addColorStop(0.45, `rgba(78, 145, 255, ${0.11 + (energy * 0.08) + (speakingBoost * 0.05)})`);
        outerGlow.addColorStop(0.78, `rgba(125, 92, 255, ${0.08 + (energy * 0.06) + (speakingBoost * 0.03)})`);
        outerGlow.addColorStop(1, "rgba(0, 0, 0, 0)");
        context.fillStyle = outerGlow;
        context.beginPath();
        context.arc(0, 0, outerGlowRadius, 0, Math.PI * 2);
        context.fill();
    }

    function drawAuraLayers(context, radius, pulse, time, energy, speakingBoost, accentBoost) {
        for (let index = 0; index < 7; index += 1) {
            const layerRadius = radius * (0.88 + (index * 0.08)) * pulse;
            const layerGradient = context.createRadialGradient(0, 0, layerRadius * 0.1, 0, 0, layerRadius);
            const alphaBase = Math.max(
                0.03,
                0.18 - (index * 0.02) + (speakingBoost * 0.03) + (accentBoost * 0.04)
            );
            layerGradient.addColorStop(
                0,
                `rgba(140, 235, 255, ${alphaBase + (energy * 0.08) + (accentBoost * 0.08)})`
            );
            layerGradient.addColorStop(0.55, `rgba(97, 154, 255, ${alphaBase})`);
            layerGradient.addColorStop(1, "rgba(0, 0, 0, 0)");
            context.fillStyle = layerGradient;
            context.beginPath();
            context.arc(
                Math.sin((time * 0.0003) + index) * layerRadius * 0.07,
                Math.cos((time * 0.0004) + index) * layerRadius * 0.05,
                layerRadius,
                0,
                Math.PI * 2
            );
            context.fill();
        }
    }

    function drawParticles(context, particles, time, radius, pixelRatio, energy, speakingBoost, accentBoost, hueShift) {
        particles.forEach((particle, index) => {
            particle.angle += particle.speed * (1 + (energy * 0.7) + (speakingBoost * 1.2) + (accentBoost * 0.6));
            const radiusOffset = radius * (1.4 + (Math.sin((time * 0.0012 * particle.drift) + index) * 0.22));
            const x = Math.cos(particle.angle + hueShift) * radiusOffset * particle.radius;
            const y = Math.sin((particle.angle * 1.15) + hueShift) * radiusOffset * particle.radius;
            const particleGradient = context.createRadialGradient(
                x,
                y,
                0,
                x,
                y,
                particle.size * pixelRatio * 4
            );
            particleGradient.addColorStop(
                0,
                `rgba(218, 245, 255, ${particle.alpha + (energy * 0.08) + (accentBoost * 0.08)})`
            );
            particleGradient.addColorStop(1, "rgba(121, 220, 255, 0)");
            context.fillStyle = particleGradient;
            context.beginPath();
            context.arc(
                x,
                y,
                particle.size * pixelRatio * (0.9 + (energy * 0.35) + (accentBoost * 0.18)),
                0,
                Math.PI * 2
            );
            context.fill();
        });
    }

    function drawWaveformHalo(context, radius, time, pixelRatio, speakingBoost, accentBoost, speechTexture) {
        const haloRadius = radius * (1.02 + (speakingBoost * 0.08));
        const amplitude = radius * (0.012 + (speakingBoost * 0.03) + (accentBoost * 0.025));
        const segments = 88;
        const textureA = 2 + (speechTexture * 1.8);
        const textureB = 5 + (speechTexture * 2.6);

        context.beginPath();
        for (let index = 0; index <= segments; index += 1) {
            const progress = index / segments;
            const angle = progress * Math.PI * 2;
            const wave = (Math.sin((angle * textureA) - (time * 0.0048)) * 0.62)
                + (Math.cos((angle * textureB) + (time * 0.0034)) * 0.38);
            const dynamicRadius = haloRadius + (wave * amplitude);
            const x = Math.cos(angle) * dynamicRadius;
            const y = Math.sin(angle) * dynamicRadius;
            if (index === 0) {
                context.moveTo(x, y);
            } else {
                context.lineTo(x, y);
            }
        }
        context.closePath();
        context.lineWidth = pixelRatio * (1.25 + (speakingBoost * 0.7));
        context.strokeStyle = `rgba(129, 227, 255, ${0.12 + (speakingBoost * 0.16) + (accentBoost * 0.12)})`;
        context.stroke();
    }

    function drawTravelingHighlight(context, radius, time, pixelRatio, speakingBoost, accentBoost) {
        if (speakingBoost <= 0.01 && accentBoost <= 0.01) {
            return;
        }

        const ringRadius = radius * (1.08 + (speakingBoost * 0.06));
        const startAngle = (time * 0.0032) % (Math.PI * 2);
        const sweepAngle = 0.52 + (accentBoost * 0.35);

        context.beginPath();
        context.strokeStyle = `rgba(220, 247, 255, ${0.16 + (speakingBoost * 0.22) + (accentBoost * 0.16)})`;
        context.lineWidth = pixelRatio * (2.2 + (accentBoost * 1.6));
        context.lineCap = "round";
        context.arc(0, 0, ringRadius, startAngle, startAngle + sweepAngle);
        context.stroke();
        context.lineCap = "butt";
    }

    function drawRipples(context, ripples, time, radius, pixelRatio, speakingActive) {
        for (let index = ripples.length - 1; index >= 0; index -= 1) {
            const ripple = ripples[index];
            const age = time - ripple.startedAt;
            const progress = age / ripple.durationMs;
            if (progress >= 1) {
                ripples.splice(index, 1);
                continue;
            }

            const rippleRadius = radius * (0.96 + (progress * ripple.spread));
            context.beginPath();
            context.strokeStyle = `rgba(132, 235, 255, ${(1 - progress) * ripple.alpha * (speakingActive ? 1 : 0.65)})`;
            context.lineWidth = pixelRatio * (1.7 - (progress * 0.9));
            context.arc(0, 0, rippleRadius, 0, Math.PI * 2);
            context.stroke();
        }
    }

    function spawnRipple(ripples, time, speechTexture, speechAccent) {
        ripples.push({
            startedAt: time,
            durationMs: 720 + Math.random() * 160,
            spread: 1.28 + (speechTexture * 0.18) + (Math.random() * 0.12),
            alpha: 0.17 + (speechAccent * 0.12),
        });
    }

    function buildSpeechTexture(text) {
        const cleanedText = String(text || "").trim().toLowerCase();
        if (!cleanedText) {
            return 1;
        }

        const vowels = (cleanedText.match(/[aeiouy]/g) || []).length;
        const consonants = (cleanedText.match(/[bcdfghjklmnpqrstvwxyz]/g) || []).length;
        const words = cleanedText.split(/\s+/).filter(Boolean).length;
        const texture = 0.75 + Math.min(0.75, ((vowels * 0.03) + (consonants * 0.012) + (words * 0.06)));
        return Math.max(0.75, Math.min(1.5, texture));
    }

    window.MakiOrb = {
        init: initializeMakiOrb,
    };
})();
