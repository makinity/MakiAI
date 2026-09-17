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

        // Situational Interactive Modal elements
        elements.modalOverlay = document.getElementById("interactive-modal-overlay");
        elements.modalHeading = document.getElementById("modal-heading");
        elements.modalKicker = document.getElementById("modal-kicker");
        elements.modalHeaderIconWrap = document.getElementById("modal-header-icon-wrap");
        elements.modalCloseBtn = document.getElementById("modal-close-btn");
        elements.modalCancelBtns = Array.from(document.querySelectorAll(".modal-btn-cancel"));

        // Forms
        elements.modalFormDeadline = document.getElementById("modal-form-deadline");
        elements.modalFormReminder = document.getElementById("modal-form-reminder");
        elements.modalFormHomework = document.getElementById("modal-form-homework");
        elements.modalFormProject = document.getElementById("modal-form-project");
        elements.modalFormEmail = document.getElementById("modal-form-email");
        elements.modalFormClip = document.getElementById("modal-form-clip");

        // Deadline inputs
        elements.modalDeadlineSaveBtn = document.getElementById("modal-deadline-save-btn");
        elements.modalDeadlineTitle = document.getElementById("modal-deadline-title");
        elements.modalDeadlineDate = document.getElementById("modal-deadline-date");
        elements.modalDeadlineTime = document.getElementById("modal-deadline-time");
        elements.deadlineCategoryPills = Array.from(document.querySelectorAll("#deadline-category-pills .category-pill"));
        elements.deadlinePriorityRadios = Array.from(document.querySelectorAll("input[name='deadline-priority']"));

        // Reminder inputs
        elements.modalReminderSaveBtn = document.getElementById("modal-reminder-save-btn");
        elements.modalReminderText = document.getElementById("modal-reminder-text");
        elements.modalReminderDate = document.getElementById("modal-reminder-date");
        elements.modalReminderTime = document.getElementById("modal-reminder-time");
        elements.reminderCategoryPills = Array.from(document.querySelectorAll("#reminder-category-pills .category-pill"));
        elements.reminderQuickChips = Array.from(document.querySelectorAll(".quick-chip"));

        // Homework inputs
        elements.modalHomeworkGenBtn = document.getElementById("modal-homework-gen-btn");
        elements.modalHomeworkTitle = document.getElementById("modal-homework-title");
        elements.modalHomeworkInstructions = document.getElementById("modal-homework-instructions");
        elements.modalHomeworkPath = document.getElementById("modal-homework-path");
        elements.homeworkFormatPills = Array.from(document.querySelectorAll("#homework-format-pills .category-pill"));

        // Project inputs
        elements.modalProjectScaffoldBtn = document.getElementById("modal-project-scaffold-btn");
        elements.modalProjectName = document.getElementById("modal-project-name");
        elements.modalProjectVision = document.getElementById("modal-project-vision");
        elements.modalProjectPath = document.getElementById("modal-project-path");
        elements.projectStackPills = Array.from(document.querySelectorAll("#project-stack-pills .category-pill"));

        // Email inputs
        elements.modalEmailSendBtn = document.getElementById("modal-email-send-btn");
        elements.modalEmailTo = document.getElementById("modal-email-to");
        elements.modalEmailSubject = document.getElementById("modal-email-subject");
        elements.modalEmailBody = document.getElementById("modal-email-body");

        // Clip inputs
        elements.modalClipRenderBtn = document.getElementById("modal-clip-render-btn");
        elements.modalClipSource = document.getElementById("modal-clip-source");
        elements.modalClipStart = document.getElementById("modal-clip-start");
        elements.modalClipEnd = document.getElementById("modal-clip-end");
        elements.modalClipTitle = document.getElementById("modal-clip-title");
        elements.clipFormatPills = Array.from(document.querySelectorAll("#clip-format-pills .category-pill"));

        // Interview & Routine inputs
        elements.modalFormInterview = document.getElementById("modal-form-interview");
        elements.modalInterviewSaveBtn = document.getElementById("modal-interview-save-btn");
        elements.modalInterviewTitle = document.getElementById("modal-interview-title");
        elements.modalInterviewDate = document.getElementById("modal-interview-date");
        elements.modalInterviewTime = document.getElementById("modal-interview-time");
        elements.modalInterviewLink = document.getElementById("modal-interview-link");
        elements.modalInterviewProfile = document.getElementById("modal-interview-profile");
        elements.modalInterviewLeadTime = document.getElementById("modal-interview-lead-time");
        elements.interviewCategoryPills = Array.from(document.querySelectorAll("#interview-category-pills .category-pill"));
        elements.interviewPlatformPills = Array.from(document.querySelectorAll("#interview-platform-pills .category-pill"));

        // Job Hunting Niche Picker
        elements.modalFormJobNiche = document.getElementById("modal-form-job-niche");
        elements.jobNicheBtns = Array.from(document.querySelectorAll(".job-niche-btn"));
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

        // Generic Category / Format / Stack Pill bindings
        document.querySelectorAll(".category-pills").forEach((group) => {
            group.querySelectorAll(".category-pill").forEach((pill) => {
                pill.addEventListener("click", () => {
                    group.querySelectorAll(".category-pill").forEach((p) => p.classList.remove("active"));
                    pill.classList.add("active");
                });
            });
        });

        // Quick Preset Chips for Reminders
        if (elements.reminderQuickChips) {
            elements.reminderQuickChips.forEach((chip) => {
                chip.addEventListener("click", () => {
                    const offset = chip.dataset.offset;
                    applyReminderQuickPreset(offset);
                });
            });
        }

        // Modal Action & Dismiss Handlers
        if (elements.modalCloseBtn) {
            elements.modalCloseBtn.addEventListener("click", handleDismissModal);
        }
        if (elements.modalCancelBtns) {
            elements.modalCancelBtns.forEach((btn) => btn.addEventListener("click", handleDismissModal));
        }

        // Save / Trigger Buttons for all 6 modals
        if (elements.modalDeadlineSaveBtn) {
            elements.modalDeadlineSaveBtn.addEventListener("click", handleSaveDeadlineModal);
        }
        if (elements.modalReminderSaveBtn) {
            elements.modalReminderSaveBtn.addEventListener("click", handleSaveReminderModal);
        }
        if (elements.modalHomeworkGenBtn) {
            elements.modalHomeworkGenBtn.addEventListener("click", handleGenerateHomeworkModal);
        }
        if (elements.modalProjectScaffoldBtn) {
            elements.modalProjectScaffoldBtn.addEventListener("click", handleScaffoldProjectModal);
        }
        if (elements.modalEmailSendBtn) {
            elements.modalEmailSendBtn.addEventListener("click", handleSendEmailModal);
        }
        if (elements.modalClipRenderBtn) {
            elements.modalClipRenderBtn.addEventListener("click", handleRenderClipModal);
        }
        if (elements.modalInterviewSaveBtn) {
            elements.modalInterviewSaveBtn.addEventListener("click", handleSaveInterview);
        }

        if (elements.jobNicheBtns) {
            elements.jobNicheBtns.forEach((btn) => {
                btn.addEventListener("click", () => {
                    const nicheId = btn.dataset.niche;
                    if (nicheId && state.bridge && typeof state.bridge.launch_routine === "function") {
                        state.bridge.launch_routine(nicheId);
                        handleDismissModal();
                    }
                });
            });
        }

        // Auto-change link placeholder on platform pill click
        if (elements.interviewPlatformPills) {
            elements.interviewPlatformPills.forEach((pill) => {
                pill.addEventListener("click", () => {
                    const platform = pill.dataset.platform;
                    if (elements.modalInterviewLink && !elements.modalInterviewLink.value) {
                        if (platform === "Google Meet") elements.modalInterviewLink.placeholder = "https://meet.google.com/xyz-abcd-efg";
                        else if (platform === "Zoom") elements.modalInterviewLink.placeholder = "https://zoom.us/j/123456789";
                        else if (platform === "Teams") elements.modalInterviewLink.placeholder = "https://teams.microsoft.com/l/meetup-join/...";
                        else elements.modalInterviewLink.placeholder = "https://...";
                    }
                });
            });
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
        if (payload.active_modal && payload.active_modal.type) {
            const modalType = payload.active_modal.type;
            const modalData = payload.active_modal.data || {};
            const isNewModal = !state.activeModal || (state.activeModal.data && state.activeModal.data.id !== modalData.id);

            if (isNewModal) {
                state.activeModal = payload.active_modal;
                showSituationalModal(modalType, modalData);
            }
        } else if (!payload.active_modal && state.activeModal) {
            state.activeModal = null;
            if (elements.modalOverlay) {
                elements.modalOverlay.hidden = true;
            }
        }
    }

    function showSituationalModal(type, data) {
        // Hide all forms first
        const allForms = [
            elements.modalFormDeadline,
            elements.modalFormReminder,
            elements.modalFormHomework,
            elements.modalFormProject,
            elements.modalFormEmail,
            elements.modalFormClip,
            elements.modalFormInterview,
            elements.modalFormJobNiche
        ];
        allForms.forEach((f) => { if (f) f.hidden = true; });

        if (type === "deadline") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Add / Edit Deadline";
            if (elements.modalKicker) elements.modalKicker.textContent = "Deadlines Workflow";
            if (elements.modalDeadlineTitle) elements.modalDeadlineTitle.value = data.title || "";
            if (elements.modalDeadlineDate) elements.modalDeadlineDate.value = data.due_date || "";
            if (elements.modalDeadlineTime) elements.modalDeadlineTime.value = data.due_time || "23:59";

            const targetCat = data.category || "School";
            if (elements.deadlineCategoryPills) {
                elements.deadlineCategoryPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.category === targetCat);
                });
            }
            const targetPriority = data.priority || "Normal";
            if (elements.deadlinePriorityRadios) {
                elements.deadlinePriorityRadios.forEach((r) => {
                    r.checked = (r.value === targetPriority);
                });
            }
            if (elements.modalFormDeadline) elements.modalFormDeadline.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalDeadlineTitle && elements.modalDeadlineTitle.focus(), 120);

        } else if (type === "reminder") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Set Reminder / Schedule";
            if (elements.modalKicker) elements.modalKicker.textContent = "Voice Reminders";
            if (elements.modalReminderText) elements.modalReminderText.value = data.title || data.text || "";
            if (elements.modalReminderDate) elements.modalReminderDate.value = data.target_date || data.due_date || getTodayDateStr();
            if (elements.modalReminderTime) elements.modalReminderTime.value = data.target_time || data.due_time || "12:00";

            const targetCat = data.category || "Task";
            if (elements.reminderCategoryPills) {
                elements.reminderCategoryPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.category === targetCat);
                });
            }
            if (elements.modalFormReminder) elements.modalFormReminder.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalReminderText && elements.modalReminderText.focus(), 120);

        } else if (type === "homework") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Generate Academic Document";
            if (elements.modalKicker) elements.modalKicker.textContent = "Homework Engine (.docx)";
            if (elements.modalHomeworkTitle) elements.modalHomeworkTitle.value = data.subject || data.title || "";
            if (elements.modalHomeworkInstructions) elements.modalHomeworkInstructions.value = data.instructions || data.outline || "";
            if (elements.modalHomeworkPath) elements.modalHomeworkPath.value = data.output_path || "C:\\MakiSync Storage\\School";

            const targetFormat = data.format || "Standard Academic";
            if (elements.homeworkFormatPills) {
                elements.homeworkFormatPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.format === targetFormat);
                });
            }
            if (elements.modalFormHomework) elements.modalFormHomework.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalHomeworkTitle && elements.modalHomeworkTitle.focus(), 120);

        } else if (type === "new_project") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Scaffold New Project";
            if (elements.modalKicker) elements.modalKicker.textContent = "Project Architecture";
            if (elements.modalProjectName) elements.modalProjectName.value = data.name || data.title || "";
            if (elements.modalProjectVision) elements.modalProjectVision.value = data.vision || data.description || "";
            if (elements.modalProjectPath) elements.modalProjectPath.value = data.target_path || "c:\\development\\Python";

            const targetStack = data.stack || "Vite + React";
            if (elements.projectStackPills) {
                elements.projectStackPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.stack === targetStack);
                });
            }
            if (elements.modalFormProject) elements.modalFormProject.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalProjectName && elements.modalProjectName.focus(), 120);

        } else if (type === "composio_email") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Compose Email (Gmail)";
            if (elements.modalKicker) elements.modalKicker.textContent = "Cloud Workspace";
            if (elements.modalEmailTo) elements.modalEmailTo.value = data.to || "";
            if (elements.modalEmailSubject) elements.modalEmailSubject.value = data.subject || "";
            if (elements.modalEmailBody) elements.modalEmailBody.value = data.body || "";

            if (elements.modalFormEmail) elements.modalFormEmail.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalEmailTo && elements.modalEmailTo.focus(), 120);

        } else if (type === "clip") {
            if (elements.modalHeading) elements.modalHeading.textContent = "DeepClip Video Slicer";
            if (elements.modalKicker) elements.modalKicker.textContent = "Video Intelligence";
            if (elements.modalClipSource) elements.modalClipSource.value = data.source_path || "C:\\MakiSync Storage\\MakiAI\\Recordings\\latest.mp4";
            if (elements.modalClipStart) elements.modalClipStart.value = data.start_time || "00:00";
            if (elements.modalClipEnd) elements.modalClipEnd.value = data.end_time || "00:45";
            if (elements.modalClipTitle) elements.modalClipTitle.value = data.title || "Viral Clip 01";

            const targetRatio = data.ratio || "9:16";
            if (elements.clipFormatPills) {
                elements.clipFormatPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.ratio === targetRatio);
                });
            }
            if (elements.modalFormClip) elements.modalFormClip.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalClipTitle && elements.modalClipTitle.focus(), 120);

        } else if (type === "interview" || type === "routine") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Schedule Interview / Workspace Routine";
            if (elements.modalKicker) elements.modalKicker.textContent = "Proactive Workspace Engine";
            if (elements.modalInterviewTitle) elements.modalInterviewTitle.value = data.title || data.name || data.company || "";
            if (elements.modalInterviewDate) elements.modalInterviewDate.value = data.date || data.target_date || getTodayDateStr();
            if (elements.modalInterviewTime) elements.modalInterviewTime.value = data.time || data.target_time || "09:00";
            if (elements.modalInterviewLink) elements.modalInterviewLink.value = data.link || data.url || "";
            if (elements.modalInterviewProfile) elements.modalInterviewProfile.value = data.chrome_profile || "Default";
            if (elements.modalInterviewLeadTime) elements.modalInterviewLeadTime.value = String(data.lead_time_minutes || 15);

            const targetCat = data.category || "Interview";
            if (elements.interviewCategoryPills) {
                elements.interviewCategoryPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.category === targetCat);
                });
            }
            const targetPlatform = data.platform || "Google Meet";
            if (elements.interviewPlatformPills) {
                elements.interviewPlatformPills.forEach((p) => {
                    p.classList.toggle("active", p.dataset.platform === targetPlatform);
                });
            }
            if (elements.modalFormInterview) elements.modalFormInterview.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
            window.setTimeout(() => elements.modalInterviewTitle && elements.modalInterviewTitle.focus(), 120);

        } else if (type === "job_niche") {
            if (elements.modalHeading) elements.modalHeading.textContent = "Job Hunting Niche Selection";
            if (elements.modalKicker) elements.modalKicker.textContent = "Dual-Profile Workspace Provisioning";
            if (elements.modalFormJobNiche) elements.modalFormJobNiche.hidden = false;
            if (elements.modalOverlay) elements.modalOverlay.hidden = false;
        }
    }

    function applyReminderQuickPreset(offset) {
        const now = new Date();
        if (offset === "15m") {
            now.setMinutes(now.getMinutes() + 15);
        } else if (offset === "30m") {
            now.setMinutes(now.getMinutes() + 30);
        } else if (offset === "1h") {
            now.setHours(now.getHours() + 1);
        } else if (offset === "tonight") {
            now.setHours(20, 0, 0, 0);
        } else if (offset === "tomorrow") {
            now.setDate(now.getDate() + 1);
            now.setHours(9, 0, 0, 0);
        }

        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, "0");
        const dd = String(now.getDate()).padStart(2, "0");
        const hh = String(now.getHours()).padStart(2, "0");
        const min = String(now.getMinutes()).padStart(2, "0");

        if (elements.modalReminderDate) elements.modalReminderDate.value = `${yyyy}-${mm}-${dd}`;
        if (elements.modalReminderTime) elements.modalReminderTime.value = `${hh}:${min}`;
    }

    function getTodayDateStr() {
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, "0");
        const dd = String(now.getDate()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd}`;
    }

    // ─── Modal Submissions ───────────────────────────────────────────────────

    async function handleSaveDeadlineModal() {
        if (!state.bridge || typeof state.bridge.save_deadline !== "function") {
            handleDismissModal();
            return;
        }

        const activePill = elements.deadlineCategoryPills ? elements.deadlineCategoryPills.find((p) => p.classList.contains("active")) : null;
        const category = activePill ? activePill.dataset.category : "School";
        const selectedPriority = elements.deadlinePriorityRadios ? (elements.deadlinePriorityRadios.find((r) => r.checked)?.value || "Normal") : "Normal";

        const payload = {
            title: elements.modalDeadlineTitle ? elements.modalDeadlineTitle.value.trim() : "New Task",
            category: category,
            due_date: elements.modalDeadlineDate ? elements.modalDeadlineDate.value.trim() : "",
            due_time: elements.modalDeadlineTime ? elements.modalDeadlineTime.value.trim() : "23:59",
            priority: selectedPriority,
        };

        if (elements.modalDeadlineSaveBtn) elements.modalDeadlineSaveBtn.disabled = true;

        try {
            const res = await state.bridge.save_deadline(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Save deadline error:", err);
        } finally {
            if (elements.modalDeadlineSaveBtn) elements.modalDeadlineSaveBtn.disabled = false;
        }
    }

    async function handleSaveReminderModal() {
        if (!state.bridge || typeof state.bridge.save_reminder !== "function") {
            handleDismissModal();
            return;
        }

        const activePill = elements.reminderCategoryPills ? elements.reminderCategoryPills.find((p) => p.classList.contains("active")) : null;
        const category = activePill ? activePill.dataset.category : "Task";

        const payload = {
            title: elements.modalReminderText ? elements.modalReminderText.value.trim() : "Reminder",
            category: category,
            target_date: elements.modalReminderDate ? elements.modalReminderDate.value.trim() : "",
            target_time: elements.modalReminderTime ? elements.modalReminderTime.value.trim() : "12:00",
        };

        if (elements.modalReminderSaveBtn) elements.modalReminderSaveBtn.disabled = true;

        try {
            const res = await state.bridge.save_reminder(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Save reminder error:", err);
        } finally {
            if (elements.modalReminderSaveBtn) elements.modalReminderSaveBtn.disabled = false;
        }
    }

    async function handleGenerateHomeworkModal() {
        if (!state.bridge || typeof state.bridge.generate_homework !== "function") {
            handleDismissModal();
            return;
        }

        const activePill = elements.homeworkFormatPills ? elements.homeworkFormatPills.find((p) => p.classList.contains("active")) : null;
        const format = activePill ? activePill.dataset.format : "Standard Academic";

        const payload = {
            subject: elements.modalHomeworkTitle ? elements.modalHomeworkTitle.value.trim() : "Assignment",
            instructions: elements.modalHomeworkInstructions ? elements.modalHomeworkInstructions.value.trim() : "",
            format: format,
            output_path: elements.modalHomeworkPath ? elements.modalHomeworkPath.value.trim() : "C:\\MakiSync Storage\\School",
        };

        if (elements.modalHomeworkGenBtn) elements.modalHomeworkGenBtn.disabled = true;

        try {
            const res = await state.bridge.generate_homework(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Homework gen error:", err);
        } finally {
            if (elements.modalHomeworkGenBtn) elements.modalHomeworkGenBtn.disabled = false;
        }
    }

    async function handleScaffoldProjectModal() {
        if (!state.bridge || typeof state.bridge.scaffold_project !== "function") {
            handleDismissModal();
            return;
        }

        const activePill = elements.projectStackPills ? elements.projectStackPills.find((p) => p.classList.contains("active")) : null;
        const stack = activePill ? activePill.dataset.stack : "Vite + React";

        const payload = {
            name: elements.modalProjectName ? elements.modalProjectName.value.trim() : "NewProject",
            vision: elements.modalProjectVision ? elements.modalProjectVision.value.trim() : "",
            stack: stack,
            target_path: elements.modalProjectPath ? elements.modalProjectPath.value.trim() : "c:\\development\\Python",
        };

        if (elements.modalProjectScaffoldBtn) elements.modalProjectScaffoldBtn.disabled = true;

        try {
            const res = await state.bridge.scaffold_project(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Project scaffold error:", err);
        } finally {
            if (elements.modalProjectScaffoldBtn) elements.modalProjectScaffoldBtn.disabled = false;
        }
    }

    async function handleSendEmailModal() {
        if (!state.bridge || typeof state.bridge.send_email !== "function") {
            handleDismissModal();
            return;
        }

        const payload = {
            to: elements.modalEmailTo ? elements.modalEmailTo.value.trim() : "",
            subject: elements.modalEmailSubject ? elements.modalEmailSubject.value.trim() : "No Subject",
            body: elements.modalEmailBody ? elements.modalEmailBody.value.trim() : "",
        };

        if (elements.modalEmailSendBtn) elements.modalEmailSendBtn.disabled = true;

        try {
            const res = await state.bridge.send_email(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Send email error:", err);
        } finally {
            if (elements.modalEmailSendBtn) elements.modalEmailSendBtn.disabled = false;
        }
    }

    async function handleRenderClipModal() {
        if (!state.bridge || typeof state.bridge.render_clip !== "function") {
            handleDismissModal();
            return;
        }

        const activePill = elements.clipFormatPills ? elements.clipFormatPills.find((p) => p.classList.contains("active")) : null;
        const ratio = activePill ? activePill.dataset.ratio : "9:16";

        const payload = {
            source_path: elements.modalClipSource ? elements.modalClipSource.value.trim() : "",
            start_time: elements.modalClipStart ? elements.modalClipStart.value.trim() : "00:00",
            end_time: elements.modalClipEnd ? elements.modalClipEnd.value.trim() : "00:45",
            title: elements.modalClipTitle ? elements.modalClipTitle.value.trim() : "Highlight Clip",
            ratio: ratio,
        };

        if (elements.modalClipRenderBtn) elements.modalClipRenderBtn.disabled = true;

        try {
            const res = await state.bridge.render_clip(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Render clip error:", err);
        } finally {
            if (elements.modalClipRenderBtn) elements.modalClipRenderBtn.disabled = false;
        }
    }

    async function handleSaveInterview() {
        if (!state.bridge || typeof state.bridge.save_routine !== "function") {
            handleDismissModal();
            return;
        }

        const activeCatPill = elements.interviewCategoryPills ? elements.interviewCategoryPills.find((p) => p.classList.contains("active")) : null;
        const category = activeCatPill ? activeCatPill.dataset.category : "Interview";

        const activePlatPill = elements.interviewPlatformPills ? elements.interviewPlatformPills.find((p) => p.classList.contains("active")) : null;
        const platform = activePlatPill ? activePlatPill.dataset.platform : "Google Meet";

        const payload = {
            title: elements.modalInterviewTitle ? elements.modalInterviewTitle.value.trim() : "Scheduled Session",
            category: category,
            date: elements.modalInterviewDate ? elements.modalInterviewDate.value.trim() : "",
            time: elements.modalInterviewTime ? elements.modalInterviewTime.value.trim() : "09:00",
            platform: platform,
            link: elements.modalInterviewLink ? elements.modalInterviewLink.value.trim() : "",
            chrome_profile: elements.modalInterviewProfile ? elements.modalInterviewProfile.value : "Default",
            lead_time_minutes: elements.modalInterviewLeadTime ? parseInt(elements.modalInterviewLeadTime.value) : 15,
        };

        if (elements.modalInterviewSaveBtn) elements.modalInterviewSaveBtn.disabled = true;

        try {
            const res = await state.bridge.save_routine(payload);
            applyBackendState(res);
            if (elements.modalOverlay) elements.modalOverlay.hidden = true;
            state.activeModal = null;
            renderAll();
        } catch (err) {
            console.error("[Modal] Save interview error:", err);
        } finally {
            if (elements.modalInterviewSaveBtn) elements.modalInterviewSaveBtn.disabled = false;
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

    let lastRenderedActivitySig = "";

    function renderActivity() {
        const currentCount = state.activity.length;
        const lastItem = currentCount > 0 ? state.activity[currentCount - 1] : null;
        const currentSignature = currentCount + "_" + (lastItem ? ((lastItem.timestamp || "") + (lastItem.text || "")) : "");

        if (currentSignature === lastRenderedActivitySig) {
            return; // State unchanged — preserve scroll position
        }

        const wrap = elements.activityScrollWrap;
        const isNearBottom = !wrap || (wrap.scrollHeight - wrap.scrollTop - wrap.clientHeight <= 140);
        const isInitial = !lastRenderedActivitySig;

        lastRenderedActivitySig = currentSignature;
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

        if (wrap && (isNearBottom || isInitial)) {
            requestAnimationFrame(() => {
                wrap.scrollTop = wrap.scrollHeight;
            });
        }
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
