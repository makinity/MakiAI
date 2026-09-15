# 🛠️ MakiAI — Developer & AI Agent Tooling Collection (`gitdev.md`)

This document tracks developer frameworks, coding agent harnesses, context optimizers, and CLI tools for software engineering. These tools empower AI coding assistants (Antigravity, Claude Code, Cursor, Codex, Gemini CLI) and serve as delegation targets when MakiAI directs coding and technical tasks.

---

## 🏗️ 1. AI Engineering Harness & Multi-Agent Framework
* **Repository:** [affaan-m/ECC](https://github.com/affaan-m/ECC) *(Engineering Command Center)*
* **Role in Dev Stack:** **Agentic Engineering Operating System & Toolbox**
* **Capability:**
  * **68 Specialized Subagents:** Architecture planning, security review, build repair, database design, and TDD execution.
  * **292 Domain Skills:** Pre-configured procedures for Frontend, Backend, ML, DevOps, Docker, and API design.
  * **AgentShield:** Pre-flight security scanning for malicious prompts, leaked secrets, and unsafe tool configurations.
  * **Engineering Lifecycle:** Enforces a structured engineering loop: `plan -> test -> implement -> review -> verify -> remember -> improve`.
* **Integration Target:** Primary harness for Claude Code, Antigravity, and Codex IDE pair-programming.

---

## ⚡ 2. Token Context Optimizer & Session Continuity
* **Repository:** [mksglu/context-mode](https://github.com/mksglu/context-mode) *(#1 on Hacker News)*
* **Role in Dev Stack:** **MCP Context Compression & Memory Optimizer**
* **Capability:**
  * **"Think in Code" Execution:** Replaces raw file dumps (700 KB) with sandboxed execution (`ctx_execute`), shrinking context overhead by up to 98% (down to 3.6 KB).
  * **Local SQLite FTS5 Indexing:** Caches large tool outputs, git logs, and issue threads to local disk with BM25 keyword search.
  * **Session Compaction Protection:** Prevents agent amnesia across long multi-hour coding sessions by preserving task history outside the LLM context window.
* **Integration Target:** Model Context Protocol (MCP) server for IDE agents (Antigravity, Claude Code, Cursor, VS Code).

---

## 🎯 3. Action-First Output Enforcement
* **Repository:** [ayghri/i-have-adhd](https://github.com/ayghri/i-have-adhd)
* **Role in Dev Stack:** **Concise & Direct Agent Behavior Rules**
* **Capability:**
  * Eliminates AI filler, unnecessary pleasantries, and multi-paragraph preambles.
  * Forces coding agents to lead with the solution, action steps, and runnable code immediately.
* **Integration Target:** IDE agent behavioral rules (`AGENTS.md` / `rules.md`).

---

## 💻 4. Local Autonomous Coding CLI & Delegation
* **Engine:** **Kiro CLI (`services/coding/kiro_service.py`)**
* **Role in MakiAI:** **Desktop Autonomous Developer Agent**
* **Capability:**
  * MakiAI delegates complex coding features, bugfixes, and multi-file code generation directly to the local Kiro CLI.
  * Voice commands like *"Maki, use Kiro to build the authentication system"* trigger background coding workflows while Maki continues monitoring desktop tasks.
* **Integration Target:** Native subprocess bridge inside MakiAI orchestrator.

---

## 🔄 5. Self-Hosted Workflow & Integration Generation (MCP)
* **Repository:** [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) *(n8n Model Context Protocol Server)*
* **Role in Dev Stack:** **Zero-Hallucination n8n Workflow Builder & Node Knowledge Base**
* **Capability:**
  * **2,700+ Node Schema Knowledge:** Provides AI coding assistants with complete documentation, parameter schemas, input/output types, and operations across all core and community n8n nodes.
  * **Instant Workflow JSON Synthesis:** Enables coding agents to generate valid, copy-paste-ready n8n workflow JSONs without hallucinated properties or broken wire connections.
  * **Backend Automation Delegation:** Allows MakiAI and IDE agents to architect complex multi-app automations (CRMs, webhooks, Notion, Google Workspace, Stripe, Telegram) through self-hosted n8n workflows rather than hardcoding complex REST boilerplate in Python.
* **Integration Target:** MCP Server (`docker run -i --rm -e MCP_MODE=stdio ghcr.io/czlonkowski/n8n-mcp:latest`) for Antigravity, Claude Code, Cursor, and Windsurf.

---

