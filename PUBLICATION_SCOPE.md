# GitHub publication scope

This repository is prepared for publication as the AYEC Pro project source.

## Intended contents

- Application source under `src/` and `Main.py`.
- Central services under `Web_Arayuzu/`, `Admin_Konsol/`, `backend/`, and
  `ecosystem/`.
- Shared contracts and operational documentation under `docs/` and `shared/`.
- CI quality checks under `.github/workflows/`.
- Sanitized project continuation records under `Konusmalar/`.

## Excluded contents

- `.env` and all credentials or tokens.
- Local SQLite databases, WAL files, backups, and logs.
- Python environments, caches, generated build folders, installers, and local
  reports.
- Local screenshots, maintenance uploads, and runtime state.

## Required checks before push

1. Confirm the destination is a dedicated AYEC Pro repository owned by
   `KeineLust10`.
2. Review the staged file list and verify that no secret or local database is
   included.
3. Run `python tools/mojibake_guard.py`.
4. Run `python tools/ascii_diff_guard.py`.
5. Run the focused test and compile commands required by the changed area.
6. Push to the repository default branch or a review branch according to the
   repository policy.

The current local checkout has no GitHub remote and no configured GitHub token.
The existing `Bulut` and `gdp-dashboard` repositories are not selected as the
AYEC Pro destination.
