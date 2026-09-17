# 🤖 AI Collaboration Guide: Gemini + Claude

This guide explains how to use the **Double Agent** workflow to maximize efficiency and minimize errors.

## The Team
1.  **Gemini (The Architect & Reviewer)** 🧠
    *   **Role**: Analyzes the codebase, plans the architecture, checks for errors.
    *   **Tools**: `architectural_analysis`, `code_review`.
    *   **Strength**: Huge context window, understands the "Big Picture".

2.  **Claude (The Coder)** 💻
    *   **Role**: Writes the actual code based on Gemini's specs.
    *   **Strength**: Logic, complex algorithms, clean code.

---

## 🔄 The Workflow Cycle

### Phase 1: Planning (Gemini)
1.  Tell Gemini what you want to do:
    *   _"I want to add a new Loan module."_
2.  Gemini uses the `/architectural_analysis` workflow.
3.  Gemini produces a **Spec** and a **File List**.

### Phase 2: Context Handoff
1.  Gemini identifies the files needed, e.g., `src/db/models.py`, `src/ui/main.py`.
2.  Run the helper script to grab these files:
    ```powershell
    python scripts/prepare_context.py src/db/models.py src/ui/main.py
    ```
3.  The script copies the file contents to your clipboard.

### Phase 3: Coding (Claude)
1.  Go to Claude.
2.  Paste the **Spec** (from Gemini) and the **Context** (from the script).
3.  Ask Claude to write the code.
4.  Copy Claude's solution.

### Phase 4: Review (Gemini)
1.  Come back to Gemini.
2.  Paste Claude's code.
3.  Run the `/code_review` workflow (or just ask "Review this").
4.  Gemini checks for:
    *   Compatibility with other files.
    *   Security issues.
    *   Style consistency.

### Phase 5: Apply & Verify
1.  If the review is good, apply the changes.
2.  Run tests/verify manually.

---

## 🛠️ Helper Tools

### `scripts/prepare_context.py`
Usage:
```bash
python scripts/prepare_context.py <file_path_1> <file_path_2> ...
```
Examples:
*   `python scripts/prepare_context.py src/main.py`
*   `python scripts/prepare_context.py src/ui/*.py` (if shell supports expansion)
