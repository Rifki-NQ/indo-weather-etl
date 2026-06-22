# indo-weather-etl

An ETL Pipeline designed to extract data from public weather forecast API provided by [BMKG](https://data.bmkg.go.id/prakiraan-cuaca/), tranform the extracted data then load it into local storage using sqlite3

---

## Architecture Overview

This project is split into three layers:

### Extract Layer

The extract layer lives in [`src/core/extract.py`](src/core/extract.py).

It validates incoming BMKG API data using Pydantic — invalid forecast entries are silently skipped, and an error is raised only if the entire response is unusable. Validation and model conversion happen lazily via an async iterable: data is yielded one item at a time, with `await asyncio.sleep(0)` inserted after each yield to cooperate with the event loop.

The layer also includes a retry mechanism to handle the inherent fragility of HTTP requests. Any failure that isn't a `404` will trigger a configurable number of retries, each separated by a delay.

Five class-level constants control this behavior:

```bash
BASE_URL             # base URL of the BMKG weather forecast API
REQUEST_TIMEOUT      # seconds before an unresponsive request is cancelled
REQUEST_DELAY        # delay between successive requests
RETRY_MAX_ATTEMPT    # maximum number of retry attempts on failure
RETRY_DELAY          # delay between each retry attempt
```

---
