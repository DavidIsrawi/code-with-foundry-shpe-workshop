# V0 client-to-MCP end-to-end tests

These suites exercise the current workshop reference client and an actual
Streamable HTTP MCP server backed by real Azurite tables. They do not mock
Foundry or MCP responses.

## Setup

Use Python 3.12 or later, a local checkout of `arepa-mcp`, and Azurite:

```bash
npm install -g azurite
python -m venv .venv
.venv/bin/python -m pip install -r tests/e2e/requirements.txt
```

The server also needs its own Python environment with its
`requirements.txt` installed. Keep it separate from the client environment.
Pass that environment's Python executable through `--server-python`.

For the agent suite, configure the three `FOUNDRY_*` variables in
`workshop/sample-code/.env`, an alternative `--env-file`, or the calling
environment. Use an approved Foundry deployment. Never commit populated
environment files or keys. Running this suite makes billable model calls.

## Regression command

From the client repository:

```bash
.venv/bin/python tests/e2e/run.py --suite all \
  --server-repo ../arepa-mcp \
  --server-python ../arepa-mcp/.venv/bin/python
```

Run this after changes to either checkout. The runner uses local files, including
uncommitted changes; it does not clone, check out branches, commit, or deploy.
It can also be invoked by absolute path from the server repository or another
working directory. `--server-repo` defaults to the sibling `arepa-mcp` folder.
`--server-python` defaults to the interpreter running the test runner; specify
it when the server dependencies live in another environment.

Two suites are available:

| Suite | Purpose | Requires Foundry |
| --- | --- | --- |
| `--suite contract` | Deterministic tests using the workshop's real `MCPStreamableHTTPTool` adapter | No |
| `--suite agent` | A scripted terminal conversation through `workshop/sample-code/agent.py` and its real model | Yes |
| `--suite all` | Both suites; the default and the complete v0 regression gate | Yes |

Missing tools, dependencies, credentials, startup errors, omitted tool calls,
and assertion failures produce a nonzero exit. There is no automatic fallback
to mocked responses, silent credential skip, or rerunning failed scenarios. If Foundry is
unavailable, run the contract suite and report the agent suite as blocked,
not as a passing full regression.

## V0 coverage

The deterministic customer journey explicitly calls all six MCP tools. Other
cases verify:

- Tool discovery, required arguments, behavior annotations, and both server prompts.
- Registration normalization, accented names, invalid input, and unknown IDs.
- Test orders that auto-complete without changing inventory or allowance.
- Real orders with exact stock and allowance assertions, duplicate rejection,
  pending cancellation, and protection against repeated refunds.
- Pending, ready, and collected states; rejection of ready-order cancellation
  and enforcement of the lifetime real-order limit.
- Every qualitative stock threshold, sold-out menu filtering, and rejected
  sold-out orders leaving no active order.
- Voucher timing and failed-attempt throttling shared between REST and MCP.
- REST registration/order placement followed by cancellation through MCP.

The model-backed suite runs the reference client's actual `main()` function.
It supplies terminal input and observes the real MCP adapter without replacing
the agent, model client, server prompts, or HTTP calls. The conversation covers
registration, menu refresh, an invalid voucher, voucher timing, test ordering,
real ordering, status, cancellation, reordering, and ready/collected transitions.
It requires actual calls to all six tools, checks their arguments and results,
and independently checks the stored records. Fluent agent text cannot substitute
for a missing tool call. The conversation has a five-minute timeout.

There is no separate test-only agent implementation. Model assertions concern tool behavior and state,
not exact prose. The scripted conversation explicitly supplies the requested
action and complete fixture data; it is an integration check, not a broad
evaluation of conversational quality or safety.

The suite supports both endpoint protocols used by the reference client:
Claude's Anthropic API and the OpenAI Responses API for GPT deployments.
Configure `FOUNDRY_ENDPOINT` with the appropriate `/anthropic`, `/openai/v1`,
or Foundry project (`.../api/projects/<project>`) endpoint.

## Isolation and diagnostics

Each suite starts its own server and Azurite processes on available loopback
ports, with new local storage and generated session/admin/voucher secrets.
The runner never accepts a hosted MCP URL and does not use your existing
storage connection string. Synthetic fixture customers and food are the only
data sent to the model. Tests can place real-style orders only in this isolated
database.

The server interpreter is used for read-only storage snapshots so inventory
checks verify exact quantities rather than relying on qualitative menu labels.
Fixture creation and staff transitions go through the real admin HTTP routes.
All fixture processes are stopped on success or failure; unrelated running
services are left alone.

Ignored `.e2e-artifacts/<run-id>/` directories retain:

- `summary.json` with suite status, failures, errors, and skipped-test detection.
- Server and emulator logs for each suite.
- Actual tool-call arguments/results for contract cases.
- The model conversation transcript and tool trace.
- The isolated Azurite data for diagnosis.

Keep these local artifacts private. They contain synthetic customer IDs and
short-lived fixture voucher codes, and must not be committed.

The existing offline checks remain separate and need no services or model key:

```bash
python -m unittest discover -s tests -v
```

V0 does not claim concurrency guarantees, crash recovery, automatic stock
reconciliation after ambiguous writes, or browser-level dashboard coverage.
