# indo-weather-etl

An ETL Pipeline designed to extract data from public weather forecast API provided by [BMKG](https://data.bmkg.go.id/prakiraan-cuaca/), tranform the extracted data then load it into Postgresql

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

## Usage

Run the pipeline with:

```bash
weather --adm4 <adm4_code>
```

> `adm4_code` is Indonesia's administrative area code down to the village level.
> See the full reference: [Kode Wilayah Administrasi Pemerintahan seluruh Indonesia](https://m.nomor.net/_kodepos.php?_i=kode-wilayah).

Output is written to `database/`, with logs in `logs/`.

---

## Architecture Overview

This project is split into three layers that form a linear pipeline:
**extract → transform → load**. Each layer is loosely coupled through
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

This layer receives an `AsyncIterable` from the **transform** layer and iterates over it, loading each record into the database. It uses `Postgresql` through [Neon serverless postgres](https://neon.com/docs/introduction/serverless) as the cloud storage and [`SQLAlchemy Core`](https://docs.sqlalchemy.org/en/20/core/) to interact with `Postgresql` through Python objects rather than raw SQL strings.

Data is modeled using a star schema, producing two tables:

```bash
weather_forecast   # fact table — contains weather forecast data produced by the pipeline
forecast_location  # dimension table — contains location data for each forecast
```

The load layer uses upsert logic: `INSERT OR IGNORE` for `forecast_location` and `INSERT OR UPDATE` for `weather_forecast`. The `INSERT OR IGNORE` strategy for `forecast_location` is intentional — location data from the API rarely changes, so silently skipping duplicates is the safe choice.

---

## Running Tests

```bash
pytest tests/
```

---
