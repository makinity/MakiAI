/**
 * MakiAI Mobile Web Phone — Multimodal Client Engine
 * Full-duplex Web Audio capture + WebSocket streaming + Neural TTS playback + Live Video Switching
 */

(function () {
    "use strict";

    // State
    const state = {
        inCall: false,
        isMuted: false,
        speakerBoost: false,
        videoMode: "orb", // "orb", "screen", "webcam", "phone_cam"
        facingMode: "user", // "user" or "environment"
        ws: null,
        audioContext: null,
        mediaStream: null,
        audioInput: null,
        scriptProcessor: null,
        audioPlayer: null,
        timerInterval: null,
        callStartEpoch: 0,
        audioQueue: [],
        isPlayingAudio: false,
        phoneCamStream: null,
        visionInterval: null,
        pin: localStorage.getItem("maki_phone_pin") || "",
    };

    // DOM Elements
    const elements = {
        connectionDot: document.getElementById("connection-dot"),
        brandName: document.getElementById("brand-name"),
        callStatusBadge: document.getElementById("call-status-badge"),
        callStatusText: document.getElementById("call-status-text"),
        visualizerWrap: document.getElementById("visualizer-wrap"),
        remoteVideoWrap: document.getElementById("remote-video-wrap"),
        remoteStreamImg: document.getElementById("remote-stream-img"),
        videoOverlayBadge: document.getElementById("video-overlay-badge"),
        localCamWrap: document.getElementById("local-cam-wrap"),
        localCamFeed: document.getElementById("local-cam-feed"),
        btnFlipCam: document.getElementById("btn-flip-cam"),
        visionCanvas: document.getElementById("vision-snapshot-canvas"),
        callTimer: document.getElementById("call-timer"),
        callSubtext: document.getElementById("call-subtext"),
        transcriptContainer: document.getElementById("transcript-container"),
        btnCallAction: document.getElementById("btn-call-action"),
        btnMute: document.getElementById("btn-mute"),
        btnSpeaker: document.getElementById("btn-speaker"),
        quickChips: document.getElementById("quick-chips"),
        videoModeBar: document.getElementById("video-mode-bar"),
        pinModal: document.getElementById("pin-modal"),
        pinInput: document.getElementById("pin-input"),
        btnPinCancel: document.getElementById("btn-pin-cancel"),
        btnPinSubmit: document.getElementById("btn-pin-submit"),
    };

    // ─── Initialization ───────────────────────────────────────────────────────

    function init() {
        if (elements.pinModal) {
            elements.pinModal.hidden = true;
        }
        bindEvents();
        checkServerInfo();
    }

    function bindEvents() {
        elements.btnCallAction.addEventListener("click", toggleCall);
        elements.btnMute.addEventListener("click", toggleMute);
        elements.btnSpeaker.addEventListener("click", toggleSpeaker);

        // Video Mode Buttons
        if (elements.videoModeBar) {
            elements.videoModeBar.addEventListener("click", (e) => {
                const btn = e.target.closest(".mode-btn");
                if (btn && btn.dataset.mode) {
                    setVideoMode(btn.dataset.mode);
                }
            });
        }

        // Camera Flip Button
        if (elements.btnFlipCam) {
            elements.btnFlipCam.addEventListener("click", toggleCameraFacing);
        }

        // Quick Command Chips
        if (elements.quickChips) {
            elements.quickChips.addEventListener("click", (e) => {
                const btn = e.target.closest(".chip");
                if (btn && btn.dataset.cmd) {
                    sendTextCommand(btn.dataset.cmd);
                }
            });
        }

        // PIN Modal
        if (elements.btnPinSubmit) {
            elements.btnPinSubmit.addEventListener("click", () => {
                const pinVal = elements.pinInput.value.trim();
                state.pin = pinVal;
                localStorage.setItem("maki_phone_pin", pinVal);
                elements.pinModal.hidden = true;
                startCall();
            });
        }
        if (elements.btnPinCancel) {
            elements.btnPinCancel.addEventListener("click", () => {
                elements.pinModal.hidden = true;
            });
        }
    }

    async function checkServerInfo() {
        try {
            const res = await fetch("/api/phone/info");
            if (res.ok) {
                const data = await res.json();
                if (data.bot_name && elements.brandName) {
                    elements.brandName.textContent = data.bot_name;
                }
                elements.connectionDot.classList.add("connected");
            }
        } catch (e) {
            console.warn("[Phone] Server info check failed:", e);
        }
    }

    // ─── Call Lifecycle ───────────────────────────────────────────────────────

    async function toggleCall() {
        if (state.inCall) {
            endCall();
        } else {
            await startCall();
        }
    }

    async function startCall() {
        setCallStatus("connecting", "Connecting...");
        addTranscriptBubble("Connecting to MakiAI server...", "system");

        try {
            // 1. Initialize AudioContext & Unlock Mobile Audio Player (Must happen synchronously on user gesture)
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            state.audioContext = new AudioCtx({ sampleRate: 16000 });
            if (state.audioContext.state === "suspended") {
                await state.audioContext.resume();
            }

            // Prime persistent HTML5 audio element for mobile browser autoplay bypass
            if (!state.audioPlayer) {
                state.audioPlayer = new Audio();
                state.audioPlayer.setAttribute("playsinline", "true");
                state.audioPlayer.setAttribute("webkit-playsinline", "true");
            }
            state.audioPlayer.src = "data:audio/mp3;base64,//uQxAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAFAAAACAAADAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMD////////////////////////////////////////////////////////////////";
            state.audioPlayer.play().catch((e) => console.log("[Phone] Audio primed:", e));

            // 2. Request Microphone Access
            state.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    channelCount: 1,
                    sampleRate: 16000,
                },
                video: false,
            });

            // 3. Connect WebSocket
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            const wsUrl = `${protocol}//${window.location.host}/ws/phone-stream?pin=${encodeURIComponent(state.pin)}`;
            state.ws = new WebSocket(wsUrl);
            state.ws.binaryType = "arraybuffer";

            state.ws.onopen = () => {
                onCallConnected();
            };

            state.ws.onmessage = (event) => {
                handleServerMessage(event.data);
            };

            state.ws.onerror = (err) => {
                console.error("[Phone] WebSocket error:", err);
                addTranscriptBubble("Call connection error.", "system");
            };

            state.ws.onclose = (e) => {
                console.log("[Phone] WebSocket closed:", e.code, e.reason);
                if (e.code === 4001) {
                    elements.pinModal.hidden = false;
                    addTranscriptBubble("Authentication PIN required.", "system");
                }
                endCall();
            };

        } catch (err) {
            console.error("[Phone] Start call failed:", err);
            addTranscriptBubble(`Microphone access error: ${err.message}`, "system");
            endCall();
        }
    }

    function onCallConnected() {
        state.inCall = true;
        state.isMuted = false;
        elements.btnCallAction.classList.add("in-call");
        elements.btnMute.disabled = false;
        elements.connectionDot.classList.add("connected");
        setCallStatus("active", "Live Call");
        elements.callSubtext.textContent = "Listening... Speak naturally";

        // Start Call Duration Timer
        state.callStartEpoch = Date.now();
        state.timerInterval = setInterval(updateCallTimer, 1000);
        updateCallTimer();

        // Start Mic Audio Processor
        startAudioCapture();

        // Default to Orb mode
        setVideoMode(state.videoMode || "orb", false);
    }

    function endCall() {
        state.inCall = false;
        elements.btnCallAction.classList.remove("in-call");
        elements.btnMute.disabled = true;
        elements.btnMute.classList.remove("active");
        setCallStatus("idle", "Standby");
        elements.callSubtext.textContent = "Tap Call to speak with your PC";
        setOrbState("idle");

        if (state.timerInterval) {
            clearInterval(state.timerInterval);
            state.timerInterval = null;
        }
        elements.callTimer.textContent = "00:00";

        // Stop Phone Camera if active
        stopPhoneCamera();

        // Stop Audio Capture
        if (state.scriptProcessor) {
            state.scriptProcessor.disconnect();
            state.scriptProcessor = null;
        }
        if (state.audioInput) {
            state.audioInput.disconnect();
            state.audioInput = null;
        }
        if (state.mediaStream) {
            state.mediaStream.getTracks().forEach((t) => t.stop());
            state.mediaStream = null;
        }
        if (state.audioContext && state.audioContext.state !== "closed") {
            try { state.audioContext.close(); } catch (_) {}
            state.audioContext = null;
        }

        // Close WebSocket
        if (state.ws) {
            try { state.ws.close(); } catch (_) {}
            state.ws = null;
        }

        // Reset visual view
        setVideoMode("orb", false);

        // Clear audio queue
        state.audioQueue = [];
        state.isPlayingAudio = false;
    }

    // ─── Video Mode & Camera Management ──────────────────────────────────────

    async function setVideoMode(mode, notifyServer = true) {
        state.videoMode = mode;

        // Update nav button states
        if (elements.videoModeBar) {
            elements.videoModeBar.querySelectorAll(".mode-btn").forEach((btn) => {
                btn.classList.toggle("active", btn.dataset.mode === mode);
            });
        }

        // Reset view visibility
        elements.visualizerWrap.hidden = (mode !== "orb");
        elements.remoteVideoWrap.hidden = (mode !== "screen" && mode !== "webcam");
        elements.localCamWrap.hidden = (mode !== "phone_cam");

        if (mode === "screen") {
            elements.videoOverlayBadge.textContent = "💻 PC Screen Share";
            stopPhoneCamera();
        } else if (mode === "webcam") {
            elements.videoOverlayBadge.textContent = "👁️ Laptop Built-in Cam";
            stopPhoneCamera();
        } else if (mode === "phone_cam") {
            await startPhoneCamera();
        } else {
            // Orb
            stopPhoneCamera();
        }

        // Notify server of new video mode
        if (notifyServer && state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({
                type: "set_video_mode",
                mode: mode,
            }));
        }
    }

    async function startPhoneCamera() {
        try {
            stopPhoneCamera();
            state.phoneCamStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: state.facingMode,
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
                audio: false,
            });

            if (elements.localCamFeed) {
                elements.localCamFeed.srcObject = state.phoneCamStream;
                elements.localCamFeed.play().catch(() => {});
            }

            // Start sending vision snapshots periodically
            state.visionInterval = setInterval(sendVisionSnapshot, 1000);
        } catch (err) {
            console.error("[Phone] Camera start failed:", err);
            addTranscriptBubble("Camera access error: " + err.message, "system");
            setVideoMode("orb");
        }
    }

    function stopPhoneCamera() {
        if (state.visionInterval) {
            clearInterval(state.visionInterval);
            state.visionInterval = null;
        }
        if (state.phoneCamStream) {
            state.phoneCamStream.getTracks().forEach((t) => t.stop());
            state.phoneCamStream = null;
        }
        if (elements.localCamFeed) {
            elements.localCamFeed.srcObject = null;
        }
    }

    async function toggleCameraFacing() {
        state.facingMode = state.facingMode === "user" ? "environment" : "user";
        if (elements.localCamFeed) {
            elements.localCamFeed.style.transform = state.facingMode === "user" ? "scaleX(-1)" : "none";
        }
        if (state.videoMode === "phone_cam") {
            await startPhoneCamera();
        }
    }

    function sendVisionSnapshot() {
        if (!state.inCall || state.videoMode !== "phone_cam" || !elements.localCamFeed || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
            return;
        }

        try {
            const canvas = elements.visionCanvas;
            const video = elements.localCamFeed;
            if (video.videoWidth === 0 || video.videoHeight === 0) return;

            canvas.width = 480;
            canvas.height = Math.round((video.videoHeight / video.videoWidth) * 480);
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            const dataUrl = canvas.toDataURL("image/jpeg", 0.65);
            const base64Data = dataUrl.split(",")[1];

            if (base64Data) {
                state.ws.send(JSON.stringify({
                    type: "camera_frame",
                    image_base64: base64Data,
                }));
            }
        } catch (e) {
            console.warn("[Phone] Snapshot send error:", e);
        }
    }

    // ─── Audio Capture & Streaming ───────────────────────────────────────────

    function startAudioCapture() {
        if (!state.audioContext || !state.mediaStream) return;

        state.audioInput = state.audioContext.createMediaStreamSource(state.mediaStream);
        const bufferSize = 2048;
        state.scriptProcessor = state.audioContext.createScriptProcessor(bufferSize, 1, 1);

        state.scriptProcessor.onaudioprocess = (e) => {
            if (!state.inCall || state.isMuted || !state.ws || state.ws.readyState !== WebSocket.OPEN) {
                return;
            }

            const inputData = e.inputBuffer.getChannelData(0);
            const pcm16 = convertFloat32ToInt16(inputData);

            // Send raw binary PCM16 16kHz chunk
            state.ws.send(pcm16.buffer);
        };

        state.audioInput.connect(state.scriptProcessor);
        state.scriptProcessor.connect(state.audioContext.destination);
    }

    function convertFloat32ToInt16(buffer) {
        let l = buffer.length;
        let buf = new Int16Array(l);
        while (l--) {
            let s = Math.max(-1, Math.min(1, buffer[l]));
            buf[l] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return buf;
    }

    // ─── Server Messages & Video / Audio Playback ────────────────────────────

    function handleServerMessage(data) {
        if (typeof data === "string") {
            try {
                const msg = JSON.parse(data);
                handleJsonEvent(msg);
            } catch (e) {
                console.warn("[Phone] Could not parse JSON message:", e);
            }
        }
    }

    function handleJsonEvent(msg) {
        switch (msg.type) {
            case "state":
                setOrbState(msg.state);
                if (msg.state === "listening") {
                    setCallStatus("active", "Listening...");
                    elements.callSubtext.textContent = "Listening to you...";
                } else if (msg.state === "thinking") {
                    setCallStatus("thinking", "Thinking...");
                    elements.callSubtext.textContent = "Processing request...";
                } else if (msg.state === "speaking") {
                    setCallStatus("speaking", "Speaking...");
                    elements.callSubtext.textContent = "Maki speaking...";
                } else {
                    setCallStatus("active", "Live Call");
                    elements.callSubtext.textContent = "Speak when ready...";
                }
                break;

            case "set_video_mode":
                if (msg.mode && msg.mode !== state.videoMode) {
                    setVideoMode(msg.mode, false);
                }
                break;

            case "video_frame":
                if (msg.image_base64 && elements.remoteStreamImg) {
                    elements.remoteStreamImg.src = `data:image/jpeg;base64,${msg.image_base64}`;
                }
                break;

            case "user_transcript":
                if (msg.text) {
                    addTranscriptBubble(msg.text, "user");
                }
                break;

            case "assistant_transcript":
                if (msg.text) {
                    addTranscriptBubble(msg.text, "assistant");
                }
                break;

            case "audio_chunk":
                if (msg.audio_base64) {
                    enqueueAudio(msg.audio_base64, msg.format || "wav");
                }
                break;

            case "system_info":
                if (msg.bot_name && elements.brandName) {
                    elements.brandName.textContent = msg.bot_name;
                }
                break;
        }
    }

    // ─── Seamless Audio Playback Queue ───────────────────────────────────────

    function enqueueAudio(base64Audio, format) {
        state.audioQueue.push({ data: base64Audio, format: format });
        if (!state.isPlayingAudio) {
            playNextAudio();
        }
    }

    async function playNextAudio() {
        if (state.audioQueue.length === 0) {
            state.isPlayingAudio = false;
            setOrbState("idle");
            return;
        }

        state.isPlayingAudio = true;
        setOrbState("speaking");
        const next = state.audioQueue.shift();

        try {
            const mime = next.format === "wav" ? "audio/wav" : "audio/mp3";
            const audioUrl = `data:${mime};base64,${next.data}`;

            if (!state.audioPlayer) {
                state.audioPlayer = new Audio();
                state.audioPlayer.setAttribute("playsinline", "true");
                state.audioPlayer.setAttribute("webkit-playsinline", "true");
            }

            state.audioPlayer.src = audioUrl;
            state.audioPlayer.volume = 1.0;

            state.audioPlayer.onended = () => {
                playNextAudio();
            };

            state.audioPlayer.onerror = (e) => {
                console.error("[Phone] Audio element error:", e);
                playNextAudio();
            };

            const playPromise = state.audioPlayer.play();
            if (playPromise !== undefined) {
                await playPromise;
            }
        } catch (err) {
            console.error("[Phone] Audio playback error:", err);
            playNextAudio();
        }
    }

    // ─── In-Call Controls ────────────────────────────────────────────────────

    function toggleMute() {
        state.isMuted = !state.isMuted;
        if (state.isMuted) {
            elements.btnMute.classList.add("active");
            elements.btnMute.querySelector(".btn-label").textContent = "Unmute";
            elements.callSubtext.textContent = "Microphone muted";
        } else {
            elements.btnMute.classList.remove("active");
            elements.btnMute.querySelector(".btn-label").textContent = "Mute";
            elements.callSubtext.textContent = "Listening... Speak naturally";
        }
    }

    function toggleSpeaker() {
        state.speakerBoost = !state.speakerBoost;
        elements.btnSpeaker.classList.toggle("active", state.speakerBoost);
    }

    function sendTextCommand(text) {
        if (!state.inCall) {
            startCall().then(() => {
                setTimeout(() => {
                    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                        state.ws.send(JSON.stringify({ type: "text_command", text: text }));
                    }
                }, 600);
            });
            return;
        }

        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ type: "text_command", text: text }));
        }
    }

    // ─── UI Helpers ──────────────────────────────────────────────────────────

    function setCallStatus(type, label) {
        elements.callStatusBadge.className = "call-badge " + type;
        elements.callStatusText.textContent = label;
    }

    function setOrbState(status) {
        elements.visualizerWrap.className = "visualizer-wrap " + (status || "idle");
    }

    function updateCallTimer() {
        const elapsedSecs = Math.floor((Date.now() - state.callStartEpoch) / 1000);
        const mins = String(Math.floor(elapsedSecs / 60)).padStart(2, "0");
        const secs = String(elapsedSecs % 60).padStart(2, "0");
        elements.callTimer.textContent = `${mins}:${secs}`;
    }

    function addTranscriptBubble(text, sender) {
        const wrap = document.createElement("div");
        wrap.className = `transcript-msg ${sender}`;
        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";
        bubble.textContent = text;
        wrap.appendChild(bubble);
        elements.transcriptContainer.appendChild(wrap);
        elements.transcriptContainer.scrollTop = elements.transcriptContainer.scrollHeight;
    }

    // Boot on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
