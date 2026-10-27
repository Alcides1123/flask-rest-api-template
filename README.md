# Flask API REST Template

[![Development](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/development_pipeline.yml/badge.svg)](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/development_pipeline.yml)
[![Staging](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/staging_pipeline.yml/badge.svg)](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/staging_pipeline.yml)
[![Production](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/production_pipeline.yml/badge.svg)](https://github.com/vectornguyen76/flask-rest-api-template/actions/workflows/production_pipeline.yml)

<p align="center">
<img src="./assets/logo.png" alt="Logo" />
</p>

Rest API template developed in Python with the Flask framework. The template covers user management, jwt tokens for authentication, and assign permissions for each user with Flask Principal. In the local environment, it uses docker to create an environment made up of several services such as api (flask), database (postgresql), reverse-proxy (nginx).

## Index

- [Technology](#technology)
- [Requirements](#requirements)
- [Security Best Practices](#security-best-practices)
- [Environments](#environments)
  - [Develop](#develop)
  - [Testing](#testing)
  - [Local](#local)
  - [Production](#production)
- [Creating Deployment Archive](#creating-deployment-archive)
- [Flask Commands](#flask-commands)
  - [Flask-cli](#flask-cli)
- [Database Commands](#database-commands)
  - [Flask-migrate](#flask-migrate)
- [Swagger](#swagger)
- [CI/CD Status](#cicd-status)
- [Reference](#reference)
- [Contribution](#contribution)

## Technology

- **Operating System:** Ubuntu
- **Web Framework:** Flask
- **ORM:** Flask-sqlalchemy
- **Swagger:** Swagger-UI
- **Authentication:** Flask Json Web Token
- **Permission:** JWT Decorator
- **Serialization, Deserialization and Validation:** Marshmallow
- **Migration Database:** Flask-migrate
- **Environment Manager:** Anaconda/Miniconda
- **Containerization:** Docker, docker-compose
- **Database:** PostgreSQL
- **Python WSGI HTTP Server:** Gunicorn
- **Proxy:** Nginx
- **Tests:** Unittest
- **Deployment Platform:** AWS
- **CI/CD:** Github Actions

## Requirements

- **Python:** 3.10 - 3.12 (tested) | Latest Stable: Python 3.15.2 (as of Oct 2026)
- [Anaconda/Miniconda](instructions/anaconda-miniconda.md)
- [Docker](instructions/docker-dockercompose.md)
- [Docker-Compose](instructions/docker-dockercompose.md)
- [Github](https://github.com)

## Security Best Practices

### 🔒 Before You Start

**IMPORTANT:** Never commit sensitive files to version control!

#### Security Checklist

- [ ] Verify `.gitignore` excludes all `.env*` files
- [ ] Verify `.dockerignore` excludes:
  - `.env*`
  - `.git`
  - `__pycache__`
  - `*.pyc`
  - `logs/`
- [ ] Use `.env.example` templates (never commit actual `.env` files)
- [ ] Generate strong, unique secrets for production
- [ ] Never share or commit real credentials
- [ ] Rotate secrets regularly

#### Verify Your Repository is Secure (Windows PowerShell)

```powershell
# Check if .env files are tracked by git
git ls-files | Select-String -Pattern "\.env"
# Should return NOTHING or only .env.example files

# Check .gitignore
Get-Content .gitignore | Select-String -Pattern "\.env"
# Should show entries for .env files