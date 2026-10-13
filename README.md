# indo-weather-etl

An ETL Pipeline designed to extract data from public weather forecast API provided by [BMKG](https://data.bmkg.go.id/prakiraan-cuaca/), transform the extracted data then load it into PostgreSQL

---

## Table of Contents

- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Usage](#usage)
- [Architecture Overview](#architecture-overview)
  - [Extract Layer](#extract-layer)
  - [Transform Layer](#transform-layer)
  - [Load Layer](#load-layer)
  - [Runner Layer](#runner-layer)
  - [Additional Layer](#additional-layer)
- [Running Tests](#running-tests)
  - [Running Full Tests](#running-full-tests)
  - [Running Non-Integration Tests Only](#running-non-integration-tests-only)
  - [Running Integration Tests Only](#running-integration-tests-only)
- [Run with systemd](#run-with-systemd)
  - [1. Create the service unit](#1-create-the-service-unit)
  - [2. Create the timer unit](#2-create-the-timer-unit)
  - [3. Enable the timer](#3-enable-the-timer)
  - [4. Verify](#4-verify)

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Rifki-NQ/indo-weather-etl.git

# 2. Navigate into the project directory
cd indo-weather-etl

# 3. Create a virtual environment

# Linux / macOS
python3 -m venv .venv

# Windows
python -m venv .venv

# 4. Activate the virtual environment

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# 5. Install dependencies
pip install -e .

# (Optional) Install dev dependencies
pip install -e ".[dev]"
```

---

## Environment Variables

This project loads configuration from a `.env` file. Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

| Variable | Description | Required | Example |
| -------- | ----------- | -------- | ------- |
| `DATABASE_URL` | Async PostgreSQL connection string for the main (production) database | Yes | `postgresql+asyncpg://user:pass@host/neondb?ssl=require` |
| `TEST_DATABASE_URL` | Async PostgreSQL connection string for a **separate, dedicated test database** — not a branch of the main DB | Yes | `postgresql+asyncpg://user:pass@host/neondb_test?ssl=require` |
| `ADM4_CODES_PATH` | Path to the CSV containing adm4 codes to ingest | Yes | `myfolder/adm4_codes.csv` |

> `.env` is git-ignored — never commit real credentials. Keep `.env.example` updated with placeholder values whenever a new variable is added.
> `DATABASE_URL` and `TEST_DATABASE_URL` point to **two distinct Neon databases**, not branches of the same one — running tests will not affect production data, but you'll need to run migrations/seed data on both independently.

---

## Usage

Run the pipeline with:

```bash
run_etl
```

> - make sure the `CSV` file with a column of `adm4 codes` exists for the runner to ingest, see the example in [`jawa_barat.csv`](adm4_codes/jawa_barat.csv)
> - `adm4_code` is Indonesia's administrative area code down to the village level.
> See the full reference: [Kode Wilayah Administrasi Pemerintahan seluruh Indonesia](https://m.nomor.net/_kodepos.php?_i=kode-wilayah).

logs output is written in `logs/`.

---

## Architecture Overview

This project is split into four layers that form a linear pipeline:
**extract → transform → load → runner**. Each layer is loosely coupled through
[Protocols](src/core/models/protocols.py), which define the boundaries between them and make the pipeline easier to test.

### Extract Layer

The extract layer lives in [`src/core/etl/extract.py`](src/core/etl/extract.py).

Extract layer has the responsibility to make HTTP requests using [`httpx`](https://www.python-httpx.org/), it then validates the incoming BMKG API data using [`Pydantic`](https://pydantic.dev/docs/validation) — invalid forecast entries are silently skipped, and an error is raised only if the entire response is unusable. Validation and model conversion happen lazily via an async iterable: data is yielded one item at a time, with `await asyncio.sleep(0)` inserted after each yield to cooperate with the event loop.

The layer also includes a retry mechanism to handle the inherent fragility of HTTP requests. Any failure that isn't a `404` will trigger a configurable number of retries, each separated by a delay.

Five class-level constants control this behavior:

```bash
BASE_URL              # base URL of the BMKG weather forecast API
REQUEST_TIMEOUT       # seconds before an unresponsive request is cancelled
RETRY_MAX_ATTEMPT     # maximum number of retry attempts on failure
RETRY_DELAY           # delay between each retry attempt
RATE_LIMITED_BACKOFF  # default backoff value when rate limited
```

### Transform Layer

The transform layer lives in [`src/core/etl/transform.py`](src/core/etl/transform.py)

This layer receives data from the extract layer. It loops over the iterable forecast data and converts each location and forecast entry into a [dataclass](src/core/models/domain_model.py) — the pipeline's
own domain model.

This conversion translates the [Pydantic data model](src/core/models/raw_model.py) into a more semantic internal
representation, containing only what the pipeline actually needs.

The transformation happens lazily — results are yielded as an `AsyncIterable`, so each entry is transformed only when consumed by the load layer.

### Load Layer

The load layer lives in [`src/core/etl/load.py`](src/core/etl/load.py).

This layer receives an `AsyncIterable` from the **transform** layer and iterates over it, loading each record into the database. It uses `PostgreSQL` through [Neon serverless postgres](https://neon.com/docs/introduction/serverless) as the cloud storage and [`SQLAlchemy Core`](https://docs.sqlalchemy.org/en/20/core/) to interact with `PostgreSQL` through Python objects rather than raw SQL strings.

Data is modeled using a star schema, producing two tables:

```bash
weather_forecast   # fact table — contains weather forecast data produced by the pipeline
forecast_location  # dimension table — contains location data for each forecast
```

The load layer uses upsert logic: `ON CONFLICT DO NOTHING` for `forecast_location` and `ON CONFLICT DO UPDATE` for `weather_forecast`. The `ON CONFLICT DO NOTHING` strategy for `forecast_location` is intentional — location data from the API rarely changes, so silently skipping duplicates is the safe choice.

### Runner Layer

The runner layer lives in [`src/core/runner.py`](src/core/runner.py)

This layer has the responsibility to run the `etl` in batch, it uses `asyncio.create_task()` to run each single adm4_code task concurrently, `with asyncio.Semaphore()` to limit the concurrency and `asyncio.sleep()` to add delays between each task creation to respect the API rate limit.

### Additional Layer

This project also includes a helper layer, [`src/core/db_balancer.py`](src/core/db_balancer.py), responsible for keeping database size under control by pruning stale data from the `weather_forecast` table.

`db_balancer` deletes any `weather_forecast` rows whose `forecast_datetime` has already passed relative to the ETL run time. Since forecasts for past timestamps are no longer useful, this prevents the table from growing unbounded over time.

---

## Running Tests

### Running Full Tests

With a note, this includes integration tests in [`tests/test_loader.py`](tests/test_loader.py) and [`tests/test_db_balancer.py`](tests/test_db_balancer.py)

```bash
pytest tests/
```

### Running Non-Integration Tests Only

```bash
pytest -m "not integration" tests/
```

### Running Integration Tests Only

```bash
pytest -m "integration" tests/
```

---

### Run with systemd

You can run the pipeline unattended on a VPS or server using a systemd service and timer. The service defines *what* to run, and the timer defines *when* (every 4 hours).

> **Prerequisite:** complete the [Installation](#installation) steps first.

#### 1. Create the service unit

```bash
sudo nano /etc/systemd/system/indo-weather-etl.service
```

Paste the following:

```ini
[Unit]
Description=Indo Weather ETL - a BMKG weather forecast data pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=your_username
WorkingDirectory=/path/to/indo-weather-etl
ExecStart=/path/to/indo-weather-etl/.venv/bin/run_etl
Restart=on-failure
RestartSec=30
```

Then replace:

- `/path/to/indo-weather-etl` with the **absolute** path to the project (systemd requires absolute paths in `ExecStart`)

- `your_username` with the user that owns the project

Save with `Ctrl+O`, `Enter`, then exit with `Ctrl+X`.

#### 2. Create the timer unit

```bash
sudo nano /etc/systemd/system/indo-weather-etl.timer
```

Paste the following:

```ini
[Unit]
Description=Run indo-weather-etl every 4 hours

[Timer]
OnCalendar=*-*-* 00/4:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

This runs the service every 4 hours (00:00, 04:00, 08:00, ...). `Persistent=true` makes systemd run a missed job after downtime, such as a reboot.

Save and exit the same way.

#### 3. Enable the timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now indo-weather-etl.timer
```

`enable` makes the timer start on boot, and `--now` starts it immediately.

#### 4. Verify

Trigger one run manually and check the logs:

```bash
sudo systemctl start indo-weather-etl.service
journalctl -u indo-weather-etl.service -n 50
```

Confirm the next scheduled run:

```bash
systemctl list-timers indo-weather-etl.timer
```

---
