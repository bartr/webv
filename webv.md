# Web Validate (WebV) — Features

Web Validate (WebV) is a web request validation tool for running end-to-end tests and long-running performance and availability tests against web APIs.

## Core Capabilities

- JSON API validation — purpose-built for testing JSON web APIs with deep validation of arbitrary result graphs
- YAML-based test definitions — author validation tests in human-friendly YAML
- Deep / nested validation — validate nested JSON objects, arrays, and trees to arbitrary depth
- End-to-end testing — run functional tests as part of CI/CD pipelines
- Performance & availability testing — execute long-running tests to monitor latency, health, and service status
- Test-in-production — run geo-distributed tests 24x7 from multiple regions to track usage and performance over time

## Execution Modes

- Default mode — processes input file(s) sequentially one time, then exits
- Run-loop mode (`--run-loop`) — runs continuously in a loop until stopped or for a specified `--duration`
- Dry-run mode (`--dry-run`) — validates and displays parameter values without executing tests
- Randomized requests (`--random`) — randomize request order in run-loop mode
- Configurable delay & sleep — `--delay-start` to defer test start; `--sleep` to throttle between requests
- Multi-threaded load — specify the same server multiple times to run parallel threads in a single instance

## Validation Checks

- Status code — validate HTTP status code (100–599; default 200)
- Content type — validate HTTP Content-Type / MIME type (default application/json)
- Content length — exact `length`, or `minLength` / `maxLength` bounds
- Response time — `maxMilliSeconds` maximum request duration
- Exact match — body exactly matches an expected value
- Contains / not contains — case-sensitive string presence and negated presence checks
- JSON array validation
  - `count`, `minCount`, `maxCount` of items
  - `byIndex` — validate an object at a specific array index
  - `forAny` — pass if any item in the array matches
  - `forEach` — validate every item in the array
- JSON object validation — check fields exist, match expected values, and recurse into nested objects
- Fail-fast control — `failOnValidationError` per request causes immediate test failure

## Test File Features

- YAML-based validation test files define requests and expected results
- Per-request configuration: `path`, `verb` (HTTP verbs), `testName`, `tag`, and `validation` rules
- Custom request bodies — send a request `body` with a configurable `contentMediaType`
- Custom request headers — attach arbitrary HTTP headers per request
- Environment variable substitution — inject `${VARIABLE_NAME}` values into test files at runtime (declared in the `variables` list)
- Human-friendly YAML syntax — comments, anchors, and case-insensitive property names supported
- HTTP redirects are not followed; all string comparisons are case-sensitive

## Performance Targeting

- Categorize results for performance reporting and trend analysis

## Observability & Monitoring

- Structured logging — logs published to stdout/stderr (`TsvMin`, `Tsv`, `Json`, `None` formats)
  - JSON output is camelCased by default
  - Default log format is `Tsv` in run-once mode and `Json` in run-loop (`--run-loop`) mode
- Prometheus metrics — `/metrics` endpoint exposed in run-loop mode for scraping
- Health endpoints — `/healthz` and `/readyz` exposed in run-loop mode for liveness/readiness checks
- Version endpoint — `/version` exposed in run-loop mode returns the semver string (matches `--version` output, no whitespace)
- Single pane of glass — compare server errors vs. client errors via centralized logging and metrics
- Log forwarding — integrates with Fluent Bit and existing log infrastructure
- Grafana dashboards — example dashboards for visualizing results
- User-defined metadata — `--tag`, `--region`, and `--zone` to distinguish instances/locations in logs
- Test summaries — output summary as `Tsv`, `Json`, or `Xml` (JUnit format)

### Per-Request Log Fields

Emitted for every executed request (one record per request).

