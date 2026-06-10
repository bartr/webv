# Product Requirements Document (PRD) — Web Validate (WebV) CLI

## Overview

Web Validate (WebV) is a command-line tool for validating HTTP/JSON web APIs. It runs declarative, YAML-defined HTTP tests against one or more target servers and reports validation results. WebV operates in two primary modes:

1. **Run-once mode** — executes test files sequentially one time, emits results and an optional summary, then exits with a status code suitable for CI/CD gating.
2. **Run-loop mode** — runs continuously (or for a bounded duration) to support long-running availability and performance testing, exposing Prometheus metrics, health, readiness, and version HTTP endpoints for orchestrator and observability integration.

The deliverable is a single self-contained executable plus a hardened container image and a Kustomize-based Kubernetes deployment under `./deploy/`. The implementation language is unconstrained; the CLI surface, log/summary formats, Prometheus metrics, HTTP endpoints, exit-code semantics, and deployment artifacts described here are the contract.

## Purpose

- **Problem solved.** Teams need a single tool that (a) validates web API responses deeply (status, content type, headers, body shape, JSON structure) for end-to-end CI tests, and (b) runs the same tests continuously in production to monitor availability and performance — without maintaining two separate tools or test definitions.
- **Users.**
  - **Service / API developers** authoring functional tests for CI/CD pipelines.
  - **SRE / platform engineers** running 24x7 in-cluster availability and synthetic-traffic tests.
  - **Quality / release engineers** gating releases on JUnit-compatible test reports.
- **Value.** One declarative YAML test definition drives both CI gating and in-production monitoring; integrates with existing Prometheus / Grafana / Fluent Bit stacks; deploys via GitOps-friendly Kustomize manifests.

## Functional Requirements

### Core CLI behavior

1. WebV MUST accept test definitions from one or more YAML test files specified via `--files` / `-f` / `FILES`.
2. WebV MUST send HTTP requests to one or more servers specified via `--server` / `-s` / `SERVER`. Specifying the same server multiple times MUST spawn parallel threads against that server within a single process instance.
3. WebV MUST support both run-once mode (default) and run-loop mode (`--run-loop` / `-r` / `RUN_LOOP`).
4. WebV MUST support a `--dry-run` / `-d` mode that validates configuration and parameter values without executing any HTTP requests.
5. WebV MUST resolve `${VARIABLE_NAME}` placeholders in test files against the process environment at test-file load time. Placeholders MUST be declared in a `variables` list within the test file.
6. WebV MUST treat YAML property names case-insensitively and MUST accept YAML comments.
7. WebV MUST NOT follow HTTP redirects. All string comparisons in validation rules MUST be case-sensitive.
8. CLI flags MUST take precedence over environment variables for any setting that supports both.

### Per-request configuration (test file)

9. Each request in a test file MUST support: `path`, `verb` (HTTP verb), `testName`, `tag`, `body`, `contentMediaType`, `headers` (key/value map), `validation` (validation rules), and `failOnValidationError` (bool).
10. The default `verb` MUST be `GET`.
11. The default `contentMediaType` MUST be `application/json`.
12. Setting `failOnValidationError: true` on a request MUST cause WebV to exit with a non-zero status as soon as that request fails validation (immediate failure, regardless of `--max-errors`).

### Validation rules

13. WebV MUST support validating: `statusCode` (100–599; default 200), HTTP `contentType` (default `application/json`), content `length` / `minLength` / `maxLength`, `maxMilliSeconds` response time, `exactMatch` body, `contains` / `notContains` substring checks (case-sensitive).
14. WebV MUST support JSON array validation: `count`, `minCount`, `maxCount`, `byIndex` (validate object at a specific index), `forAny` (any item matches), and `forEach` (every item matches).
15. WebV MUST support JSON object validation: presence of fields, exact-value matches, and recursive validation into nested objects.

### Execution modes and pacing

