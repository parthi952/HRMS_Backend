# TIBOS HRMS Backend

Company-owned FastAPI backend for the TIBOS HRMS application.

## Local setup

1. Create a Python virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env` and supply development-only values.
4. Apply migrations with `alembic upgrade head`.
5. Start the API with `uvicorn main:app --reload`.

The application uses `URL_DB` for its database. SQLite is a local fallback only;
production should use the managed production database configured outside Git.

## Production entry points

- FastAPI application: `main.py`
- Database configuration: `database.py`
- Database migrations: `alembic/`
- Employee birthday delivery: `Festival/BirthdayService.py`
- Authentication and SSO: `Auth/`
- Runtime dependencies: `requirements.txt`

## Security rules

- Never commit `.env`, databases, uploads, SSO configuration, private keys, or
  certificates.
- Store production configuration outside the checkout, preferably in Azure Key
  Vault or a root-owned environment file.
- Deploy through a company-owned identity; do not use a former employee's token
  or SSH key.
- Apply Alembic migrations before restarting a new application release.

See `docs/REPOSITORY_MIGRATION.md` before connecting this source snapshot to the
company GitHub organization or changing the Azure VM deployment.
