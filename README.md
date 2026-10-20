# Code with Claude - Microsoft Foundry Workshop

Build an AI agent with **Microsoft Foundry** and the **Microsoft Agent Framework** that uses a Claude model and calls tools through an MCP server.

## What you will build

![Arepa Lab logo](workshop/images/arepa-lab.svg)

An arepa-ordering agent for **Arepa Lab** at the **2026 SHPE National Convention**,
October 28–31, 2026, in Indianapolis, Indiana, that:

- Uses **Claude Sonnet 4.6** deployed in Microsoft Foundry
- Loads its persona and welcome banner from MCP **prompts**
- Calls live tools from the **Arepa Lab MCP server** over Streamable HTTP

**Workshop training key:** `ArepasAtSHPE`. This is a public access/display
value for the external training platform, not the rotating order voucher,
an MCP credential, or an admin password. External platform acceptance has
not been configured by this repository.

> **Microsoft Foundry** is Microsoft's hosted platform for deploying AI models (OpenAI, Anthropic, Mistral, and more) and exposing them via an endpoint and key.
>
> **MCP** (Model Context Protocol) is an open standard that lets agents discover and call tools, prompts, and resources from a remote server over HTTP.

## Repository layout

```
.
├── workshop/
│   ├── workshop.md              # Step-by-step lab manual
│   ├── skillable/               # Skillable lab instructions
│   └── sample-code/             # Final reference implementation
│       ├── agent.py
│       ├── requirements.txt
│       └── .env.sample
└── arepa-lab-agent/             # Your working folder for the workshop
    ├── .env.sample              # Copy to .env and fill in your settings
    ├── agent.py                 # Empty starter - you build it up during the workshop
    └── requirements.txt         # Python dependencies
```

## Prerequisites

- An Azure subscription with access to **Microsoft Foundry**
- A deployed Claude model (e.g. `claude-sonnet-4-6`)
- Python 3.10+
- A running Arepa Lab MCP server, locally or at an endpoint supplied by the facilitator

## Quick start

1. Follow the [workshop lab manual](workshop/workshop.md) to build the agent step-by-step in `arepa-lab-agent/`.
2. Or, to run the finished reference agent in [workshop/sample-code/](workshop/sample-code/) directly:

   ```bash
   cd workshop/sample-code
   pip install -r requirements.txt
   cp .env.sample .env   # then edit .env with the variables listed below
   python agent.py
   ```

## Environment variables

Copy `arepa-lab-agent/.env.sample` to `arepa-lab-agent/.env` for the starter,
or use the sample in `workshop/sample-code/` for the reference agent.
Keep populated `.env` files local; they are ignored by Git.

| Variable | Description |
| --- | --- |
| `FOUNDRY_ENDPOINT` | Target URI of your Foundry deployment, e.g. `https://<resource>.services.ai.azure.com/anthropic` |
| `FOUNDRY_API_KEY` | API key for the Foundry deployment |
| `FOUNDRY_MODEL_DEPLOYMENT` | Deployment name (e.g. `claude-sonnet-4-6`) |
| `MCP_SERVER_URL` | Arepa Lab Streamable HTTP endpoint; defaults to `http://127.0.0.1:8000/mcp/` |

The default MCP URL requires the server to run in the same machine/container
as the client. For a hosted lab or Codespace without a local server, use the
facilitator's confirmed endpoint, including `/mcp/`. The workshop demo MCP
endpoint has no authentication; the Foundry key is only for the model.
The rebranded hosted MCP deployment and workshop link are still pending;
no production hostname or short link is assumed here.

## Arepa Lab tool contract

The client discovers tools from the server rather than defining local aliases.
The server exposes exactly these tools:

| Tool | Arguments / behavior |
| --- | --- |
| `register_customer(first_name, last_name, city)` | Returns an eight-character `customer_id`. Reuse that ID. |
| `list_arepas()` | Returns only in-stock items with `id`, `name`, `description`, `price` (USD), `stock_status`, and `stock_label`. |
| `order_arepa(flavor_id, customer_id, kind, voucher_code)` | Use the selected item's `id` as `flavor_id`. `kind` is exactly `test` or `real`; both require the current six-character dashboard voucher. |
| `check_order_status(customer_id)` | Reports active real orders, not test orders. |
| `cancel_order(customer_id, kind)` | Pending orders only; cancelling a pending real order restores stock and the customer's real-order allowance. |
| `voucher_status()` | Reports voucher status; use the current code displayed on the dashboard when ordering. |

Stock statuses are `plenty`, `limited`, and `almost_finished`. Show the returned
labels, not invented inventory counts. Existing `flavor_id`, `flavor`, and
`flavor_name` fields keep their names. Test orders immediately complete without
consuming stock; real orders consume one unit and have a lifetime limit of one
real order per customer ID (unless a pending real order is cancelled).
Practice with `kind="test"`; place a real order only when explicitly intended.

The server's `agent_instructions` prompt is the canonical conversation guidance;
`welcome_banner` supplies terminal branding. The approved C2-B logo depicts
shredded beef and cheese as branding, not ingredients guaranteed for every item.
Menu details come from the server. The menu HTTP route is `GET /arepas`; `/mcp/`, `/orders`,
`/customers`, and `/dashboard` retain their generic paths.

## Offline checks

Run `python -m unittest discover -s tests -v` from the repository root.
These checks exercise the reference client and the copy-paste lab snippets
with mocked Foundry/MCP connections; they do not place orders or require keys.

## Troubleshooting

See the [Troubleshooting section](workshop/workshop.md#troubleshooting) of the workshop for common issues and fixes.
