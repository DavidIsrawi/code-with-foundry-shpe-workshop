# arepa-lab-agent

Your working folder for the workshop. You build the **Arepa Lab** arepa-ordering agent here, step by step, by following [`../workshop/workshop.md`](../workshop/workshop.md).

## Contents

- `agent.py` - Empty starter. You fill this in during the workshop.
- `requirements.txt` - Python dependencies (`agent-framework`, `agent-framework-foundry`, `agent-framework-openai`, `python-dotenv`).
- `.env.sample` - Copy to `.env`, then fill in your Foundry endpoint, API key, and deployment name. Set `MCP_SERVER_URL` to the facilitator-provided Arepa Lab endpoint, or run the server locally at the sample URL. The workshop demo MCP endpoint needs no authentication.

## Run

```bash
cp .env.sample .env
pip install -r requirements.txt
python agent.py
```

Keep your populated `.env` local; it is ignored by Git. The starter only
contains a docstring until you complete the lab steps. To run the finished
agent instead, use [`../workshop/sample-code/`](../workshop/sample-code/).