16. `--delay-start` / `DELAY_START` (default `0`) MUST delay the start of test execution by N seconds.
17. `--sleep` / `-l` / `SLEEP` MUST insert N milliseconds between requests. Default `0` in run-once; default `1000` in run-loop mode.
18. `--duration` / `DURATION` (run-loop only; default `0` = until OS signal) MUST cause WebV to exit cleanly after N seconds.
19. `--random` / `RANDOM` (run-loop only; default `false`) MUST randomize request order.
20. `--timeout` / `-t` / `TIMEOUT` (default `30` seconds; minimum `1`) MUST bound the duration of any single HTTP request.
21. `--max-errors` / `MAX_ERRORS` (default `10`) MUST end the test with a non-zero exit code once exceeded. MUST be ignored when `--run-loop` is set.
22. `--url-prefix` / `-u` / `URL_PREFIX` MUST be prepended to every request `path` at execution time.

### Logging

23. WebV MUST support log formats `TsvMin`, `Tsv`, `Json`, `None` selected via `--log-format` / `-g` / `LOG_FORMAT`.
24. The default log format MUST be `Tsv` in run-once mode and `Json` in run-loop mode.
25. `Json` log output MUST use camelCase field names.
26. `--log-format None` MUST conflict with `--verbose` and produce a parse error.
27. WebV MUST emit one log record per executed request with the fields listed in **Per-Request Log Fields** below.
28. `--verbose` / `-v` / `VERBOSE` (default `false`) MUST cause 2xx/3xx results to be logged in addition to errors.
29. `--verbose-errors` / `VERBOSE_ERRORS` (default `false`) MUST include validation error messages in the per-request log.
30. `--tag` / `TAG`, `--region` / `REGION`, and `--zone` / `ZONE` MUST be included in per-request log records when set.

### Summary output

31. `--summary` / `SUMMARY` MUST produce an end-of-run summary in one of `None` (default), `Tsv`, `Json`, or `Xml`.
32. `Xml` summary output MUST conform to the JUnit XML schema for CI test reporting.
33. The summary MUST include the fields listed in **Summary Log Fields** below.

### Run-loop mode HTTP endpoints

34. When `--run-loop` is set, WebV MUST expose an HTTP listener on `--port` / `-p` / `PORT` (default `8080`; valid range `0 < port < 64K`) serving four endpoints: `/metrics`, `/healthz`, `/readyz`, `/version`.
35. `/version` MUST return the same semver string as `--version` with no surrounding whitespace.
36. `/healthz` MUST return HTTP 200 while the process is running and the loop has not been signaled to stop.
37. `/readyz` MUST return HTTP 200 only after `--delay-start` has elapsed and the first iteration has begun, and MUST return non-2xx during graceful shutdown.
38. `/metrics` MUST expose Prometheus metrics in the standard Prometheus text exposition format.

### Prometheus metrics

39. WebV MUST publish the metrics listed in **Prometheus Metrics** below on `/metrics`. Labels `region` and `zone` MUST be added to each metric only when the corresponding CLI flag / env var is non-empty.
40. WebV MUST also export standard process and runtime metrics as exposed by the Prometheus client library in use.

### Run-loop lifecycle and graceful shutdown

41. In run-loop mode, WebV MUST register handlers for `SIGINT` and `SIGTERM` and perform a graceful shutdown.
42. Graceful shutdown MUST: (a) stop accepting new request iterations; (b) wait for the in-flight HTTP request to complete (bounded by `--timeout`); (c) keep `/metrics`, `/healthz`, `/readyz`, `/version` serving until the listener is stopped so a final scrape is possible; (d) flush logs and summary to stdout/stderr; (e) stop the HTTP listener; (f) exit with status `0` for a clean shutdown.
43. Graceful shutdown MUST be bounded by a deadline (default `30` seconds); if exceeded, the process MUST force-exit to avoid orchestrator hangs.

### Exit codes (CI/CD gating)

44. WebV MUST exit with a non-zero status code when any of the following occurs:
    - Test file parse error.
    - Unhandled exception during a test.
    - `--max-errors` threshold exceeded (run-once only).
    - Any validation error on a request with `failOnValidationError: true`.

### Build

45. Running `./build` from the repository root MUST produce a self-contained executable at `./bin/webv` on Linux, WSL, and macOS, under bash and zsh shells, with no required runtime framework on the target host.
46. `./build --release` MUST produce a stripped, optimized binary tagged with the current semver.
47. `./build --image vX.Y.Z` MUST build and tag the container image as `webv:X.Y.Z` (see Container).

### Container

