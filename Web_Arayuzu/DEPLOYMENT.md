# AYEC Pro Web Server Deployment

This package runs the AYEC Pro web API and interface with Docker Compose. It
does not start automatically while you inspect or edit the source tree.

## Files to copy

Copy the complete `Web_Arayuzu` directory to the server. Keep these files
together:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `requirements.txt`, `requirements-ocr.txt`, and `requirements-paddle.txt`
- `Main.py`, `web/`, and the remaining application files

Do not copy local `.env`, database, backup, log, or virtual-environment files
from a developer machine. The Docker build context excludes these local files.

To create a clean upload archive from the current source, run:

```powershell
python tools/build_deployment_bundle.py
```

The archive is written to `../dist/AYEC_Pro_Web_Server.zip`. It contains the
web runtime and deployment configuration while excluding local database,
tenant, backup, upload, and virtual-environment data.

## Configure and validate

From the copied `Web_Arayuzu` directory, create the environment file and edit
the public port and dependency profile if required:

```powershell
Copy-Item .env.example .env
```

Validate the Compose file before starting the service:

```powershell
docker compose config --quiet
```

Build and start the service when the server is ready:

```powershell
docker compose build ayec-web
docker compose up -d ayec-web
docker compose logs -f ayec-web
```

## Reset the platform admin password

After the service is running, open PowerShell in the extracted deployment
folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RESET_ADMIN_PASSWORD.ps1
```

Enter a password with at least 8 characters when prompted. The script applies
it to `ayecpro@gmail.com` in the running `ayec-web` container. It does not put
the password in the command line, and the reset utility retains a database
backup before changing the account.

The Compose file publishes the selected host port to container port `8501`.
Its bind mounts keep `/data`, tenant data, and web uploads outside the
container. Back up the host data, tenant data, and upload directories together.
Do this before moving or restoring the deployment.

## Network and operations

Place the service behind an HTTPS reverse proxy for public access. Restrict
the application port to the proxy and trusted administration networks. Do not
publish SQLite files or the data directories as static web content.

Use `docker compose stop ayec-web` to stop the service and
`docker compose start ayec-web` to start it again. Updating source files
requires rebuilding the image before replacing the running container.

## Verification boundary

The Compose configuration can be validated without starting the application.
An image build requires an available Docker Engine and access to the package
registries used by the Dockerfile. Application screenshots and runtime checks
must be performed on the server deployment after you start it.
