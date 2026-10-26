# Regression checks

- Keep the reference client and final copy-paste lab snippets in sync.
- Run `python -m unittest discover -s tests -v` for offline workshop checks.
- After changes to client behavior, dependencies, MCP contracts, or the paired
  server, run `tests/e2e/run.py --suite all` with the client interpreter and the
  actual local server checkout/interpreter. See
  [the E2E setup and commands](tests/e2e/README.md).
- Both v0 suites must pass: the deterministic contract suite and the real
  Foundry-backed reference-agent conversation, each covering all seven tools.
- If model credentials or access are unavailable, run `--suite contract` and
  explicitly report the agent suite as blocked. Do not substitute mocks,
  silently skip it, or claim the full regression passed.
- Use the runner's isolated fixtures. Never point tests at a hosted workshop
  endpoint or existing customer/inventory data, and never commit `.env` files
  or `.e2e-artifacts/`.