48. The container MUST be produced from a multi-stage `Dockerfile`: a `builder` stage that compiles the binary with reproducible flags, and a `runtime` stage based on `gcr.io/distroless/static-debian12:nonroot` (or `scratch`).
49. The runtime image MUST contain only the `webv` binary, MUST run as non-root (`USER 65532:65532`), and MUST declare `ENTRYPOINT ["/webv"]` (no shell-form `CMD`).
50. Base images and toolchain dependencies MUST be pinned by digest; the build MUST be reproducible.
51. The build script MUST scan the produced image for HIGH/CRITICAL CVEs (e.g., `trivy` or `grype`) and fail on any.
52. Test files MUST be mounted read-only at `/tests`. The container `WORKDIR` MUST be `/tests` and `--files` MUST resolve relative paths against `/tests`. Swapping test suites by remounting `/tests` MUST NOT require an image rebuild.
53. The container MUST honor `SIGTERM` so that `docker stop` performs a clean shutdown without `--time` overrides.
54. Image tags MUST follow semver (e.g., `webv:0.1.0`, `webv:0.2.0`) and additionally publish `webv:latest`.

### Kubernetes deployment (Kustomize)

55. All cluster manifests MUST live under `./deploy/` and MUST be Kustomize-only. Helm charts, `helm template` output, and `helm install` MUST NOT be used. Upstream projects (Prometheus, Grafana, Prometheus Operator CRDs) MUST be vendored as plain YAML and composed via `kustomization.yaml`.
56. The directory layout MUST be:
    - `deploy/webv/base/` — self-contained Kustomization that deploys WebV with `webv:latest`.
    - `deploy/webv/overlays/v0.1.0/`, `deploy/webv/overlays/v0.2.0/`, … — overlays that only pin `newTag` (and any version-specific patches).
    - `deploy/prometheus/` — vendored upstream Prometheus / Prometheus Operator manifests.
    - `deploy/grafana/` — vendored upstream Grafana manifests plus WebV dashboards as ConfigMaps.
    - `deploy/servicemonitor-crd/` — Prometheus Operator CRDs.
