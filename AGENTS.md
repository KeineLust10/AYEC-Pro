# AYEC Pro Coding Rules

## Central Platform Rule

Read docs/AYEC_ECOSYSTEM_RULES.md before changing licensing, authentication,
database integration, backup, restore, pricing, or onboarding a new product.
Technical Service is a product; Admin_Konsol is the management center.
Use the installed ayec-core package and register products in ecosystem/products.json.
Report the connection contract and implement integration as part of new-product work.
Preserve product, customer and device isolation; verify deployed behavior before
claiming live completion. Existing task authorization remains sufficient.

## ASCII Source Rule

All new source code, comments, documentation, test data, and UI literals must be written as ASCII-only text.

Reason: Codex and Windows terminals can corrupt Turkish characters when text passes through different code pages. ASCII source prevents mojibake.

Rules:

- Do not type Turkish characters directly in source files.
- For user-visible Turkish text, use Unicode escape sequences in code.
- Example: write `"M\u00fc\u015fteri"` instead of typing the Turkish word directly.
- Keep files encoded as UTF-8.
- Do not paste mojibake text such as `M\u00c3\u00bc...` or `Sat\u00c4...`.
- Before finishing changes, run:

```powershell
python tools/mojibake_guard.py
python tools/ascii_diff_guard.py
```

Allowed exceptions:

- Binary files.
- Existing legacy text that has not been edited.
- External vendor files.
- Generated files that are not committed.

When editing an existing non-ASCII line, rewrite the changed line as ASCII using escapes.

## Dialog Footer Rule

- Use the shared `ModernDialog` or `BaseModernDialog` footer for persistent dialog actions.
- Add action controls through `add_button()` or `footer_layout`.
- Do not leave a visible standard footer without a visible action or status control.
- Body-only dialogs must call `set_footer_visible(False)`.
- Do not create a second action row in `content_layout` when the standard footer is available.

## Incremental Source Inspection Rule

Do not read or print a large source file in one operation.

- Locate the exact class, method, or symbol with `rg -n` first.
- Read only a small bounded range around that location.
- Make and test one focused change at a time.
- Do not begin a second feature area until the current focused change has been verified.

## Incremental Source Inspection Rule

Do not read or print large source files in a single command.

- First locate the exact symbol or text with `rg -n`.
- Read only the required local context with small, targeted chunks.
- Keep each source-reading chunk focused on one function, class section, or issue.
- Do not use whole-file output commands for source code, including `Get-Content` without a bounded range.
- Continue investigation and edits in small verified steps, then run focused tests for the changed behavior.
