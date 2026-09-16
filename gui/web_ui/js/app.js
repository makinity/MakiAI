(function () {
    const UI_STATE_POLL_INTERVAL_MS = 180;

    const state = {
        botName: "MakiAI",
        status: {
            label: "Preparing desktop bridge...",
            state: "ready",
        },
        micActive: false,
        autoListenEnabled: false,
        speakingActive: false,
        commandBusy: false,
        activity: [],
        bridge: null,
        orb: null,
        openPanelId: null,
        pollTimer: null,
        pollRequestActive: false,
        settingsStatusTimer: null,
    };

    const elements = {};

    document.addEventListener("DOMContentLoaded", () => {
        cacheElements();
        bindEvents();
        initializeOrb();
        bootstrapUi();
    });

    function cacheElements() {
        elements.statusPanel = document.getElementById("status-panel");
        elements.commandPanel = document.getElementById("command-panel");
        elements.activityPanel = document.getElementById("activity-panel");
        elements.settingsPanel = document.getElementById("settings-panel");
        elements.sceneBackdrop = document.getElementById("scene-backdrop");
        elements.toggleButtons = Array.from(document.querySelectorAll("[data-panel-target]"));
        elements.closeButtons = Array.from(document.querySelectorAll("[data-close-panel]"));
        elements.statusPill = document.getElementById("status-pill");
        elements.statusLabel = document.getElementById("status-label");
        elements.statusMode = document.getElementById("status-mode");
        elements.orbCaptionValue = document.getElementById("orb-caption-value");
        elements.activityList = document.getElementById("activity-list");
        elements.activityCount = document.getElementById("activity-count");
        elements.activityScrollWrap = document.getElementById("activity-scroll-wrap");
        elements.commandInput = document.getElementById("command-input");
        elements.sendButton = document.getElementById("send-button");
        elements.micButton = document.getElementById("mic-button");
        elements.brandTitle = document.querySelector(".brand-title");

        // Settings inputs
        elements.saveSettingsBtn = document.getElementById("save-settings-btn");
        elements.settingsStatusMsg = document.getElementById("settings-status-msg");
        elements.settingAppName = document.getElementById("setting-app-name");
        elements.settingWakeWord = document.getElementById("setting-wake-word");
        elements.settingPttHotkey = document.getElementById("setting-ptt-hotkey");
        elements.settingGeminiKey = document.getElementById("setting-gemini-key");
        elements.settingGroqKey = document.getElementById("setting-groq-key");
        elements.settingElevenKey = document.getElementById("setting-eleven-key");
        elements.settingElevenVoice = document.getElementById("setting-eleven-voice");
        elements.settingTtsFallback = document.getElementById("setting-tts-fallback");
        elements.settingKbPath = document.getElementById("setting-kb-path");

        // Interactive Modal elements
        elements.modalOverlay = document.getElementById("interactive-modal-overlay");
        elements.modalCloseBtn = document.getElementById("modal-close-btn");
        elements.modalCancelBtn = document.getElementById("modal-cancel-btn");
        elements.modalSaveBtn = document.getElementById("modal-save-btn");
        elements.modalTitleInput = document.getElementById("modal-deadline-title");
        elements.modalDateInput = document.getElementById("modal-deadline-date");
        elements.modalTimeInput = document.getElementById("modal-deadline-time");
        elements.categoryPills = Array.from(document.querySelectorAll(".category-pill"));
        elements.priorityRadios = Array.from(document.querySelectorAll("input[name='deadline-priority']"));
    }

    function bindEvents() {
        elements.sendButton.addEventListener("click", handleSend);
        elements.micButton.addEventListener("click", handleToggleMic);
        elements.commandInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                handleSend();
                return;
            }

            if (event.key === "Escape") {
                closeAllPanels();
            }
        });

        if (elements.saveSettingsBtn) {
            elements.saveSettingsBtn.addEventListener("click", handleSaveSettings);
        }

        // Modal category pill clicks
        if (elements.categoryPills) {
            elements.categoryPills.forEach((pill) => {
                pill.addEventListener("click", () => {
                    elements.categoryPills.forEach((p) => p.classList.remove("active"));
                    pill.classList.add("active");
                });
            });
        }

        // Modal action buttons
        if (elements.modalCloseBtn) {
            elements.modalCloseBtn.addEventListener("click", handleDismissModal);
        }
        if (elements.modalCancelBtn) {
            elements.modalCancelBtn.addEventListener("click", handleDismissModal);
        }
        if (elements.modalSaveBtn) {
            elements.modalSaveBtn.addEventListener("click", handleSaveDeadlineModal);
        }

        // Password visibility toggles
        document.querySelectorAll(".btn-toggle-vis").forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetId = btn.dataset.target;
                const input = document.getElementById(targetId);
                if (input) {
                    input.type = input.type === "password" ? "text" : "password";
                }
            });
        });

        elements.sceneBackdrop.addEventListener("click", closeAllPanels);
        elements.closeButtons.forEach((button) => {
            button.addEventListener("click", closeAllPanels);
        });

        elements.toggleButtons.forEach((button) => {
            button.addEventListener("click", () => {
                togglePanel(button.dataset.panelTarget);
            });
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                if (elements.modalOverlay && !elements.modalOverlay.hidden) {
                    handleDismissModal();
                } else {
                    closeAllPanels();
                }
            }
        });
    }

    function initializeOrb() {
        if (window.MakiOrb && typeof window.MakiOrb.init === "function") {
            state.orb = window.MakiOrb.init(document.getElementById("orb-canvas"));
        }
        renderStatus();
    }

    async function bootstrapUi() {
        state.bridge = await waitForBridge();

        if (!state.bridge) {
            state.status = {
                label: "Desktop bridge unavailable.",
                state: "error",
            };
            state.activity = [
                {
                    type: "system",
                    text: "Frontend preview mode: the Python bridge is not attached in this context.",
                    timestamp: nowTimestamp(),
                },
            ];
            renderAll();
            return;
        }

        try {
            applyBackendState(await state.bridge.get_bootstrap_data());
            renderAll();
            startStatePolling();

            try {
                applyBackendState(await state.bridge.start_voice_standby());
            } catch (error) {
                state.status = {
                    label: "Voice standby could not start.",
                    state: "error",
                };
                state.activity.push({
                    type: "system",
                    text: `Voice standby could not start: ${error.message || error}`,
                    timestamp: nowTimestamp(),
                });
            }
            renderAll();
        } catch (error) {
            state.status = {
                label: "Desktop bridge unavailable.",
                state: "error",
            };
            state.activity = [
                {
                    type: "system",
                    text: `Bridge bootstrap failed: ${error.message || error}`,
                    timestamp: nowTimestamp(),
                },
            ];
            renderAll();
        }
    }

    async function waitForBridge() {
        if (window.pywebview && window.pywebview.api) {
            return window.pywebview.api;
        }

        return new Promise((resolve) => {
            let settled = false;

            function finish(value) {
                if (settled) {
                    return;
                }
                settled = true;
                window.removeEventListener("pywebviewready", handleReady);
                resolve(value);
            }

            function handleReady() {
                finish(window.pywebview && window.pywebview.api ? window.pywebview.api : null);
            }

            window.addEventListener("pywebviewready", handleReady);
            window.setTimeout(() => finish(window.pywebview && window.pywebview.api ? window.pywebview.api : null), 900);
        });
    }

    function startStatePolling() {
        stopStatePolling();
        state.pollTimer = window.setInterval(refreshUiState, UI_STATE_POLL_INTERVAL_MS);
    }

    function stopStatePolling() {
        if (!state.pollTimer) {
            return;
        }

        window.clearInterval(state.pollTimer);
        state.pollTimer = null;
    }

    async function refreshUiState() {
        if (!state.bridge || state.pollRequestActive) {
            return;
        }

        state.pollRequestActive = true;
        try {
            applyBackendState(await state.bridge.get_ui_state());
            renderAll();
        } catch (error) {
            state.status = {
                label: "UI state refresh failed.",
                state: "error",
            };
            renderAll();
            stopStatePolling();
        } finally {
            state.pollRequestActive = false;
        }
    }

    async function handleSend() {
        const command = elements.commandInput.value.trim();

        if (!state.bridge) {
            state.status = {
                label: "Desktop bridge unavailable.",
                state: "error",
            };
            if (command) {
                state.activity.push({
                    type: "user",
                    text: command,
                    timestamp: nowTimestamp(),
                });
            }
            state.activity.push({
                type: "system",
                text: "Command could not be sent because the Python desktop bridge is unavailable.",
                timestamp: nowTimestamp(),
            });
            renderAll();
            return;
        }

        state.commandBusy = true;
        renderAll();
        try {
            const payload = await state.bridge.send_command(command);
            applyBackendState(payload);
            if (payload.ok) {
                elements.commandInput.value = "";
            }
            renderAll();
        } catch (error) {
            state.status = {
                label: "Command send failed.",
                state: "error",
            };
            state.activity.push({
                type: "system",
                text: `Command send failed: ${error.message || error}`,
                timestamp: nowTimestamp(),
            });
            renderAll();
        } finally {
            state.commandBusy = false;
            renderAll();
        }
    }

    async function handleToggleMic() {
        if (!state.bridge) {
            state.autoListenEnabled = !state.autoListenEnabled;
            state.micActive = false;
            state.status = {
                label: state.autoListenEnabled
                    ? "Voice standby enabled in preview mode."
                    : "Voice standby paused in preview mode.",
                state: "ready",
            };
            state.activity.push({
                type: "system",
                text: state.autoListenEnabled
                    ? "Preview voice standby enabled."
                    : "Preview voice standby disabled.",
                timestamp: nowTimestamp(),
            });
            renderAll();
            return;
        }

        try {
            applyBackendState(await state.bridge.toggle_mic());
            renderAll();
        } catch (error) {
            state.status = {
                label: "Voice standby toggle failed.",
                state: "error",
            };
            state.activity.push({
                type: "system",
                text: `Voice standby toggle failed: ${error.message || error}`,
                timestamp: nowTimestamp(),
            });
            renderAll();
        }
    }

    // ─── Settings Load & Save ────────────────────────────────────────────────

    async function loadSettings() {
        if (!state.bridge || typeof state.bridge.get_settings !== "function") {
            return;
        }

        try {
            const cfg = await state.bridge.get_settings();
            if (!cfg) return;

            if (elements.settingAppName) elements.settingAppName.value = cfg.app_name || "";
            if (elements.settingWakeWord) elements.settingWakeWord.value = cfg.wake_word || "";
            if (elements.settingPttHotkey) elements.settingPttHotkey.value = cfg.ptt_hotkey || "";
            if (elements.settingGeminiKey) elements.settingGeminiKey.value = cfg.gemini_api_key || "";
            if (elements.settingGroqKey) elements.settingGroqKey.value = cfg.groq_api_key || "";
            if (elements.settingElevenKey) elements.settingElevenKey.value = cfg.elevenlabs_api_key || "";
            if (elements.settingElevenVoice) elements.settingElevenVoice.value = cfg.elevenlabs_voice_id || "";
            if (elements.settingTtsFallback) elements.settingTtsFallback.checked = Boolean(cfg.tts_fallback);
            if (elements.settingKbPath) elements.settingKbPath.value = cfg.kb_path || "";
        } catch (err) {
            console.error("[Settings] Failed to load settings:", err);
        }
    }

    async function handleSaveSettings() {
        if (!state.bridge || typeof state.bridge.save_settings !== "function") {
            showSettingsStatus("Desktop bridge unavailable", true);
            return;
        }

        const payload = {
            app_name: elements.settingAppName ? elements.settingAppName.value.trim() : "",
            wake_word: elements.settingWakeWord ? elements.settingWakeWord.value.trim() : "",
            ptt_hotkey: elements.settingPttHotkey ? elements.settingPttHotkey.value.trim() : "",
            gemini_api_key: elements.settingGeminiKey ? elements.settingGeminiKey.value.trim() : "",
            groq_api_key: elements.settingGroqKey ? elements.settingGroqKey.value.trim() : "",
            elevenlabs_api_key: elements.settingElevenKey ? elements.settingElevenKey.value.trim() : "",
            elevenlabs_voice_id: elements.settingElevenVoice ? elements.settingElevenVoice.value.trim() : "",
            tts_fallback: elements.settingTtsFallback ? elements.settingTtsFallback.checked : true,
            kb_path: elements.settingKbPath ? elements.settingKbPath.value.trim() : "",
        };

        if (elements.saveSettingsBtn) {
            elements.saveSettingsBtn.disabled = true;
        }

        try {
            const res = await state.bridge.save_settings(payload);
            if (res && res.ok) {
                showSettingsStatus("Configuration saved and applied!", false);
                if (res.settings && res.settings.app_name) {
                    state.botName = res.settings.app_name;
                    renderAll();
                }
            } else {
                showSettingsStatus("Error saving: " + (res.message || "Unknown error"), true);
            }
        } catch (err) {
            showSettingsStatus("Save error: " + (err.message || err), true);
        } finally {
            if (elements.saveSettingsBtn) {
                elements.saveSettingsBtn.disabled = false;
            }
        }
    }

    function showSettingsStatus(msg, isError) {
        if (!elements.settingsStatusMsg) return;
        elements.settingsStatusMsg.textContent = msg;
        elements.settingsStatusMsg.classList.toggle("is-error", isError);
        elements.settingsStatusMsg.hidden = false;

        window.clearTimeout(state.settingsStatusTimer);
        state.settingsStatusTimer = window.setTimeout(() => {
            if (elements.settingsStatusMsg) {
                elements.settingsStatusMsg.hidden = true;
            }
        }, 4000);
    }

    // ─── State & UI Sync ─────────────────────────────────────────────────────

    function applyBackendState(payload) {
        if (!payload || typeof payload !== "object") {
            return;
        }

        const wasSpeaking = state.speakingActive;

        if (typeof payload.bot_name === "string" && payload.bot_name.trim()) {
            state.botName = payload.bot_name.trim();
        }
        if (payload.status && typeof payload.status === "object") {
            state.status = payload.status;
        }
        if (Array.isArray(payload.activity)) {
            state.activity = payload.activity;
        }
        if (typeof payload.mic_active !== "undefined") {
            state.micActive = Boolean(payload.mic_active);
        }
        if (typeof payload.auto_listen_enabled !== "undefined") {
            state.autoListenEnabled = Boolean(payload.auto_listen_enabled);
        }
        if (typeof payload.speaking_active !== "undefined") {
            state.speakingActive = Boolean(payload.speaking_active);
        }

        if (!wasSpeaking && state.speakingActive && state.orb && typeof state.orb.playSpeechPattern === "function") {
            state.orb.playSpeechPattern(getLatestSpokenText());
        }

        // Handle Situational Interactive Modals
        if (payload.active_modal && payload.active_modal.type === "deadline") {
            const modalData = payload.active_modal.data || {};
            const isNewModal = !state.activeModal || (state.activeModal.data && state.activeModal.data.id !== modalData.id);

            if (isNewModal) {
                state.activeModal = payload.active_modal;
                if (elements.modalTitleInput) elements.modalTitleInput.value = modalData.title || "";
                if (elements.modalDateInput) elements.modalDateInput.value = modalData.due_date || "";
                if (elements.modalTimeInput) elements.modalTimeInput.value = modalData.due_time || "23:59";

                // Category pill selection
                const targetCat = modalData.category || "School";
                if (elements.categoryPills) {
                    elements.categoryPills.forEach((p) => {
                        p.classList.toggle("active", p.dataset.category === targetCat);
                    });
                }

                // Priority radio selection
                const targetPriority = modalData.priority || "Normal";
                if (elements.priorityRadios) {
                    elements.priorityRadios.forEach((r) => {
                        r.checked = (r.value === targetPriority);
                    });
                }

                if (elements.modalOverlay) {
                    elements.modalOverlay.hidden = false;
                    window.setTimeout(() => {
                        if (elements.modalTitleInput) elements.modalTitleInput.focus();
                    }, 120);
                }
            }
        } else if (!payload.active_modal && state.activeModal) {
            state.activeModal = null;
            if (elements.modalOverlay) {
                elements.modalOverlay.hidden = true;
            }
        }
    }

    // ─── Modal Actions ────────────────────────────────────────────────────────

    async function handleSaveDeadlineModal() {
        if (!state.bridge || typeof state.bridge.save_deadline !== "function") {
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            return;
        }

        const activePill = elements.categoryPills ? elements.categoryPills.find((p) => p.classList.contains("active")) : null;
        const category = activePill ? activePill.dataset.category : "School";

        const selectedPriority = elements.priorityRadios ? (elements.priorityRadios.find((r) => r.checked)?.value || "Normal") : "Normal";

        const payload = {
            title: elements.modalTitleInput ? elements.modalTitleInput.value.trim() : "New Task",
            category: category,
            due_date: elements.modalDateInput ? elements.modalDateInput.value.trim() : "",
            due_time: elements.modalTimeInput ? elements.modalTimeInput.value.trim() : "23:59",
            priority: selectedPriority,
        };

        if (elements.modalSaveBtn) {
            elements.modalSaveBtn.disabled = true;
        }

        try {
            const res = await state.bridge.save_deadline(payload);
            applyBackendState(res);
            if (elements.modalOverlay) {
                elements.modalOverlay.hidden = true;
            }
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Save deadline error:", err);
        } finally {
            if (elements.modalSaveBtn) {
                elements.modalSaveBtn.disabled = false;
            }
        }
    }

    async function handleDismissModal() {
        if (elements.modalOverlay) {
            elements.modalOverlay.hidden = true;
        }
        state.activeModal = null;
        if (state.bridge && typeof state.bridge.dismiss_modal === "function") {
            try {
                const res = await state.bridge.dismiss_modal();
                applyBackendState(res);
                renderAll();
            } catch (err) {
                console.error("[Modal] Dismiss error:", err);
            }
        }
    }

    function togglePanel(panelId) {
        if (state.openPanelId === panelId) {
            closeAllPanels();
            return;
        }

        openPanel(panelId);
    }

    function openPanel(panelId) {
        state.openPanelId = panelId;

        getPanels().forEach((panel) => {
            const isOpen = panel.id === panelId;
            panel.hidden = !isOpen;
            panel.classList.toggle("is-open", isOpen);
        });

        elements.sceneBackdrop.hidden = !panelId;

        elements.toggleButtons.forEach((button) => {
            const isActive = button.dataset.panelTarget === panelId;
            button.classList.toggle("is-active", isActive);
            button.setAttribute("aria-expanded", String(isActive));
        });

        if (panelId === "command-panel") {
            window.setTimeout(() => {
                if (elements.commandInput) elements.commandInput.focus();
            }, 120);
        }

        if (panelId === "settings-panel") {
            loadSettings();
        }
    }

    function closeAllPanels() {
        state.openPanelId = null;
        getPanels().forEach((panel) => {
            panel.hidden = true;
            panel.classList.remove("is-open");
        });
        elements.sceneBackdrop.hidden = true;
        elements.toggleButtons.forEach((button) => {
            button.classList.remove("is-active");
            button.setAttribute("aria-expanded", "false");
        });
    }

    function getPanels() {
        return [
            elements.statusPanel,
            elements.commandPanel,
            elements.activityPanel,
            elements.settingsPanel
        ].filter(Boolean);
    }

    function renderAll() {
        document.title = `${state.botName} Desktop UI`;
        if (elements.brandTitle) {
            elements.brandTitle.textContent = state.botName;
        }
        renderStatus();
        renderActivity();
        renderMicState();
        syncControlState();
    }

    function renderStatus() {
        elements.statusPill.dataset.state = state.status.state;
        elements.statusPill.dataset.speaking = String(state.speakingActive);
        elements.statusLabel.textContent = state.status.label;
        elements.statusMode.textContent = state.speakingActive ? "Speaking" : titleCase(state.status.state);
        elements.orbCaptionValue.textContent = state.speakingActive ? "Speaking" : titleCase(state.status.state);
        if (state.orb && typeof state.orb.setState === "function") {
            state.orb.setState(state.status.state);
        }
        if (state.orb && typeof state.orb.setSpeaking === "function") {
            state.orb.setSpeaking(state.speakingActive);
        }
    }

    function renderActivity() {
        elements.activityList.innerHTML = "";

        if (!state.activity.length) {
            const emptyItem = document.createElement("li");
            emptyItem.className = "activity-empty";
            emptyItem.textContent = "No recent activity yet.";
            elements.activityList.appendChild(emptyItem);
            elements.activityCount.textContent = "0";
            return;
        }

        state.activity.forEach((item) => {
            const listItem = document.createElement("li");
            listItem.className = "activity-item";
            listItem.dataset.type = item.type || "system";

            const meta = document.createElement("div");
            meta.className = "activity-meta";

            const kind = document.createElement("span");
            kind.textContent = titleCase(item.type || "system");

            const time = document.createElement("span");
            time.textContent = item.timestamp || nowTimestamp();

            meta.appendChild(kind);
            meta.appendChild(time);

            const text = document.createElement("p");
            text.className = "activity-text";
            text.textContent = item.text || "";

            listItem.appendChild(meta);
            listItem.appendChild(text);
            elements.activityList.appendChild(listItem);
        });

        elements.activityCount.textContent = String(state.activity.length);
        elements.activityScrollWrap.scrollTop = elements.activityScrollWrap.scrollHeight;
    }

    function renderMicState() {
        const voiceStandbyActive = state.autoListenEnabled || state.micActive;
        elements.micButton.classList.toggle("is-active", voiceStandbyActive);
        elements.micButton.setAttribute("aria-pressed", String(voiceStandbyActive));
        elements.micButton.setAttribute(
            "aria-label",
            voiceStandbyActive ? "Pause voice standby" : "Resume voice standby"
        );
        elements.micButton.title = voiceStandbyActive ? "Pause voice standby" : "Resume voice standby";
    }

    function syncControlState() {
        elements.sendButton.disabled = state.commandBusy;
        elements.commandInput.disabled = state.commandBusy;
        elements.micButton.disabled = false;
    }

    function getLatestSpokenText() {
        const latestItem = [...state.activity].reverse().find((item) => {
            const itemType = String(item.type || "").toLowerCase();
            return itemType === "assistant" || itemType === "system";
        });
        return latestItem ? String(latestItem.text || "") : String(state.status.label || "");
    }

    function titleCase(value) {
        const text = String(value || "");
        return text.charAt(0).toUpperCase() + text.slice(1);
    }

    function nowTimestamp() {
        return new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
    }
})();