57. `kubectl apply -k deploy/webv/base` MUST deploy a fully functional WebV instance without requiring any overlay.
58. Each component MUST be its own self-contained Kustomization; no `kustomization.yaml` may reference paths outside its own component directory; no manifest may hard-code a cluster name.
59. All cluster-specific values (hostnames, replica counts, ingress class, scrape intervals) MUST be exposed as overlay patches — never baked into a base manifest — so a future `cluster-<name>/` wrapper layer can patch them without editing the component.
60. Prometheus scraping of WebV MUST be driven exclusively by a `ServiceMonitor` resource (no pod / service scrape annotations). The `ServiceMonitor` MUST select the WebV `Service` by label and target the `http` port at path `/metrics` with scrape interval `30s` and timeout `10s`.
61. Ingress MUST use the built-in Traefik shipped with k3s / k3d via a Traefik `IngressRoute` CRD. The `IngressRoute` MUST expose `/metrics`, `/healthz`, `/readyz`, and `/version`; `/metrics` MUST be protected by rate-limit and IP-allowlist middlewares.
62. Grafana and Prometheus MUST each have their own `IngressRoute` protected by basic-auth middleware.
63. The WebV `Deployment` spec MUST conform to Pod Security Standards `restricted`, including: `runAsNonRoot: true`, `runAsUser: 65532`, `runAsGroup: 65532`, `fsGroup: 65532`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`, `seccompProfile.type: RuntimeDefault`, `automountServiceAccountToken: false`, a dedicated `ServiceAccount` with no RBAC bindings, explicit CPU and memory `requests` and `limits`, `terminationGracePeriodSeconds: 60`, and `livenessProbe` / `readinessProbe` / `startupProbe` against `/healthz` and `/readyz`.
64. A default-deny `NetworkPolicy` MUST be present and MUST allow only: ingress from the Traefik and Prometheus namespaces on port `8080`, and egress to kube-dns and configured `--server` target(s).
65. Production overlays MUST reference the image by digest (`webv@sha256:...`).
66. The `webv` namespace MUST be labeled `pod-security.kubernetes.io/enforce: restricted`.

## API Endpoints

Exposed by the WebV process only when `--run-loop` is set, on `--port` (default `8080`).

- `/metrics` — Prometheus text-format metrics scrape endpoint. Includes `WebVDuration` (Histogram) and `WebVSummary` (Summary) plus standard process / runtime metrics from the Prometheus client library.
- `/healthz` — Liveness probe. Returns HTTP 200 while the process is alive; non-2xx during force-exit.
- `/readyz` — Readiness probe. Returns HTTP 200 once `--delay-start` has elapsed and the first iteration has begun; non-2xx during graceful shutdown so the orchestrator stops sending traffic.
- `/version` — Returns the WebV semver string (matching `--version` output) with no surrounding whitespace.

## User Stories

- As a **service developer**, I want to declare HTTP API tests in YAML and run them in CI, so that pull requests fail fast when a response contract regresses.
- As a **release engineer**, I want WebV to produce JUnit XML output and a non-zero exit code on failure, so that my CI system reports test results and gates releases.
- As an **SRE**, I want WebV to run continuously in Kubernetes and expose Prometheus metrics, health, and readiness endpoints, so that I can monitor synthetic traffic and let the orchestrator manage its lifecycle.
- As a **platform engineer**, I want WebV to ship as a hardened, non-root, read-only-rootfs container with Kustomize manifests, so that it can be deployed via GitOps into a `restricted` Pod Security namespace without modifications.
- As a **performance engineer**, I want to run multiple parallel threads against the same target and get duration histograms and quantiles per `(status, server, failed[, region, zone])`, so that I can characterize tail latency over time.
- As a **multi-region tester**, I want to label each WebV instance with `--region` and `--zone`, so that logs and metrics distinguish results by location.
- As a **fleet operator**, I want a `deploy/` tree that can later be wrapped in a `cluster-<name>/` directory for Flux, so that adopting GitOps does not require restructuring component manifests.

## Per-Request Log Fields

One record per executed request.

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

TSV column order MUST be: `date`, `testName`, `server`, `statusCode`, `errorCount`, `duration`, `contentLength`, `region`, `zone`, `tag`, `quartile`, `category`, `verb`, `path`. `TsvMin` MUST omit the trailing metadata columns. `None` MUST suppress per-request logging entirely.

## Summary Log Fields

Emitted once at end-of-run when `--summary` is set (run-once mode).

| Field | Type | Description |
| --- | --- | --- |
| `totalRequests` | int | Total requests executed |
| `validationErrorCount` | int | Total validation errors |
| `failedRequests` | int | Total requests that failed |
| `successfulRequests` | int | Total requests that succeeded |
| `durationMs` | number | Wall-clock duration of the run (ms) |
| `startTime` / `endTime` | ISO-8601 timestamp | Run start and end (UTC) |

## Prometheus Metrics

Exposed on `/metrics` only when `--run-loop` is set.

| Metric | Type | Labels | Description |
| --- | --- | --- | --- |
| `WebVDuration` | Histogram | `status`, `server`, `failed` (+ optional `region`, `zone`) | Request duration distribution (ms). Exponential buckets starting at 1 ms, factor 2, 10 buckets. |
| `WebVSummary` | Summary | `status`, `server`, `failed` (+ optional `region`, `zone`) | Request duration quantiles (φ = 0.9, 0.95, 0.99, 1.0) with a 5-minute sliding window. |

## CLI Parameter Reference

### Required

| Option | Short | Env var | Description |
| --- | --- | --- | --- |
| `--server` | `-s` | `SERVER` | Server URL(s) to test (one or more; repeat to fan out parallel threads) |
| `--files` | `-f` | `FILES` | One or more YAML test files (default location: current directory) |

### Common

| Option | Short | Env var | Default | Description |
| --- | --- | --- | --- | --- |
| `--dry-run` | `-d` | — | `false` | Validate and display parameter values without executing tests |
| `--delay-start` | — | `DELAY_START` | `0` | Delay starting the test (seconds) |
| `--log-format` | `-g` | `LOG_FORMAT` | `Tsv` (run-once), `Json` (run-loop) | `TsvMin`, `Tsv`, `Json`, `None` (conflicts with `--verbose`) |
| `--max-errors` | — | `MAX_ERRORS` | `10` | End test after N validation errors (ignored with `--run-loop`); non-zero exit when exceeded |
| `--region` | — | `REGION` | _empty_ | Deployment region for logging (user-defined) |
| `--zone` | — | `ZONE` | _empty_ | Deployment zone for logging (user-defined) |
| `--tag` | — | `TAG` | _empty_ | User-defined tag included in logs |
| `--sleep` | `-l` | `SLEEP` | `0` (`1000` with `--run-loop`) | Milliseconds to sleep between requests |
| `--summary` | — | `SUMMARY` | `None` | `None`, `Tsv`, `Json`, `Xml` (JUnit) |
| `--timeout` | `-t` | `TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `--url-prefix` | `-u` | `URL_PREFIX` | _empty_ | Prefix prepended to every request path |
| `--verbose` | `-v` | `VERBOSE` | `false` | Log 2xx/3xx results as well as errors |
| `--verbose-errors` | — | `VERBOSE_ERRORS` | `false` | Display validation error messages |

