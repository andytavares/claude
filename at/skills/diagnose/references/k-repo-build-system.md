# k-repo Build System Reference

## Pipeline

- **Org/Pipeline slug**: `klaviyo-ci/k-repo`
- **Build system**: Pants (monorepo)
- **CI**: Buildkite

## Key bk CLI Commands

```bash
# View a build (get job list)
bk build view <build-num> -p klaviyo-ci/k-repo --json

# Get a job's logs
bk job log <job-uuid> -p klaviyo-ci/k-repo -b <build-num> --no-timestamps

# List artifacts for a build
bk artifacts list <build-num> -p klaviyo-ci/k-repo

# Download a specific artifact (must cd to target dir first)
cd /tmp/investigation && bk artifacts download <artifact-id> -p klaviyo-ci/k-repo --build <build-num>
```

## Key gh CLI Commands

```bash
# Get PR details and changed files
gh pr view <PR-num> --repo klaviyo/k-repo --json title,body,files,baseRefName,headRefName

# Get PR check statuses with build URLs
gh pr checks <PR-num> --repo klaviyo/k-repo

# Extract build number from check URL
# URLs look like: https://buildkite.com/klaviyo-ci/k-repo/builds/129213
```

## Build Artifacts (from "Setup pipeline" job)

| Artifact path | Contents | Use |
|---|---|---|
| `dist.docker/targets` | All pants targets in the changeset (one per line) | Quick count of total targets |
| `dist.docker/stats.jsonl` | Pants run stats + changeset command used | Shows `--changed-since` command |
| `dist.docker/peek.json.gz` | Full dependency graph for changeset targets | BFS/path analysis |

To download all three:
```bash
mkdir -p /tmp/investigation
cd /tmp/investigation

# List artifacts to find IDs
bk artifacts list <build-num> -p klaviyo-ci/k-repo

# Download by artifact ID
bk artifacts download <id-for-targets> -p klaviyo-ci/k-repo --build <build-num>
bk artifacts download <id-for-stats> -p klaviyo-ci/k-repo --build <build-num>
bk artifacts download <id-for-peek-gz> -p klaviyo-ci/k-repo --build <build-num>

# Decompress peek
gunzip -k dist.docker/peek.json.gz
```

## Standard Build Job Names

| Job name | Step key | What it does |
|---|---|---|
| `Setup pipeline` | `setup` | Runs `pants --changed-since`, computes changeset, generates pipeline |
| `Python Tests` | — | Runs pytest on changed python_test targets |
| `Tests on Python3.12` | — | Same on 3.12 |
| `Lint` | — | Ruff/flake8 |
| `Typecheck` | — | Pyright/mypy |
| `Docker build and publish AMD images` | — | Builds docker_image targets (AMD) |
| `Docker build and publish ARM images` | — | Builds docker_image targets (ARM) |
| `Compare Generated Targets` | `compare_targets` | Compares changeset vs baseline (often soft-fails) |

## Changeset Computation (from Setup pipeline log)

The setup job logs show exactly what happened:

```
INFO:...build_changeset_v2:Number of top level targets: 4
INFO:...dependency_graph:Computed transitive dependents for 4 targets: 1903 dependents found
INFO:...build_changeset_v2:Complete changeset built: 4 targets + 1903 dependents = 1905 total
```

Key log lines to grep for:
- `"Number of top level targets"` — directly changed targets
- `"Computed transitive dependents"` — blast radius
- `"Complete changeset built"` — summary
- `"Building dependency graph from"` — total graph size

## peek.json Structure

Each entry in the array:
```json
{
  "address": "python/klaviyo/foo/bar.py",
  "target_type": "python_source",
  "dependencies": ["python/klaviyo/baz/__init__.py", "3rdparty/python#pydantic"],
  "description": "",
  "files": [...],
  "goals": [...],
  "output_path": "...",
  "packages": [...],
  "tags": [...]
}
```

**Note**: peek.json only contains targets in the changeset, not the full repo graph. The `dependencies` field is the forward dependency list (what this target needs), which you invert to get reverse deps (what depends on this target).

## Target Types

| Type | Meaning |
|---|---|
| `python_source` | Individual `.py` file |
| `python_sources` | Group of `.py` files |
| `python_test` | Individual test file |
| `python_tests` | Group of test files |
| `pex_binary` | Compiled Python executable |
| `docker_image` | Docker image build target |
| `python_distribution` | PyPI-style distribution |
| `resource` | Non-code resource (YAML, JSON, etc.) |
| `file` / `files` | Raw file targets |

## Common Root Causes for Large Blasts

1. **Resource bundled on a core library** — A `resources()` target containing data files wired as a dependency of a widely-imported library. Any data file change cascades through everything. Look for `python_sources(dependencies=[":some_resource"])` in BUILD files.

2. **Shared conftest** — Changes to `python/conftest.py` or `python/conftest.py:test_utils` invalidate every test in the repo.

3. **Third-party version bump** — A `3rdparty/python` requirement change cascades to everything using that package.

4. **Proto/schema change** — Protobuf or OpenAPI schema changes cascade to all generated code consumers.

## How to Read a BUILD File Connection

If pants says `protocol.py` depends on `foo.yml`, check the BUILD file in `protocol.py`'s directory:

```python
# If you see this:
resources(name="yaml_configuration", sources=["yaml_/**/*"])
python_sources(dependencies=[":yaml_configuration"])

# It means: EVERY .py in this dir inherits a dep on EVERY yaml_ file.
# The connection is in BUILD, not in the Python import.
```
