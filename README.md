# Flask API REST Template

[![Development](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/development_pipeline.yml/badge.svg)](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/development_pipeline.yml)
[![Staging](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/staging_pipeline.yml/badge.svg)](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/staging_pipeline.yml)
[![Production](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/production_pipeline.yml/badge.svg)](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/production_pipeline.yml)

<p align="center">
<img src="./assets/logo.png" alt="Logo" />
</p>

Rest API template developed in Python with the Flask framework. The template covers user management, JWT tokens for authentication, and role/permission based authorization. In the local environment, it uses Docker to create an environment made up of several services: api (Flask + Gunicorn), database (PostgreSQL) and reverse-proxy (Nginx).

All commands in this guide are given for **Bash** (Linux / macOS / WSL / Git Bash) **and** **PowerShell** (Windows). Wherever a command is identical in both shells, it is shown only once.

## Index

- [Technology](#technology)
- [Requirements](#requirements)
- [Security Best Practices](#security-best-practices)
  - [Security Checklist](#security-checklist)
  - [Verify Your Repository is Secure](#verify-your-repository-is-secure)
  - [Generating Secrets](#generating-secrets)
  - [Default Seed Accounts](#default-seed-accounts)
    - [How authorization works](#how-authorization-works)
  - [Other Things to Know Before Going to Production](#other-things-to-know-before-going-to-production)
- [Environments](#environments)
  - [Environment Variables](#environment-variables)
  - [Develop](#develop)
  - [Testing](#testing)
  - [Local](#local)
  - [Production](#production)
- [Windows / PowerShell Notes](#windows--powershell-notes)
- [Creating Deployment Archive](#creating-deployment-archive)
- [Flask Commands](#flask-commands)
  - [Flask-cli](#flask-cli)
- [Database Commands](#database-commands)
  - [Flask-migrate](#flask-migrate)
- [API Endpoints](#api-endpoints)
- [Swagger](#swagger)
- [CI/CD Status](#cicd-status)
- [Reference](#reference)
- [Contribution](#contribution)

## Technology

- **Operating System:** Ubuntu (containers / deploy target), developed on Linux, macOS and Windows
- **Web Framework:** Flask
- **ORM:** Flask-sqlalchemy
- **Swagger:** Swagger-UI (via flask-smorest)
- **Authentication:** Flask-JWT-Extended
- **Permission:** JWT + role/permission decorator
- **Serialization, Deserialization and Validation:** Marshmallow
- **Migration Database:** Flask-migrate
- **Environment Manager:** Anaconda/Miniconda or `venv`
- **Containerization:** Docker, Docker Compose
- **Database:** PostgreSQL
- **Python WSGI HTTP Server:** Gunicorn
- **Proxy:** Nginx
- **Tests:** Unittest
- **Deployment Platform:** AWS
- **CI/CD:** Github Actions

## Requirements

- **Python:** 3.10 (the version used by the [Dockerfile](Dockerfile) and the CI pipelines). The pinned dependencies also install and pass the test suite on 3.12.
- **Git**
- **Docker** and **Docker Compose** (Docker Desktop on Windows/macOS) – only needed for the [Local](#local) environment
- **PostgreSQL** – provided by Docker Compose; a SQLite file can be used instead for quick local development (see [Develop](#develop))
- An environment manager: [Anaconda/Miniconda](https://docs.conda.io/en/latest/miniconda.html) or the built-in `venv` module
- On Windows: **PowerShell 5.1** or **PowerShell 7+** (all PowerShell snippets in this README work in both)

## Security Best Practices

### 🔒 Before You Start

**IMPORTANT:** Never commit sensitive files to version control!

This template reads every secret from environment variables (see [Environment Variables](#environment-variables)). Nothing in the repository should ever contain a real secret – not the code, not the Docker image, and not the deployment archive.

### Security Checklist

- [ ] Verify `.gitignore` excludes all `.env*` files (it does – see the `# Environment variable` block; only `*.example` templates are re-included)
- [ ] Verify `.dockerignore` excludes:
  - `.env*`
  - `.git`
  - `__pycache__`
  - `*.pyc`
  - `*.log` (so the `logs/` content is never baked into an image)
- [ ] Use `.env.example` templates only (never commit actual `.env` files)
- [ ] Generate strong, unique secrets for `SECRET_KEY` and `JWT_SECRET_KEY` in every environment (see [Generating Secrets](#generating-secrets))
- [ ] Change or remove the [default seed accounts](#default-seed-accounts) before exposing the API
- [ ] Never share or commit real credentials – use GitHub _Secrets_ for CI/CD (see [.github/workflows/README.md](.github/workflows/README.md))
- [ ] Rotate secrets regularly and after any suspected leak
- [ ] Install the pre-commit hooks – they include `detect-private-key` (see [Contribution](#contribution))

### Verify Your Repository is Secure

Run these from the repository root. Both variants do the same thing.

**Bash**

```bash
# 1. Check that no .env files are tracked by git
git ls-files | grep -E '(^|/)\.env'
# Should return NOTHING (or only *.example files)

# 2. Check that .gitignore has the rules
grep -n '\.env' .gitignore
# Should show ".env" and ".env*" (and the "!.env*.example" exceptions)

# 3. Ask git directly whether a given file would be ignored
git check-ignore -v .env .env.api.local .env.db.local
# Each file should be listed together with the matching .gitignore rule

# 4. Make sure no .env file ever made it into the history
git log --all --name-only --format='' | grep -E '(^|/)\.env' | sort -u
# Should return NOTHING (or only *.example files)
```

**PowerShell**

```powershell
# 1. Check that no .env files are tracked by git
git ls-files | Select-String -Pattern '(^|/)\.env'
# Should return NOTHING (or only *.example files)

# 2. Check that .gitignore has the rules
Get-Content .gitignore | Select-String -Pattern '\.env'
# Should show ".env" and ".env*" (and the "!.env*.example" exceptions)

# 3. Ask git directly whether a given file would be ignored
git check-ignore -v .env .env.api.local .env.db.local
# Each file should be listed together with the matching .gitignore rule

# 4. Make sure no .env file ever made it into the history
git log --all --name-only --format='' | Select-String -Pattern '(^|/)\.env' | Sort-Object -Unique
# Should return NOTHING (or only *.example files)
```

If step 1 or step 4 returns a real `.env` file, **treat every secret in it as compromised**: rotate the secrets first, then remove the file from the history (for example with [`git filter-repo`](https://github.com/newren/git-filter-repo)).

### Generating Secrets

`SECRET_KEY` (Flask) and `JWT_SECRET_KEY` (token signing) must be long, random and different from each other. The same command works in Bash and PowerShell:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Run it twice and paste one value into each variable. Never reuse the development values in staging or production.

### Default Seed Accounts

`flask create-user-admin` (which the Docker `entrypoint.sh` runs automatically when `APP_ENV=local`) seeds three accounts for convenience:

| Username | Password | Role  | Permissions                |
| -------- | -------- | ----- | -------------------------- |
| `admin`  | `123456` | Admin | read, write, delete, admin |
| `user`   | `123456` | User  | read, write                |
| `guest`  | `123456` | Guest | read                       |

These are **public, well-known credentials**. Before any environment is reachable by someone other than you:

- change the passwords (`PUT /user/<id>`), or
- edit `init_db_user()` in [manage.py](manage.py) to read the initial password from an environment variable, or
- do not run `create-user-admin` at all in that environment (in `APP_ENV=production` the entrypoint does not run it).

#### How authorization works

- `read`, `write` and `delete` gate access to data.
- The `admin` permission gates everything that changes _who may do what_: creating / editing / deleting roles and permissions, assigning roles to users, and blocking users. `write` alone never lets a user change authorization.
- Users may update their own username and password; only an admin may update other users or change `roles`.
- Nothing authorization-related is stored in the JWT. Every request re-reads roles and permissions from the database, so revoking a role or blocking a user takes effect on the user's very next request.
- Lockout guard: any change that would remove the caller's own `admin` access (e.g. deleting the Admin role, removing the `admin` permission from it, renaming the permission, or an admin blocking themselves) is rejected with `400` before it is committed.

There is no special "super admin" user id. Whoever holds a role with the `admin` permission is an admin; running `flask create-user-admin` on a database seeded by an older version of this template adds the `admin` permission to the existing `Admin` role.

### Other Things to Know Before Going to Production

- **CORS** is off unless `CORS_ORIGINS` lists your front-end origin(s); credentials are never allowed (authentication is a bearer token, not a cookie). `DevelopConfig` defaults to `*` for convenience – never use `*` in production.
- **Rate limiting** protects `/login` (`RATELIMIT_LOGIN`, default `5 per minute`) and `/register` (`RATELIMIT_REGISTER`, default `3 per minute`) per client IP. The default `memory://` store is per Gunicorn worker; set `RATELIMIT_STORAGE_URI` to a shared store (e.g. Redis) for exact limits across workers. Behind Nginx, `TRUSTED_PROXY_COUNT` must be set (the Local / Production configs default to `1`) so the limit is keyed on the real client address and not on the proxy.
- **Dependencies**: the Docker image installs only `requirements.txt` (runtime). Linters, test tools and `pip-audit` are in `requirements-dev.txt`. CI runs `pip-audit -r requirements.txt` on every pipeline and fails on known vulnerabilities – run it locally too before bumping versions.
- **Container user**: the image runs as the unprivileged user `app` (uid/gid 1000). The `./logs` bind mount must be writable by that uid; on a host where your user is not uid 1000, `chown -R 1000:1000 logs` (or change the ids in the Dockerfile).
- **Token lifetimes** are set in `config.py` (`JWT_ACCESS_TOKEN_EXPIRES` = 30 minutes, `JWT_REFRESH_TOKEN_EXPIRES` = 30 days). Logging out or refreshing adds the token `jti` to a database blocklist together with the token's expiry; run `flask prune-blocklist` periodically (cron) to drop rows for tokens that have expired anyway.
- **Registration** (`POST /register`) is open and assigns the `Guest` (read-only) role, looked up by name. Disable or protect it if you do not want self sign-up.
- **Environment files are not part of the deployment archive** (see [Creating Deployment Archive](#creating-deployment-archive)); `.env.api.local` / `.env.db.local` must be provisioned on the server (or injected by your orchestrator) out of band.
- **Gunicorn worker count / timeouts** are tunable via environment variables (`WEB_CONCURRENCY`, `MAX_WORKERS`, `TIMEOUT`, …) – see [gunicorn/gunicorn_config.py](gunicorn/gunicorn_config.py).
- Run the app behind TLS (terminate at the load balancer or in Nginx). The provided [nginx/default.conf](nginx/default.conf) is plain HTTP.

## Environments

The configuration class is selected with `APP_SETTINGS_MODULE` (see [config.py](config.py)):

| Environment | `APP_SETTINGS_MODULE`     | `APP_ENV`    | Database variable   | Debug | Typical use                        |
| ----------- | ------------------------- | ------------ | ------------------- | ----- | ---------------------------------- |
| Develop     | `config.DevelopConfig`    | `develop`    | `DATABASE_URL`      | on    | `flask run` on your machine        |
| Testing     | `config.TestingConfig`    | `testing`    | `DATABASE_TEST_URL` | on    | `flask tests` / CI                 |
| Local       | `config.LocalConfig`      | `local`      | `DATABASE_URL`      | off   | Docker Compose (api + db + nginx)  |
| Production  | `config.ProductionConfig` | `production` | `DATABASE_URL`      | off   | Docker image on the server (CI/CD) |

### Environment Variables

`python-dotenv` is installed, so the `flask` command automatically loads a `.env` file from the current directory – this is the recommended, shell-independent way to set variables for development and testing. Docker Compose instead reads `.env.api.local` and `.env.db.local` (see [Local](#local)). All of these files are git-ignored.

| Variable                                                                                                       | Used by                      | Description                                                                                |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------ |
| `APP_SETTINGS_MODULE`                                                                                          | `app/__init__.py`            | Config class, e.g. `config.DevelopConfig`                                                  |
| `APP_TEST_SETTINGS_MODULE`                                                                                     | `tests/`                     | Config class for tests, defaults to `config.TestingConfig`                                 |
| `APP_NAME`                                                                                                     | `config.py`                  | Application name                                                                           |
| `SECRET_KEY`                                                                                                   | Flask                        | Flask secret – **generate a random value**                                                 |
| `JWT_SECRET_KEY`                                                                                               | Flask-JWT-Extended           | Token signing key – **generate a random value**, different from `SECRET_KEY`               |
| `DATABASE_URL`                                                                                                 | Develop / Local / Production | SQLAlchemy URL, e.g. `postgresql://user:pass@host:5432/db` or `sqlite:///dev.db`           |
| `DATABASE_TEST_URL`                                                                                            | Testing                      | SQLAlchemy URL for the test database (tables are created and dropped by every test)        |
| `APP_ENV`                                                                                                      | `entrypoint.sh`              | `local` or `production` – decides what the container entrypoint does                       |
| `DATABASE`                                                                                                     | `entrypoint.sh`              | Set to `postgres` to make the entrypoint wait for PostgreSQL before starting               |
| `BBDD_HOST`                                                                                                    | `entrypoint.sh`              | PostgreSQL host used by the readiness check (`db_service` in Docker Compose)               |
| `POSTGRES_USER`                                                                                                | `entrypoint.sh`, postgres    | Database user                                                                              |
| `POSTGRES_PASSWORD`                                                                                            | postgres image               | Database password                                                                          |
| `POSTGRES_DB`                                                                                                  | `entrypoint.sh`, postgres    | Database name                                                                              |
| `PGPASSWORD`                                                                                                   | `entrypoint.sh` (`psql`)     | Same value as `POSTGRES_PASSWORD`; `psql` needs it for the non-interactive readiness check |
| `API_ENTRYPOINT`                                                                                               | `entrypoint.sh`              | WSGI entrypoint for Gunicorn, default `wsgi:app` ([wsgi.py](wsgi.py))                      |
| `LOG_TIMEZONE`                                                                                                 | `app/utils/logging.py`       | Timezone for log timestamps, default `Asia/Ho_Chi_Minh`                                    |
| `API_HOST` / `API_PORT`                                                                                        | Gunicorn                     | Bind address, defaults `0.0.0.0` / `5000`                                                  |
| `WEB_CONCURRENCY`, `MAX_WORKERS`, `WORKERS_PER_CORE`, `TIMEOUT`, `GRACEFUL_TIMEOUT`, `KEEP_ALIVE`, `LOG_LEVEL` | Gunicorn                     | Optional tuning, see [gunicorn/gunicorn_config.py](gunicorn/gunicorn_config.py)            |
| `CORS_ORIGINS`                                                                                                 | Flask-CORS                   | Comma separated allowed origins; empty = no cross-origin access (Develop defaults to `*`)  |
| `RATELIMIT_LOGIN` / `RATELIMIT_REGISTER`                                                                       | Flask-Limiter                | Limits for `/login` and `/register`, defaults `5 per minute` / `3 per minute`              |
| `RATELIMIT_STORAGE_URI`                                                                                        | Flask-Limiter                | Limit counter storage, default `memory://` (per process); e.g. `redis://redis:6379`        |
| `TRUSTED_PROXY_COUNT`                                                                                          | `ProxyFix`                   | Reverse proxies whose `X-Forwarded-*` headers are trusted; `0` (Develop), `1` (Local/Prod) |

> Log files go to `logs/api.log` (`logs/api_tests.log` for tests); the directory is created automatically on start-up and its content is git-ignored.

### Develop

Run the API directly on your machine with Flask's development server.

**1. Clone and create the virtual environment**

Bash:

```bash
git clone https://github.com/vectornguyen76/flask-rest-api-template.git
cd flask-rest-api-template

# Option A – venv
python3.10 -m venv venv
source venv/bin/activate

# Option B – conda
conda create -n flask-template python=3.10 -y
conda activate flask-template

pip install -r requirements-dev.txt   # runtime + linters/test tools
```

PowerShell:

```powershell
git clone https://github.com/vectornguyen76/flask-rest-api-template.git
Set-Location flask-rest-api-template

# Option A – venv  (if activation is blocked, see "Windows / PowerShell Notes")
py -3.10 -m venv venv
.\venv\Scripts\Activate.ps1

# Option B – conda  (run "conda init powershell" once, then reopen the terminal)
conda create -n flask-template python=3.10 -y
conda activate flask-template

pip install -r requirements-dev.txt   # runtime + linters/test tools
```

**2. Create a `.env` file** in the project root (git-ignored). Either point `DATABASE_URL` at a PostgreSQL instance (for example the one from [Local](#local): `docker compose up -d db_service`), or use SQLite for a zero-setup start:

```dotenv
APP_NAME=flask-rest-api-template
APP_SETTINGS_MODULE=config.DevelopConfig
APP_TEST_SETTINGS_MODULE=config.TestingConfig
SECRET_KEY=<paste output of the secrets command>
JWT_SECRET_KEY=<paste a second, different output>
DATABASE_URL=sqlite:///dev.db
DATABASE_TEST_URL=sqlite:///test.db
```

If you prefer not to use a `.env` file, export the variables in the shell instead:

```bash
# Bash
export APP_SETTINGS_MODULE=config.DevelopConfig
```

```powershell
# PowerShell (current session only)
$env:APP_SETTINGS_MODULE = "config.DevelopConfig"
```

**3. Create the schema, seed the default accounts and run**

```bash
flask create-db
flask create-user-admin
flask run
```

The API is now on <http://127.0.0.1:5000> and Swagger UI on <http://127.0.0.1:5000/swagger-ui>.

**4. Quick smoke test** – log in as the seeded `admin` and call a protected endpoint:

Bash:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://127.0.0.1:5000/user -H "Authorization: Bearer $TOKEN"
```

PowerShell:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/login `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"123456"}'

Invoke-RestMethod -Uri http://127.0.0.1:5000/user -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

(In Windows PowerShell 5.1, `curl` is an alias of `Invoke-WebRequest`; use `curl.exe` if you want the real curl.)

### Testing

Tests live in `tests/unit` and `tests/integration` and are discovered with the pattern `tests_*.py`. They build their own app instances with `create_app()` from `APP_TEST_SETTINGS_MODULE` (default `config.TestingConfig`) and create/drop all tables on `DATABASE_TEST_URL` around every test, so **point `DATABASE_TEST_URL` at a throw-away database**.

```bash
flask tests                       # run all tests
flask tests --pattern "tests_users_*.py"   # run a subset
flask cov                         # tests + coverage summary in the terminal
flask cov-html                    # tests + HTML report in report/htmlcov/
```

The CI pipelines run the same `python -m flask tests` against a PostgreSQL service container with `DATABASE_TEST_URL=postgresql://db_user:db_password@localhost/db_test`. To reproduce that locally:

```bash
docker compose up -d db_service
```

and set `DATABASE_TEST_URL=postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@localhost:5432/<POSTGRES_DB>` in your `.env`.

### Local

The `local` environment runs the full stack with Docker Compose: `api_service` (Gunicorn, port 5000), `db_service` (PostgreSQL 14, port 5432) and `nginx_service` (port 80). The container entrypoint waits for PostgreSQL, runs `flask create-db` and `flask create-user-admin`, then starts Gunicorn.

**1. Create the two env files** in the project root (both are git-ignored and docker-ignored):

`.env.db.local`

```dotenv
POSTGRES_USER=db_user
POSTGRES_PASSWORD=<strong password>
POSTGRES_DB=flask_template
```

`.env.api.local`

```dotenv
APP_NAME=flask-rest-api-template
APP_SETTINGS_MODULE=config.LocalConfig
APP_ENV=local
SECRET_KEY=<paste output of the secrets command>
JWT_SECRET_KEY=<paste a second, different output>

# Database – must match .env.db.local
DATABASE=postgres
BBDD_HOST=db_service
POSTGRES_USER=db_user
POSTGRES_PASSWORD=<same as .env.db.local>
PGPASSWORD=<same as .env.db.local>
POSTGRES_DB=flask_template
DATABASE_URL=postgresql://db_user:<same password>@db_service:5432/flask_template

# Gunicorn
API_ENTRYPOINT=wsgi:app
API_HOST=0.0.0.0
API_PORT=5000
```

> `PGPASSWORD` is required: `entrypoint.sh` polls the database with `psql`, which cannot prompt for a password inside a container. Without it the container loops on `Waiting for PostgreSQL...` forever.

**2. Build and start** (identical in Bash and PowerShell):

```bash
docker compose up -d --build
docker compose logs -f api_service      # watch the entrypoint / Gunicorn output
```

- API through Nginx: <http://localhost/> – Swagger UI: <http://localhost/swagger-ui>
- API directly: <http://localhost:5000/>
- Application logs are written to `./logs/api.log` on the host (bind mount, must be writable by uid 1000 – see [container user](#other-things-to-know-before-going-to-production)), Nginx logs to `./nginx/log/`.

**3. Stop**

```bash
docker compose down          # keep the database volume
docker compose down -v       # also delete the postgresql_data volume
```

### Production

In production the same image is started with `APP_ENV=production` and `APP_SETTINGS_MODULE=config.ProductionConfig`. In that mode the entrypoint does **not** create the schema or seed accounts – run migrations (see [Flask-migrate](#flask-migrate)) as a separate, deliberate step – and starts Gunicorn with `--bind $API_HOST:$API_PORT --workers 4 --timeout 10`.

The staging and production GitHub Actions pipelines build and push the image to Docker Hub, create an EC2 host with CloudFormation, and use Ansible to unzip the deployment archive on the server and run `docker compose up -d`. See [.github/workflows/README.md](.github/workflows/README.md) for the required GitHub _Secrets_ and _Variables_.

Because the archive never contains `.env*` files, **`.env.api.local` and `.env.db.local` must already exist on the server** (in `/home/ubuntu/server`) with production values – provision them through your secrets manager, Ansible Vault, or by hand over SSH. Never add them to the repository or the archive to "make it work".

## Windows / PowerShell Notes

- **Script execution policy.** If `.\venv\Scripts\Activate.ps1` fails with "running scripts is disabled on this system", allow locally-created scripts for your user:

  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```

- **Line endings.** `entrypoint.sh` runs inside a Linux container and **must keep LF line endings**; with CRLF the container fails with `exec /app/entrypoint.sh: no such file or directory`. The repository's `.gitattributes` (`*.sh text eol=lf`) enforces this on checkout regardless of your `core.autocrlf` setting, but editors can still convert it when saving. Check with:

  ```powershell
  git ls-files --eol entrypoint.sh
  # expected: i/lf  w/lf  attr/text eol=lf  entrypoint.sh
  ```

  If the working-tree side shows `w/crlf`, restore it with `git checkout -- entrypoint.sh`.

- **Environment variables.** `$env:NAME = "value"` only lasts for the current PowerShell session. Prefer the `.env` file, which Flask loads automatically on every platform.

- **Paths.** Use `Set-Location` / `cd` and backslashes or forward slashes interchangeably; Docker Compose bind mounts (`./logs`, `./nginx`) work unchanged with Docker Desktop (WSL 2 backend recommended).

- **`curl`.** In Windows PowerShell 5.1 `curl` is an alias for `Invoke-WebRequest`. Use `curl.exe` for the real binary or the `Invoke-RestMethod` examples in this README.

- **Docker commands** (`docker compose ...`) are identical in both shells.

## Creating Deployment Archive

The production/staging pipelines zip the repository checkout (`zip -qq -r artifact.zip .`) and Ansible extracts it on the server. Because CI runs on a clean checkout, no secrets can end up in that archive. When creating one **by hand**, exclude everything that is local, generated or secret:

**Bash**

```bash
zip -r artifact.zip . \
  -x '.git/*' '.env*' 'logs/*' 'nginx/log/*' 'venv/*' '.venv/*' \
     '*/__pycache__/*' '*.pyc' 'report/*' '*.db'
```

**PowerShell**

```powershell
Get-ChildItem -Path . -Force -Exclude .git, .env*, logs, venv, .venv, report, *.db |
  Compress-Archive -DestinationPath artifact.zip -Force
```

Then verify the archive before shipping it:

```bash
# Bash
unzip -l artifact.zip | grep -E '\.env|\.git/'
```

```powershell
# PowerShell
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::OpenRead("$PWD\artifact.zip").Entries.FullName | Select-String -Pattern '\.env|\.git/'
```

Both must return nothing.

## Flask Commands

### Flask-cli

Custom commands are registered in [manage.py](manage.py) and are available through the `flask` CLI once `APP_SETTINGS_MODULE` (and a database URL) is set. Run `flask --help` to list them.

| Command                      | Description                                                                                                                                                                                                   | Available in production |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `flask create-db`            | Create all tables (`db.create_all()`)                                                                                                                                                                         | yes                     |
| `flask reset-db`             | Drop and recreate all tables – **destroys data**                                                                                                                                                              | yes                     |
| `flask drop-db`              | Drop all tables – **destroys data**                                                                                                                                                                           | yes                     |
| `flask create-user-admin`    | Seed permissions, roles and the three [default accounts](#default-seed-accounts) if `admin` does not exist; otherwise make sure the `admin` permission exists and is granted to the Admin role (upgrade path) | yes                     |
| `flask prune-blocklist`      | Delete revoked-token rows whose token has expired anyway; schedule it (e.g. daily)                                                                                                                            | yes                     |
| `flask tests [--pattern]`    | Run the unittest suite                                                                                                                                                                                        | no                      |
| `flask cov [--pattern]`      | Run the tests with a coverage summary (needs `requirements-dev.txt`)                                                                                                                                          | no                      |
| `flask cov-html [--pattern]` | Run the tests and write an HTML coverage report to `report/htmlcov/`                                                                                                                                          | no                      |
| `flask routes`               | List all registered routes (built-in)                                                                                                                                                                         | yes                     |
| `flask run`                  | Start the development server (built-in, **not** for production – use Gunicorn)                                                                                                                                | yes                     |

The application is built by the factory `app.create_app()`; [wsgi.py](wsgi.py) calls it with `APP_SETTINGS_MODULE` and is what Gunicorn serves (`wsgi:app`). The `flask` CLI discovers `wsgi.py` automatically, so `FLASK_APP` does not need to be set. Nothing is created at import time, which is what lets the tests build isolated app instances.

## Database Commands

### Flask-migrate

Flask-Migrate (Alembic) is initialised in `app/__init__.py`, so the standard commands are available:

```bash
flask db init                      # once – creates the migrations/ folder
flask db migrate -m "add column"   # autogenerate a revision from model changes
flask db upgrade                   # apply pending revisions
flask db downgrade                 # roll back one revision
flask db history                   # show revisions
```

> **Upgrading an existing database:** `user.time_created` is now a timezone-aware `DateTime` (was a string) and `blocklist.expires_at` is a new nullable column. Generate and apply a migration (`flask db migrate` / `flask db upgrade`) or, for a throw-away local database, `flask reset-db`.
>
> **Note:** this template's `.gitignore` lists `migrations/`, so generated migrations are **not** committed by default. For a real project you will almost certainly want to remove that line and version your migrations, otherwise production schema changes cannot be reproduced.

## API Endpoints

All endpoints except `/login` and `/register` require `Authorization: Bearer <access_token>`. The permission column is enforced by the `permission_required` decorator through the user's roles (see [How authorization works](#how-authorization-works)). Unknown ids return a JSON `404`.

| Method | Path                              | Permission     | Description                                                   |
| ------ | --------------------------------- | -------------- | ------------------------------------------------------------- |
| POST   | `/register`                       | –              | Create a user (gets the `Guest` role)                         |
| POST   | `/login`                          | –              | Returns `access_token` and `refresh_token`                    |
| POST   | `/refresh`                        | refresh token  | New (non-fresh) token pair; the used refresh token is revoked |
| POST   | `/logout`                         | any token      | Revoke the access token and its paired refresh token          |
| GET    | `/user`                           | read           | List users                                                    |
| GET    | `/user/<id>`                      | read           | Get a user                                                    |
| PUT    | `/user/<id>`                      | self, or admin | Update own username / password; admin may also set `roles`    |
| PUT    | `/block-user/<id>`                | admin          | Block or unblock a user (not yourself)                        |
| POST   | `/user/<user_id>/role/<role_id>`  | admin          | Assign a role to a user                                       |
| DELETE | `/user/<user_id>/role/<role_id>`  | admin          | Remove a role from a user                                     |
| GET    | `/role`, `/role/<id>`             | read           | List / get roles                                              |
| POST   | `/role`                           | admin          | Create a role                                                 |
| PUT    | `/role/<id>`                      | admin          | Update a role and its permissions                             |
| DELETE | `/role/<id>`                      | admin          | Delete a role                                                 |
| GET    | `/permission`, `/permission/<id>` | read           | List / get permissions                                        |
| POST   | `/permission`                     | admin          | Create a permission                                           |
| PUT    | `/permission/<id>`                | admin          | Update a permission                                           |
| PUT    | `/permission-role-update`         | admin          | Replace the roles of one or more permissions                  |
| GET    | `/role-permission`                | read           | List role ↔ permission links                                  |

A Postman environment is provided in [tests/postman/](tests/postman/FlaskTemplate.postman_environment.json) (`HOST`, `TOKEN`, `REFRESHTOKEN`).

## Swagger

Interactive documentation is generated by flask-smorest from the Marshmallow schemas:

- Swagger UI: `http://<host>/swagger-ui` (e.g. <http://127.0.0.1:5000/swagger-ui> in develop, <http://localhost/swagger-ui> through Nginx in local)
- OpenAPI document: `http://<host>/openapi.json`

Click **Authorize** and enter `Bearer <access_token>` to call protected endpoints from the UI.

<p align="center">
<img src="./assets/swagger.png" alt="Swagger UI" />
</p>

## CI/CD Status

The badges at the top of this file show the status of the three GitHub Actions workflows:

| Workflow    | Trigger                     | What it does                                                                          |
| ----------- | --------------------------- | ------------------------------------------------------------------------------------- |
| Development | PR into / push to `develop` | isort, black, flake8, tests against PostgreSQL, build & push image                    |
| Staging     | PR into `staging`           | Same as development + CloudFormation stack, Ansible deploy, A/B clean-up of old stack |
| Production  | PR into `master`            | Same as staging, targeting the production stack                                       |

Details, required secrets and variables: [.github/workflows/README.md](.github/workflows/README.md). CloudFormation helper commands: [.github/workflows/cloudformations/README.md](.github/workflows/cloudformations/README.md).

## Reference

- [Flask](https://flask.palletsprojects.com/) · [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) · [Flask-Migrate](https://flask-migrate.readthedocs.io/)
- [Flask-JWT-Extended](https://flask-jwt-extended.readthedocs.io/) · [flask-smorest](https://flask-smorest.readthedocs.io/) · [Marshmallow](https://marshmallow.readthedocs.io/)
- [Gunicorn settings](https://docs.gunicorn.org/en/stable/settings.html) · [Docker Compose](https://docs.docker.com/compose/)
- [python-dotenv and the Flask CLI](https://flask.palletsprojects.com/en/2.2.x/cli/#environment-variables-from-dotenv)
- [PowerShell execution policies](https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_execution_policies)

## Contribution

1. Fork the repository and create a branch from `develop`.
2. Install the pre-commit hooks so that formatting and secret detection run before every commit:

   ```bash
   pip install pre-commit
   pre-commit install
   pre-commit run --all-files   # optional: check the whole tree once
   ```

   The hooks run `isort` (black profile), `black`, `flake8`, `prettier` (Markdown/YAML/JSON), `detect-private-key`, `end-of-file-fixer` and `trailing-whitespace` – the same checks as the CI pipeline.

3. Add or update tests under `tests/` and make sure `flask tests` passes.
4. Open a pull request into `develop`. Do not include `.env*` files, logs, databases or coverage reports.