### Run-loop only

| Option | Short | Env var | Default | Description |
| --- | --- | --- | --- | --- |
| `--run-loop` | `-r` | `RUN_LOOP` | `false` | Run tests continuously in a loop |
| `--duration` | — | `DURATION` | `0` (until OS signal) | Run for N seconds, then exit |
| `--random` | — | `RANDOM` | `false` | Randomize request order |
| `--port` | `-p` | `PORT` | `8080` | Port for web endpoints; 0 < port < 64K |

### Informational

| Option | Short | Description |
| --- | --- | --- |
| `--help` | `-h` | Show help and exit |
| `--version` | — | Show version and exit |

## Non-Functional Requirements

### Implementation

- Implementation language is unconstrained. The chosen language MUST be modern and statically typed and MUST produce a self-contained binary with no required runtime framework on the target host. The contract is the CLI surface, log/summary formats, Prometheus metrics, HTTP endpoints, exit-code semantics, signal handling, and deployment artifacts defined in this PRD.
- The build MUST be reproducible: pinned dependency versions, pinned base-image digests, deterministic output.

### Performance

- Memory footprint of the running container SHOULD fit within a 256 MiB limit and 0.5 CPU under normal long-running workloads. The provided Docker reference command demonstrates this envelope.
- WebV MUST sustain parallel-thread execution against a single server (one thread per repeated `--server` value) without serializing requests through a single shared client.
- Per-request log emission MUST NOT block the request loop beyond synchronous stdout/stderr writes.

### Security

- The container MUST run as non-root (`UID 65532`), MUST drop all Linux capabilities, MUST set `no-new-privileges`, and MUST use a read-only root filesystem with only `/tmp` (tmpfs) and `/tests` (read-only mount) writable surfaces (and `/tests` is read-only at that).
- The container MUST contain no shell and no package manager (distroless or `scratch` base).
- The Kubernetes Deployment MUST satisfy Pod Security Standards `restricted` (see Functional Requirement 63).
- A default-deny `NetworkPolicy` MUST be present (Functional Requirement 64); production overlays MUST pin the image by digest (Functional Requirement 65).
- `/metrics` MUST NOT be exposed outside the cluster without rate-limit + IP-allowlist middleware (Functional Requirement 61). Grafana and Prometheus ingress MUST require basic-auth (Functional Requirement 62).
- WebV MUST NOT follow HTTP redirects (avoids accidental egress to unintended hosts).
- Image scanning MUST gate the build on HIGH/CRITICAL CVEs (Functional Requirement 51).

### Reliability

- Graceful shutdown MUST complete within a 30-second deadline; if exceeded, the process force-exits (Functional Requirement 43).
- The HTTP listener MUST remain available until the very end of graceful shutdown so a final Prometheus scrape can capture terminal state (Functional Requirement 42c).
- `--max-errors` MUST be ignored in run-loop mode (Functional Requirement 21) so transient target outages do not terminate a long-running synthetic monitor.

### Portability

- The build script MUST support Linux, WSL, and macOS hosts running bash or zsh (Functional Requirement 45).
- The container image MUST be runnable on any OCI-compatible runtime (Docker, containerd, CRI-O).
- The Kustomize manifests MUST apply cleanly to upstream Kubernetes; only the ingress class / TLS resolver may differ when Traefik is not the cluster ingress.

