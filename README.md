# indo-weather-etl

An ETL Pipeline designed to extract data from public weather forecast API provided by [BMKG](https://data.bmkg.go.id/prakiraan-cuaca/), transform the extracted data then load it into PostgreSQL

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

The extract layer lives in [`src/core/extract.py`](src/core/extract.py).

Extract layer has the responsibility to make HTTP requests using [`httpx`](https://www.python-httpx.org/), it then validates the incoming BMKG API data using [`Pydantic`](https://pydantic.dev/docs/validation) — invalid forecast entries are silently skipped, and an error is raised only if the entire response is unusable. Validation and model conversion happen lazily via an async iterable: data is yielded one item at a time, with `await asyncio.sleep(0)` inserted after each yield to cooperate with the event loop.

The layer also includes a retry mechanism to handle the inherent fragility of HTTP requests. Any failure that isn't a `404` will trigger a configurable number of retries, each separated by a delay.

Five class-level constants control this behavior:

```bash
BASE_URL             # base URL of the BMKG weather forecast API
REQUEST_TIMEOUT      # seconds before an unresponsive request is cancelled
REQUEST_DELAY        # delay between successive requests
RETRY_MAX_ATTEMPT    # maximum number of retry attempts on failure
RETRY_DELAY          # delay between each retry attempt
```

### Transform Layer

The transform layer lives in [`src/core/transform.py`](src/core/transform.py)

This layer receives data from the extract layer. It loops over the iterable forecast data and converts each location and forecast entry into a [dataclass](src/core/models/domain_model.py) — the pipeline's
own domain model.

This conversion translates the [Pydantic data model](src/core/models/raw_model.py) into a more semantic internal
representation, containing only what the pipeline actually needs.

The transformation happens lazily — results are yielded as an `AsyncIterable`, so each entry is transformed only when consumed by the load layer.

### Load Layer

The load layer lives in [`src/core/load.py`](src/core/load.py).

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

---

## Running Tests

### Running Full Tests

With a note, this includes integration test in [`tests/test_loader.py`](tests/test_loader.py)

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
