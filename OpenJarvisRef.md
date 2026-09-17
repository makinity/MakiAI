# OpenJarvis Reference & Architecture Guide for MakiAI

This document outlines high-value patterns, architectural concepts, and capabilities analyzed from the [OpenJarvis](https://github.com/open-jarvis/OpenJarvis) framework that can be referenced and adapted into **MakiAI** to elevate intelligence, autonomy, and robustness while avoiding common pitfalls.

*(Note: Local engine/offline runtimes like Ollama/llama.cpp are deliberately omitted per project preference, keeping MakiAI powered by high-speed Cloud LLMs like Gemini, Groq, and OpenAI).*

---

## 1. Executive Summary & Comparison

| Capability | OpenJarvis Pattern | MakiAI Status | Enhancement Opportunity |
| :--- | :--- | :--- | :--- |
| **PC & OS Control** | Generic shell/CLI tools | **Deep Windows integration** (multi-monitor, explorer, audio, camera) | Maintain MakiAI's sub-10ms deterministic edge |
| **Long-Term Memory** | Automatic background fact extraction into SQLite/JSONL | Knowledge Base docs + session memory | **Implement auto-fact extraction from daily chat** |
| **Tool Extensibility** | Native **MCP (Model Context Protocol)** client | Custom Python skill scripts | **Add MCP client adapter for off-the-shelf tools** |
| **Skill Management** | Auto-discovery catalog with hot-reloading | Static router imports | **Dynamic `skills/` loader without restarts** |
| **Error Handling** | Execution trace logging & prompt adjustment | Manual debugging & exception try/catches | **Self-healing failure trace loop** |
| **Action Safety** | Risk classification (Safe / Caution / Dangerous) | Direct execution | **Add confirmation barriers for destructive ops** |

---

## 2. Key Abilities to Adapt into MakiAI

### A. Continuous Durable Fact & Preference Extraction (Auto Long-Term Memory)
* **OpenJarvis Mechanism:** In the background, an async memory observer parses chat turns and extracts durable personal facts into a structured store (`memory_facts.jsonl` + SQLite):
  - *"User's preferred editor is VS Code."*
  - *"User's primary email recipient is markjuntillava@gmail.com."*
  - *"User works on Python and React projects in `c:\development`."*
* **How to Adapt for MakiAI:**
  1. Create a lightweight `FactExtractor` daemon that runs asynchronously after conversations.
  2. Maintain a structured SQLite table `user_facts` with categories (`preference`, `contact`, `project`, `routine`, `hardware`).
  3. Automatically inject relevant top-k facts into the AI prompt context so MakiAI naturally remembers user habits without explicit *"remember this"* commands.

---

### B. Native MCP (Model Context Protocol) Integration
* **OpenJarvis Mechanism:** Implements a standard MCP client that can dynamically connect to any MCP server (e.g., GitHub, SQLite, PostgreSQL, Notion, Slack, Google Drive, Filesystem, Brave Search).
* **How to Adapt for MakiAI:**
  1. Add an `MCPClientService` inside `services/mcp/`.
  2. Allow configuration in `.env` or `mcp_config.json` to attach standard MCP servers.
  3. MakiAI immediately gains access to hundreds of pre-built community integrations without having to write and maintain custom API adapters for each service.

---

### C. Dynamic Skill Catalog & Hot-Reloading (`skills/` Auto-Discovery)
* **What OpenJarvis Has:** A skill registry that scans a `skills/` directory and registers tools dynamically at startup or on file change.
* **How to Adapt for MakiAI:**
  1. Build a `SkillRegistry` that scans `skills/*.py` looking for standardized skill classes inheriting from a base `BaseSkill`.
  2. When a new skill file is added or edited, MakiAI hot-reloads it without requiring a full application restart.
  3. Enables clean modularity where individual features (e.g. Spotify, Notion, School Timetable, Discord) live in self-contained skill packages.

---

### D. Self-Correction & Execution Trace Logging (Feedback Loop)
* **What OpenJarvis Has:** Logs execution traces of failed tool calls (e.g., failed API calls, missing parameters, incorrect path assumptions) and matches them to suggest automatic prompt/routing refinements.
* **How to Adapt for MakiAI:**
  1. In `ComposioSkill`, `FileManager`, and `ComputerRouter`, log failed tool invocations to `data/logs/execution_traces.jsonl`.
  2. Implement automatic retry with error feedback: if a tool call fails, MakiAI feeds the exact error trace back into the reasoning prompt for instant self-correction on the next turn.

---

### E. Tool Risk Classification & Safety Guardrails
* **What OpenJarvis Has:** Classifies tools into risk tiers:
  - **Level 1 (Read-only / Safe):** File reading, window listing, time checks, searches (executed instantly).
  - **Level 2 (State Modifications):** Creating files, opening tabs, moving windows, sending emails to known contacts (executed with natural spoken confirmation).
  - **Level 3 (High-Risk / Destructive):** File deletion, mass emailing, running raw shell scripts, system shutdown (requires explicit user verbal/text confirmation barrier).
* **How to Adapt for MakiAI:**
  - Standardize all router actions under these 3 tiers to protect system integrity while maintaining maximum speed for everyday commands.

---

### F. Multi-Tier Agent Execution Lifecycles
* **What OpenJarvis Has:** Decouples agents into three distinct modes:
  1. **On-Demand:** Voice/text reactive commands (sub-second responses).
  2. **Scheduled:** Cron-like routines (morning briefings, daily storage cleanups).
  3. **Continuous Monitors:** Background operatives with memory compression (e.g., monitoring urgent email alerts, tracking hardware temperatures, or watchdogs for completed downloads).
* **How to Adapt for MakiAI:**
  - Standardize MakiAI background threads (`SystemHealth`, `EmailWatcher`, `MakiSync`) under a unified `OperativeWorker` lifecycle manager with health checks, crash-recovery, and clean shutdown hooks.

---

## 3. MakiAI Core Advantages to Maintain & Protect

While borrowing the high-level agentic patterns from OpenJarvis, MakiAI must strictly maintain its existing competitive strengths:

1. **Deterministic Sub-10ms Fast Routing:** Never replace deterministic PC control with slow LLM reasoning loops. Keep the frontline regex/in-memory router for instantaneous system reactions.
2. **Deep Native Windows Integration:** Continue prioritizing rich Windows APIs (pywin32, ctypes, File Explorer `/select`, multi-monitor topology, audio endpoints).
3. **Cloud Intelligence Speed:** Rely on ultra-low latency cloud models (Gemini Flash, Groq) for conversational intelligence rather than heavy local model inference.

---

## 4. Implementation Priority Matrix

| Priority | Feature | Complexity | Impact |
| :---: | :--- | :---: | :---: |
| **P1** | **Continuous Durable Fact Extraction (Auto-Memory)** | Medium | 🌟 High (Instant Personalization) |
| **P2** | **Dynamic Skill Registry & Hot-Reloading** | Low | ⚡ High (Modular Architecture) |
| **P3** | **Execution Trace Logging & Self-Correction** | Medium | 🛡️ High (Crash Prevention & Resiliency) |
| **P4** | **Native MCP Client Adapter** | Medium | 🚀 High (Massive Tool Ecosystem) |
| **P5** | **Tool Risk Classification & Safety Guardrails** | Low | 🔒 Medium (System Safety) |