### Operability

- Logs MUST go to stdout/stderr (no log file management required) so existing log forwarders (e.g., Fluent Bit) can collect them.
- Metrics labels MUST include `region` and `zone` only when set, to keep cardinality bounded by default.
- The `deploy/` tree MUST be GitOps-friendly: self-contained per-component Kustomizations with relative paths only, namespaced resources, no hard-coded cluster names, cluster-specific values exposed only as overlay patches (Functional Requirements 58, 59).

### Compatibility

- JUnit XML summary output MUST be compatible with mainstream CI test reporters (per the JUnit schema reference).
- YAML parsing MUST tolerate comments and case-insensitive property names (Functional Requirement 6).

## Out of Scope

- **HTTP redirect following.** WebV will not follow 3xx redirects automatically.
- **Authentication helpers.** WebV does not bundle OAuth/OIDC token flows; auth is delivered via per-request headers or env-var substitution.
- **gRPC, WebSocket, or other non-HTTP/1.1+HTTP/2 protocols.**
- **Browser-driven end-to-end tests (Selenium/Playwright/etc.).** WebV is an HTTP-only client.
- **Test authoring UI.** Test files are authored in YAML in the user's editor of choice.
- **Built-in alerting.** Alerts are configured in Prometheus/Alertmanager, not in WebV.
- **In-cluster credential storage.** Secrets used by tests (via `${VAR}` substitution) must be supplied by the cluster via `Secret` env injection.
- **Helm charts** for any component under `./deploy/` (Functional Requirement 55).
- **A `cluster-<name>/` directory layer** under `./deploy/`. The structure is required to make adding it trivial in the future, but the initial deliverable does not include it.
- **A WebV management API** beyond `/metrics`, `/healthz`, `/readyz`, and `/version`.

## Acceptance Criteria

### CLI behavior

- [ ] `./bin/webv --version` prints a semver string and exits 0.
- [ ] `./bin/webv --help` prints all CLI options listed in the CLI Parameter Reference and exits 0.
- [ ] Run-once mode against a healthy server with a passing YAML test file exits 0 with no log records when `--verbose` is not set and no errors occur.
- [ ] Run-once mode exits non-zero on: a parse error in the YAML test file; an unhandled exception; `--max-errors` exceeded; any failing request that has `failOnValidationError: true`.
- [ ] `--dry-run` prints resolved parameters and exits without sending any HTTP requests.
- [ ] `${VAR}` placeholders in a test file are substituted from the environment at load time; missing variables are reported as a parse error.
- [ ] HTTP redirects are not followed (responses with 3xx status are reported as such, not transparently followed).
- [ ] CLI flag values override the corresponding environment-variable values.

### Validation engine

- [ ] All validation rules listed in Functional Requirements 13–15 produce the documented pass/fail behavior on hand-crafted fixtures, including nested object validation, `forAny`, `forEach`, and array `byIndex`.
- [ ] `failOnValidationError: true` on a failing request causes immediate non-zero exit even when other requests would still be queued.

### Logging and summary

- [ ] Default log format is `Tsv` in run-once mode and `Json` in run-loop mode.
- [ ] `--log-format Json` emits camelCase field names per the Per-Request Log Fields table.
- [ ] `--log-format None` combined with `--verbose` produces a parse error and non-zero exit.
- [ ] TSV column order matches the order specified in Per-Request Log Fields.
- [ ] `TsvMin` omits the trailing metadata columns.
- [ ] `--summary Xml` produces output that validates against the JUnit XML schema.
- [ ] `region` and `zone` are present in per-request log records when set, and absent (or `-` per TSV convention) when unset.

### Run-loop mode

- [ ] `/version` returns the same semver string as `--version` with no surrounding whitespace.
- [ ] `/healthz` returns HTTP 200 while the process is running.
- [ ] `/readyz` returns HTTP 200 only after the first iteration has begun.
- [ ] `/metrics` returns Prometheus text-format output including `WebVDuration` and `WebVSummary` with the labels specified.
- [ ] `region` and `zone` Prometheus labels appear only when the corresponding flag / env var is non-empty.
- [ ] On `SIGTERM` the process completes its in-flight request, keeps the HTTP listener serving until the final flush, then exits with status 0; total shutdown time does not exceed 30 seconds.

