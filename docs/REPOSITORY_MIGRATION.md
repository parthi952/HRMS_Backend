# Repository migration checklist

This repository is intentionally a clean snapshot. It does not include the Git
history from the former employee-owned public repository because that history
contains a database and credentials.

## Before publishing

- Create a company GitHub organization with at least two company-controlled
  owners and require two-factor authentication.
- Create a private, empty `hrms-backend` repository. Do not add a GitHub README,
  license, or `.gitignore` because this snapshot already contains them.
- Rotate database, SMTP, SSO, API, deployment, and signing secrets exposed by the
  previous public repository.
- Confirm that Azure subscription, DNS, VM, database, and certificate access are
  all controlled by the company.

## First publish

From this directory:

```bash
git init -b main
git add .
git commit -m "Initial secure company-owned HRMS backend"
git remote add origin git@github.com:COMPANY/hrms-backend.git
git push -u origin main
```

Make the repository private before pushing. Enable branch protection immediately
after the first push and require pull requests for future production changes.

## Azure VM cutover

Do not edit the running production checkout first. Take a VM backup and database
backup, clone the new repository into a separate release directory, create a new
virtual environment, install dependencies, load secrets from the existing secure
configuration, apply `alembic upgrade head`, and test the API on an unused local
port. Only then update the systemd service or release symlink and reload Nginx.

Keep the previous release directory until the application, authentication, file
uploads, email, SSO, and birthday scheduler have all been verified.
