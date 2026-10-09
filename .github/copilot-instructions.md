# Copilot Instructions

## Architecture and data flow
- This is a small permutation flow shop web app: [app.py](../app.py) serves the page and owns the FastAPI routes; Docker exposes it on `127.0.0.1:8080`.
- `GET /api/examples` lists bundled TXT files. `POST /api/solve` accepts multipart form fields and is dispatched by [solve.py](../src/backend/endpoints/solve.py).
- The solve path reads a bundled example or temporary upload, parses the instance and permutation, runs the selected calculation/search, and returns JSON for the browser. Keep file handling and algorithm logic in their existing backend modules.
- The browser is plain HTML, CSS, and JavaScript under [src/frontend](../src/frontend/index.html), served at `/static`; it submits `FormData` and renders the returned result and search history.
- `PRODUCT.md` records the student-facing purpose and constraints; keep visible copy in Spanish and retain the compact, inspectable UI.

## Flow shop and algorithms
- [flowshop.py](../src/backend/flowshop.py) implements `F[k,j] = max(F[k-1,j], F[k,j-1]) + d[k,j]`. `cmax` is the maximum final-machine completion; `fmax` is the average completion time on the final machine.
- [instance.py](../src/backend/instance.py) parses `n m` followed by one row per job with zero-based `(machine, duration)` pairs. Jobs in user sequences are numbered from 1.
- [sequence.py](../src/backend/sequence.py) validates a complete permutation or generates one when the input is empty. Preserve this convention when changing parsing or UI sequence controls.
- [local_search.py](../src/backend/local_search.py) owns local-search strategies (`best`, `first`, `random`), moves (`swap`, `2opt`), and bounded neighbor evaluation. `max_neighbors=0` means the full neighborhood; prefix cutoffs skip candidates that cannot improve the objective.
- [metaheuristics.py](../src/backend/metaheuristics.py) implements random search and simulated annealing. Optional annealing refinement is dispatched in `solve.py` through local search.
- Search results feed the history UI in `index.js`: preserve `method`, `objective`, `initial_metrics`, `final_metrics`, `iterations`, `max_iterations`, `evaluations`, `evaluation_label`, and `stop_reason`; method-specific settings and refinement details are also displayed.

## API and UI contracts
- When adding or changing a search option, update the FastAPI form signature in `app.py`, the argument flow and validation in `solve.py`, the control in `index.html`, and serialization/validation in `index.js` together.
- The submit button distinguishes direct calculation from search via `event.submitter`; keep both actions in the same form and preserve their button types/IDs.
- `calculate_flowshop` returns `rows` in sequence order, plus `sequence`, `cmax`, and `fmax`. Do not assume matrix rows are sorted by job number.
- Static asset URLs in `index.html` carry a `?v=` cache key. Bump it when changing frontend JS or CSS so browsers load the updated asset.

## Validation and tests
- TXT input is UTF-8 (BOM accepted), limited to 1 MiB and 10,000 operations; rows must list machines in order with non-negative integer durations. Keep HTTP validation errors specific and return them as `HTTPException` from the API boundary.
- Tests use the standard-library `unittest`. [test_app.py](../src/tst/test_app.py) tests parsing, sequence validation, bundled examples, and calculation; [flow_shop_test.py](../src/tst/flow_shop_test.py) contains reference fixtures.
- VS Code discovers only `test_*.py` in `src/tst` (see `.vscode/settings.json`). Run: `python -m unittest discover -s src/tst -p "test_*.py"`.

## Developer workflow
- Install dependencies with `python -m pip install -r requirements.txt`.
- Run locally with `python -m uvicorn app:app --reload --host 127.0.0.1 --port 8080`.
- Build and start the container with `docker compose up --build -d`; stop it with `docker compose down`. Compose intentionally publishes only on loopback; preserve that binding unless the deployment requirement changes.