### Build

- [ ] `./build` produces an executable at `./bin/webv` on Linux, WSL, and macOS under bash and zsh.
- [ ] `./build --release` produces a stripped binary tagged with the current semver.
- [ ] `./build --image vX.Y.Z` produces a container image tagged `webv:X.Y.Z` and `webv:latest`.

### Container

- [ ] The image is multi-stage; the runtime stage contains only the `webv` binary on a distroless or `scratch` base.
- [ ] The container runs as `65532:65532`, declares `ENTRYPOINT ["/webv"]`, and contains no shell.
- [ ] The image build fails when an HIGH or CRITICAL CVE is detected by the configured scanner.
- [ ] `docker run --read-only --cap-drop ALL --security-opt no-new-privileges --user 65532:65532 -v $PWD/tests:/tests:ro webv:X.Y.Z --server <url> --files smoke.yaml --run-loop` runs successfully and exposes `/metrics`, `/healthz`, `/readyz`, `/version`.
- [ ] Swapping the mounted directory at `/tests` changes the test files used at next container start without requiring an image rebuild.
- [ ] `docker stop webv` returns within 30 seconds with no force-kill.

### Kubernetes

- [ ] `kubectl apply -k deploy/webv/base` on a fresh cluster with Prometheus, Grafana, and the ServiceMonitor CRDs already applied produces a running WebV pod with all probes passing.
- [ ] `kubectl apply -k deploy/webv/overlays/v0.1.0` deploys WebV pinned to image tag `0.1.0`; the only difference vs. base is `newTag`.
- [ ] No `kustomization.yaml` under `deploy/` references a path outside its own component directory.
- [ ] No manifest under `deploy/` hard-codes a cluster name.
- [ ] No Helm chart, `helm install`, or `helm template` invocation appears anywhere under `deploy/`.
- [ ] Prometheus scrapes WebV via the `ServiceMonitor` resource (verified via Prometheus `targets` page); no scrape annotations are present on the WebV `Service` or `Pod`.
- [ ] The WebV `IngressRoute` exposes `/metrics`, `/healthz`, `/readyz`, `/version` through the built-in Traefik in k3s/k3d, with rate-limit and IP-allowlist middleware applied to `/metrics`.
- [ ] Grafana and Prometheus `IngressRoute` objects require basic-auth.
- [ ] The WebV `Deployment` passes `kubectl auth can-i` and admission-controller checks for Pod Security Standards `restricted`.
- [ ] A `NetworkPolicy` exists in the `webv` namespace that default-denies and explicitly allows ingress from Traefik and Prometheus namespaces on port `8080`, plus egress to kube-dns and the configured target server(s).
- [ ] Production overlays reference the WebV image by digest (`webv@sha256:...`).
- [ ] The `webv` namespace carries the label `pod-security.kubernetes.io/enforce: restricted`.

### GitOps-readiness

- [ ] Inserting an arbitrary `deploy/cluster-<name>/` wrapper that points its Kustomization at `../webv/overlays/v0.1.0` (and similarly at `../prometheus`, `../grafana`, `../servicemonitor-crd`) reconciles successfully without modifying any file inside `deploy/webv/`, `deploy/prometheus/`, `deploy/grafana/`, or `deploy/servicemonitor-crd/`.

## Assumptions

- The target hosts for the binary have `glibc`-compatible or fully static linkage available, depending on the chosen language toolchain.
- The Kubernetes cluster used for in-cluster deployment is k3s/k3d (so Traefik ingress is built in) or a cluster where Traefik is the configured ingress controller. Other ingress controllers require an alternate overlay (out of scope here).
- The Prometheus Operator (with `ServiceMonitor` CRD) is installed in the cluster via the `deploy/servicemonitor-crd/` and `deploy/prometheus/` Kustomizations before applying `deploy/webv/base/`.
- "Latest upstream" manifests for Prometheus, Grafana, and the Operator CRDs are vendored into the repo at a known, pinned release version; updating them is a manual, reviewable change.
- Test files mounted into the container or referenced by the CLI are trusted; YAML parsing does not need to sandbox untrusted input.
- The build environment has Docker (or a compatible OCI builder) and a CVE scanner (`trivy` or `grype`) installed.