| Field | Type | Description |
| --- | --- | --- |
| `type` | string | Record type; always `request` |
| `date` | ISO-8601 timestamp | UTC time the request started |
| `server` | string | Target server URL |
| `verb` | string | HTTP verb (default `GET`) |
| `path` | string | Request path |
| `testName` | string | Test name (used for grouping) |
| `statusCode` | int | HTTP response status code |
| `duration` | number (ms) | Request duration in milliseconds |
| `contentLength` | long | Response body length in bytes |
| `failed` | bool | True if the request failed (network / status outside expected range) |
| `validated` | bool | True if the response passed validation |
| `errorCount` | int | Number of validation errors for this request |
| `errors` | string[] | Validation error messages (only when `--verbose-errors`) |
| `category` | string | Performance category (`-` if unset) |
| `quartile` | int (1–4) | Performance quartile (`-` if unset) |
| `tag` | string | User-defined `--tag` value (`-` if unset) |
| `region` | string | User-defined `--region` value (`-` if unset) |
| `zone` | string | User-defined `--zone` value (`-` if unset) |

TSV column order: `date`, `testName`, `server`, `statusCode`, `errorCount`, `duration`, `contentLength`, `region`, `zone`, `tag`, `quartile`, `category`, `verb`, `path`.

`TsvMin` omits the trailing metadata columns for compact output; `None` suppresses per-request logging entirely.

### Summary Log Fields

Emitted once at the end of a run-once test when `--summary` is set.

| Field | Type | Description |
| --- | --- | --- |
| `totalRequests` | int | Total requests executed |
| `validationErrorCount` | int | Total validation errors |
| `failedRequests` | int | Total requests that failed |
| `successfulRequests` | int | Total requests that succeeded |
| `durationMs` | number | Wall-clock duration of the run (ms) |
| `startTime` / `endTime` | ISO-8601 timestamp | Run start and end (UTC) |

