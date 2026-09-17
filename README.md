# AYEC Pro

AYEC Pro is the desktop and web platform for technical service operations,
customer management, stock, finance, appointments, licensing, and central
product administration.

## Platform structure

- `src/` contains the desktop application.
- `Web_Arayuzu/` contains the central web and license services.
- `Admin_Konsol/` contains the administration center.
- `ecosystem/` contains shared product registration and AYEC Core contracts.
- `docs/` contains architecture, deployment, security, and operation notes.
- `Konusmalar/` contains sanitized continuation records for project work.

## Shared platform rule

Products use the shared AYEC Core contract for licensing, identity, tenant and
device isolation, database access, backup, restore, synchronization, and smart
import. Product onboarding is registered in `ecosystem/products.json` and is
managed through `Admin_Konsol` and `Web_Arayuzu`.

## Local setup

1. Copy `.env.example` to `.env`.
2. Fill only the local values required for the selected service.
3. Create a virtual environment and install `requirements.txt`.
4. Start the desktop application with `Baslat.bat` or the documented command.
5. Read `docs/AYEC_ECOSYSTEM_RULES.md` before changing shared platform areas.

Do not commit `.env`, local databases, credentials, build output, or runtime
logs. Live server, HTTPS, payment, and release checks must be verified
separately before a deployment is called complete.
