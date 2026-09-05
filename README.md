# Foresight — Academic Analytics

Marks and attendance go in; a ranked, explained view of which students need help comes out — while there is still time to act on it.

Flask · MySQL 8 · vanilla JavaScript. JWT authentication, role-based access control, an audited database, 165 automated tests and a one-command Docker setup.

**The full documentation lives in [`Foresight/README.md`](Foresight/README.md)** — architecture, the database design, how risk scoring works, security notes and the API reference.

## Quick start

```bash
cd Foresight
docker compose up --build
```

Then open <http://localhost:5000> and sign in as `admin` / `Admin@2024`.

Running it without Docker is covered in `Foresight/setup.txt`.

## What is in this branch

| Path | Contents |
| --- | --- |
| [`Foresight/`](Foresight) | The application — backend, database, frontend and tests |
| [`Documentation/`](Documentation) | Project reports |
| `.github/workflows/` | CI — pytest and ruff, plus a clean-MySQL load of every view, trigger and procedure |

The CI workflow sits at the repository root rather than inside `Foresight/`, because GitHub only reads workflows from the root.