`Xml` summary output follows the [JUnit](https://llg.cubic.org/docs/junit/) schema for CI test reporting.

### Prometheus Metrics

Exposed on `/metrics` only when `--run-loop` is set. Labels `region` and `zone` are added when the corresponding CLI flag / env var is non-empty.

| Metric | Type | Labels | Description |
| --- | --- | --- | --- |
| `WebVDuration` | Histogram | `status`, `server`, `failed` (+ optional `region`, `zone`) | Request duration distribution (ms). Exponential buckets starting at 1 ms, factor 2, 10 buckets. |
| `WebVSummary` | Summary | `status`, `server`, `failed` (+ optional `region`, `zone`) | Request duration quantiles (φ = 0.9, 0.95, 0.99, 1.0) with a 5-minute sliding window. |

Standard process and runtime metrics exposed by the Prometheus client library in use are also exported.


## CI/CD Integration

- Returns a non-zero exit code on failure, suitable for pipeline gating:
  - Test file parse errors
  - Unhandled exceptions during a test
  - `--max-errors` threshold exceeded (default 10; set to 1 to fail on any error)
  - Any validation error on a request with `FailOnValidationError` set to `true`
- JUnit XML summary output for integration with CI test reporting

## Configuration

- Configurable via both command-line options and environment variables (CLI flags take precedence)
- Short flags available for common parameters
- Built-in `--help` / `-h` and `--version` commands

### Required Parameters

| Option | Short | Env var | Description |
| --- | --- | --- | --- |
| `--server` | `-s` | `SERVER` | Server URL(s) to test (one or more; repeat to fan out parallel threads) |
| `--files` | `-f` | `FILES` | One or more YAML test files (default location: current directory) |

### Common Parameters

| Option | Short | Env var | Default | Description |
| --- | --- | --- | --- | --- |
| `--dry-run` | `-d` | — | `false` | Validate and display parameter values without executing tests |
| `--delay-start` | — | `DELAY_START` | `0` | Delay starting the test (seconds) |
| `--log-format` | `-g` | `LOG_FORMAT` | `Tsv` (run-once), `Json` (run-loop) | Log format: `TsvMin`, `Tsv`, `Json`, `None` (conflicts with `--verbose`) |
| `--max-errors` | — | `MAX_ERRORS` | `10` | End test after N validation errors (ignored with `--run-loop`); exits non-zero when exceeded |
| `--region` | — | `REGION` | _empty_ | Deployment region for logging (user-defined) |
| `--zone` | — | `ZONE` | _empty_ | Deployment zone for logging (user-defined) |
| `--tag` | — | `TAG` | _empty_ | User-defined tag included in logs (e.g., instance / location) |
| `--sleep` | `-l` | `SLEEP` | `0` (`1000` with `--run-loop`) | Milliseconds to sleep between requests |
| `--summary` | — | `SUMMARY` | `None` | Test summary format: `None`, `Tsv`, `Json`, `Xml` (JUnit) |
| `--timeout` | `-t` | `TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `--url-prefix` | `-u` | `URL_PREFIX` | _empty_ | Prefix prepended to every request path |
| `--verbose` | `-v` | `VERBOSE` | `false` | Log 2xx/3xx results as well as errors |
| `--verbose-errors` | — | `VERBOSE_ERRORS` | `false` | Display validation error messages |

### Run-Loop Mode Parameters

Valid only when `--run-loop` is set (some defaults also change in this mode):

| Option | Short | Env var | Default | Description |
| --- | --- | --- | --- | --- |
| `--run-loop` | `-r` | `RUN_LOOP` | `false` | Run tests continuously in a loop |
| `--duration` | — | `DURATION` | `0` (until OS signal) | Run for N seconds, then exit |
| `--random` | — | `RANDOM` | `false` | Randomize request order |
| `--port` | `-p` | `PORT` | `8080` | Port for web endpoints (`/metrics`, `/healthz`, `/readyz`, `/version`); 0 < port < 64K |

### Informational

| Option | Short | Description |
| --- | --- | --- |
| `--help` | `-h` | Show help and exit |
| `--version` | — | Show version and exit |

## Run-Loop Lifecycle & Graceful Shutdown

- In run-loop mode the process registers handlers for `SIGINT` (Ctrl-C) and `SIGTERM` and shuts down cleanly.
- On signal:
  1. Stop accepting new request iterations (drain the loop).
  2. Wait for the in-flight HTTP request to complete (bounded by `--timeout`).
  3. Stop the web listener — `/metrics`, `/healthz`, `/readyz`, and `/version` continue serving until the listener is stopped, so an orchestrator can observe a final scrape.
  4. Flush summary / logs to stdout / stderr.
  5. Exit `0` on clean shutdown; non-zero only if `--max-errors` semantics applied.
- Graceful shutdown is bounded by a deadline (default 30 s); if exceeded, the process force-exits to avoid hangs in container orchestrators.

## Implementation

- Implementation language is unconstrained; pick a modern, statically-typed choice that produces a self-contained binary. The CLI surface, log formats, metrics, and endpoints above are the contract.
- YAML parsing must accept comments and treat property names case-insensitively.
- Environment-variable substitution (`${NAME}`) is resolved at test-file load time.

## Build

- Single command produces a self-contained executable for the host platform:

  ```bash
  ./build
  ```

- Targets Linux, WSL, macOS; shells: bash and zsh.
- Output: `./bin/webv` (statically linked where the toolchain supports it; no runtime dependency on a system framework).
- A `./build --release` flag produces a stripped, optimized binary tagged with the current semver.
- `./build --image vX.Y.Z` builds and tags the container image (see Docker section).

## Docker

- Multi-stage `Dockerfile`:
  - **Stage 1 (`builder`)** — pulls toolchain, fetches dependencies, builds the `webv` binary with reproducible flags.
  - **Stage 2 (`runtime`)** — minimal base (`gcr.io/distroless/static-debian12:nonroot` or `scratch`); copies only the `webv` binary.
- Security defaults baked into the image:
  - Runs as non-root (`USER 65532:65532`).
  - No shell, no package manager, no writable layers beyond `/tests` and `/tmp`.
  - `ENTRYPOINT ["/webv"]`; no `CMD` shell form.
  - Image is built with pinned digests for base images and dependencies; built artifacts are reproducible.
  - Image is scanned (e.g., `trivy`, `grype`) in the build script; build fails on HIGH/CRITICAL CVEs.
- Image tag matches the semver, e.g., `webv:0.1.0`, `webv:0.2.0`, plus `webv:latest`.
- Test files live on a replaceable volume mounted **read-only** at `/tests`:
  - `WORKDIR /tests` and the default container command runs with `--files <file>` resolved against `/tests`.
  - Swap test suites by mounting a different host directory or named volume to `/tests` — no image rebuild required.
- Long-running deployment with Docker (hardened):

  ```bash
  docker run -d --name webv \
    --restart unless-stopped \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --pids-limit 256 \
    --memory 256m --cpus 0.5 \
    --user 65532:65532 \
    --tmpfs /tmp:rw,noexec,nosuid,size=16m \
    -p 8080:8080 \
    -v $PWD/tests:/tests:ro \
    webv:0.1.0 \
    --server https://example.com \
    --files smoke.yaml \
    --run-loop \
    --log-format Json
  ```

- Container honors `SIGTERM` for clean shutdown (see Run-Loop Lifecycle); `docker stop` works without `--time` overrides.

## Kubernetes (Kustomize)

All cluster manifests live under `./deploy/` and are **Kustomize-only** — no Helm charts, no `helm template` output, no `helm install`. Upstream projects (Prometheus, Grafana, Prometheus Operator CRDs) are vendored as plain YAML manifests pulled from their upstream release artifacts and composed with `kustomization.yaml`. Each component (the app and each observability tool) has its own directory so they can be applied independently.

### GitOps-ready layout

`./deploy/` is designed to plug into an org-wide Flux / GitOps repository without restructuring. The eventual layout inserts a `cluster-<name>/` directory immediately under `deploy/` so multiple clusters can be reconciled from one repo:

```text
deploy/
  lab01/
    webv/ …
    prometheus/ …
    grafana/ …
    servicemonitor-crd/ …
  tx-austin/
    …
```

Cluster names identify a location, lab, or fleet member — never a security tier. Mixing environments like `dev` and `prod` in the same GitOps repo is an anti-pattern because GitHub applies access control at the repo level, which would collapse their security contexts; keep separate environments in separate repos.

To keep that move trivial:

- Every component is its own self-contained Kustomization rooted at `deploy/<component>/` — nothing references paths outside its own directory, and no manifest hard-codes a cluster name.
- All resources are namespaced (`webv`, `monitoring`, etc.); cluster-scoped resources (CRDs, namespaces) live in their own component dir so a Flux `Kustomization` can target them independently.
- Cluster-specific values (hostnames, replica counts, ingress class, scrape intervals) are exposed as overlay-level patches — never baked into base manifests — so a future `cluster-<name>/` wrapper layer can patch them without touching the component dirs.
- `kustomization.yaml` files use relative paths only (`../base`, `./patches/...`); a future Flux `Kustomization` resource will point at `deploy/cluster-<name>/<component>` with no edits required to the component itself.

Until the `cluster-<name>/` layer is introduced, the current layout works directly with `kubectl apply -k` for single-cluster use.

```text
deploy/
  webv/
    base/
      kustomization.yaml
      namespace.yaml         # namespace: webv (with restricted PSA labels)
      deployment.yaml        # image: webv:latest; --run-loop; mounts /tests RO
      service.yaml           # ClusterIP, port 8080, named port `http`
      configmap-tests.yaml   # YAML test files mounted at /tests
      servicemonitor.yaml    # Prometheus Operator scrape of /metrics
      ingressroute.yaml      # Traefik IngressRoute for /metrics, /healthz, /readyz, /version
      networkpolicy.yaml     # default-deny + allow Prometheus, Traefik, DNS
    overlays/
      v0.1.0/
        kustomization.yaml   # images: [{ name: webv, newTag: 0.1.0 }]
      v0.2.0/
        kustomization.yaml   # images: [{ name: webv, newTag: 0.2.0 }]
  prometheus/                # latest upstream kube-prometheus / Prometheus Operator manifests
    kustomization.yaml
  grafana/                   # latest upstream Grafana manifests + WebV dashboards as ConfigMaps
    kustomization.yaml
  servicemonitor-crd/        # Prometheus Operator CRDs (ServiceMonitor, PodMonitor, etc.)
    kustomization.yaml
```

- `deploy/webv/base/` is a complete, self-contained Kustomization — it can be applied directly with `kubectl apply -k deploy/webv/base` and will deploy WebV using `webv:latest`.
- Overlays exist only to pin a specific semver (or apply version-specific patches); they do not add resources that the base is missing.
- Each `webv` overlay only overrides `newTag` (plus any version-specific patches); all shared resources live in `webv/base/`.
- Order of apply on a fresh cluster:
  1. `kubectl apply -k deploy/servicemonitor-crd`
  2. `kubectl apply -k deploy/prometheus`
  3. `kubectl apply -k deploy/grafana`
  4. `kubectl apply -k deploy/webv/base` _or_ `kubectl apply -k deploy/webv/overlays/v0.1.0`
- Test files are delivered via a `ConfigMap` mounted at `/tests`, so updating tests is `kubectl apply -k` of the base or an overlay — no image rebuild.

### Prometheus scraping

- Scraping is driven exclusively by a `ServiceMonitor` (no pod / service annotations).
- `ServiceMonitor` selects the WebV `Service` by label and targets the `http` port at path `/metrics`.
- Scrape interval `30s`, scrape timeout `10s`; honors `region` / `zone` labels emitted by the metrics.

### Ingress (Traefik)

- Uses the built-in Traefik shipped with k3s / k3d — no extra controller install.
- Exposed via a Traefik `IngressRoute` (CRD) for the WebV `Service`:
  - Host: `webv.local` (override per overlay)
  - Routes: `/metrics`, `/healthz`, `/readyz`, `/version`
  - TLS via Traefik's default certificate resolver; HTTP-to-HTTPS redirect middleware enabled.
  - Rate-limit and IP-allowlist middlewares applied to `/metrics` to prevent unauthenticated scraping from outside the cluster.
- Grafana and Prometheus get their own `IngressRoute` objects with basic-auth middleware.

### Security defaults (Kubernetes)

Deployment spec follows Pod Security Standards `restricted` profile:

- `runAsNonRoot: true`, `runAsUser: 65532`, `runAsGroup: 65532`, `fsGroup: 65532`.
- `readOnlyRootFilesystem: true`; writable `emptyDir` mounted at `/tmp` only if needed.
- `allowPrivilegeEscalation: false`; `capabilities.drop: ["ALL"]`.
- `seccompProfile.type: RuntimeDefault`.
- `automountServiceAccountToken: false` and a dedicated `ServiceAccount` with no RBAC bindings.
- Resource `requests` and `limits` set for CPU and memory; `terminationGracePeriodSeconds: 60`.
- `livenessProbe` → `GET /healthz`; `readinessProbe` → `GET /readyz`; `startupProbe` for slow-start safety.
- `NetworkPolicy` default-denies all ingress/egress, then allows:
  - Ingress from the Traefik and Prometheus namespaces on port `8080`.
  - Egress to kube-dns and to the configured `--server` target(s).
- Images referenced by digest (`webv@sha256:...`) in production overlays.
- Namespace labeled with `pod-security.kubernetes.io/enforce: restricted`.

## Local Development & Testing

- **CLI** — built binary runs directly: `./bin/webv --server https://example.com --files tests/smoke.yaml`.
- **Local Kubernetes** — target a `k3d` or `k3s` cluster (built-in Traefik provides ingress):

  ```bash
  k3d cluster create webv -p "80:80@loadbalancer" -p "443:443@loadbalancer"
  ./build --image 0.1.0
  k3d image import webv:0.1.0 -c webv

  kubectl apply -k deploy/servicemonitor-crd
  kubectl apply -k deploy/prometheus
  kubectl apply -k deploy/grafana
  kubectl apply -k deploy/webv/overlays/v0.1.0
  ```

- Same image and manifests deploy to upstream Kubernetes; only the ingress class / TLS resolver differs if Traefik is not the cluster ingress.
