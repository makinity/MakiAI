/**
 * MakiAI Mobile Web Phone — Client Engine
 * Full-duplex Web Audio capture + WebSocket streaming + Neural TTS playback
 */

(function () {
    "use strict";

    // State
    const state = {
        inCall: false,
        isMuted: false,
        speakerBoost: false,
        ws: null,
        audioContext: null,
        mediaStream: null,
        audioInput: null,
        scriptProcessor: null,
        timerInterval: null,
        callStartEpoch: 0,
        audioQueue: [],
        isPlayingAudio: false,
        pin: localStorage.getItem("maki_phone_pin") || "",
    };

    // DOM Elements
    const elements = {
        connectionDot: document.getElementById("connection-dot"),
        brandName: document.getElementById("brand-name"),
        callStatusBadge: document.getElementById("call-status-badge"),
        callStatusText: document.getElementById("call-status-text"),
        visualizerWrap: document.querySelector(".visualizer-wrap"),
        callTimer: document.getElementById("call-timer"),
        callSubtext: document.getElementById("call-subtext"),
        transcriptContainer: document.getElementById("transcript-container"),
        btnCallAction: document.getElementById("btn-call-action"),
        btnMute: document.getElementById("btn-mute"),
        btnSpeaker: document.getElementById("btn-speaker"),
        quickChips: document.getElementById("quick-chips"),
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
                    // PIN Authentication Required
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

        // Clear audio queue
        state.audioQueue = [];
        state.isPlayingAudio = false;
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

    // ─── Server Messages & Audio Playback ────────────────────────────────────

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
            // Auto-start call on chip press
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
