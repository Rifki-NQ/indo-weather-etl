# indo-weather-etl

An ETL Pipeline designed to extract data from public weather forecast API provided by [BMKG](https://data.bmkg.go.id/prakiraan-cuaca/), tranform the extracted data then load it into local storage using sqlite3

---

## Architecture Overview

This project is split into three layers that form a linear pipeline:
**extract → transform → load**. Each layer is loosely coupled through
[Protocols](src/core/models/protocols.py), which define the boundaries between them and make the pipeline easier to test.

### Extract Layer

The extract layer lives in [`src/core/extract.py`](src/core/extract.py).

It validates incoming BMKG API data using [Pydantic](src/core/models/raw_model.py) — invalid forecast entries are silently skipped, and an error is raised only if the entire response is unusable. Validation and model conversion happen lazily via an async iterable: data is yielded one item at a time, with `await asyncio.sleep(0)` inserted after each yield to cooperate with the event loop.

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

This conversion translates the [Pydantic](src/core/transform.py) data model into a more semantic internal
representation, containing only what the pipeline actually needs.

The transformation happens lazily — results are yielded as an `AsyncIterable`, so each entry is transformed only when consumed by the load layer.

### Load Layer

The load layer lives in [`src/core/load.py`](src/core/load.py).

This layer receives an `AsyncIterable` from the **transform** layer and iterates over it, loading each record into the database. It uses `sqlite3` for local disk storage and `SQLAlchemy Core` to interact with SQLite through Python objects rather than raw SQL strings.

Data is modeled using a star schema, producing two tables:

```bash
weather_forecast   # fact table — contains weather forecast data produced by the pipeline
forecast_location  # dimension table — contains location data for each forecast
```

The load layer uses upsert logic: `INSERT OR IGNORE` for `forecast_location` and `INSERT OR REPLACE` for `weather_forecast`. The `INSERT OR IGNORE` strategy for `forecast_location` is intentional — location data from the API rarely changes, so silently skipping duplicates is the safe choice.

---
