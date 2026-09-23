# AI Model Routing Rule

This rule applies to coding work in AYEC Pro.

1. Start implementation with Luna.
2. Run the focused test or verification immediately after the change.
3. If a test fails, send the failure and the smallest relevant context back to Luna for a fix.
4. If Luna cannot resolve the same failure after a focused retry, escalate the task with the evidence to Sol or Astra.
5. Keep the escalation focused: include the failing test, traceback, changed files, and the attempted fix.
6. Do not claim completion until the relevant tests and source quality checks pass.

Automatic routing note: the repository cannot change the active Codex model by itself. The Codex task runner must apply the routing rule when a new user message starts coding work. Until that runner is connected, the assistant follows this rule explicitly in the current task.

Inspection-only mode requested by the owner:

- Review the application from the first menu through the last menu.
- Inspect dialogs, buttons, context menus, double-click actions, combo boxes, toggle switches, navigation, loops, crashes, duplicate code, dead code, voice assistant behavior, integrations, appointments, Kanban screens, and model update behavior.
- Report findings and evidence only. Do not modify product code during an inspection-only task.
