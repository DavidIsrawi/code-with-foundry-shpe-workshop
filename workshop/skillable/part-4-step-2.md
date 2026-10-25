## Part 4 - Step 2: Connect to the Arepa Lab MCP Server

A chatbot that only chats is just an expensive parrot. To actually *do*
things - list in-stock arepas, place an order, check its status - the
agent needs **tools**. Staff, not the client, mark real orders ready for pickup.

> **What is MCP?** The **Model Context Protocol** is an open standard
> for letting AI agents talk to external systems. An MCP server publishes
> a set of tools (functions the agent can call), prompts (reusable
> instruction snippets), and resources (data) over HTTP. Your agent just
> needs the URL - the framework handles discovery and invocation.
> Arepa Lab uses **Streamable HTTP**, not the legacy SSE transport.

Two changes to your 'agent.py':

1. Import 'MCPStreamableHTTPTool', read the server URL from 'MCP_SERVER_URL', and call 'connect()'.
2. Pass it to the 'Agent' via 'tools='.

The agent will discover the available tools automatically and decide when
to call them based on what you ask.

The tools are `register_customer(first_name, last_name, city)`,
`list_arepas()`, `order_arepa(flavor_id, customer_id, kind, voucher_code)`,
`check_order_status(customer_id)`, `cancel_order(customer_id, kind)`, and
`voucher_status()`. There are no legacy tool aliases.

`list_arepas()` returns only in-stock items with `id`, `name`, `description`,
`price` (USD), `stock_status`, and `stock_label`. Stock statuses are `plenty`,
`limited`, and `almost_finished`; do not infer exact inventory. Use the
returned item's `id` as `flavor_id` when ordering. The fields `flavor_id`,
`flavor`, and `flavor_name` have not been renamed. The menu HTTP route is
`GET /arepas`; the client connects to `/mcp/`, not the menu route.

```python-notype
"""Arepa Lab - The arepa ordering agent."""

import asyncio
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

from agent_framework import Agent, MCPStreamableHTTPTool   # 👈 updated
from agent_framework.foundry import AnthropicFoundryClient
from agent_framework.openai import OpenAIChatClient

# 1. Load environment variables from .env
load_dotenv()

async def main() -> None:
    # 2. Select the protocol advertised by the Foundry endpoint
    endpoint = urlsplit(os.environ["FOUNDRY_ENDPOINT"].rstrip("/"))
    if "/api/projects/" in endpoint.path and not endpoint.path.endswith("/openai/v1"):
        endpoint = endpoint._replace(path=endpoint.path + "/openai/v1")
    client_type = OpenAIChatClient if endpoint.path.endswith("/openai/v1") else AnthropicFoundryClient
    chat_client = client_type(
        model=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],
        api_key=os.environ["FOUNDRY_API_KEY"],
        base_url=endpoint.geturl(),
    )

    # 3. Connect to the Arepa Lab MCP server                    👈 new
    mcp_tool = MCPStreamableHTTPTool(
        name="arepa-lab",
        url=os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp/"),
    )
    await mcp_tool.connect()

    # 4. Create the agent
    agent = Agent(
        client=chat_client,
        name="arepa-lab-agent",
        tools=mcp_tool,                                          # 👈 new
    )

    # 5. Start a chat session and talk to the agent
    session = agent.create_session()
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("\033[1;35mYou:\033[0m\n")
        if user_input.lower() in ("exit", "quit"):
            break

        response = await agent.run(user_input, session=session)
        print(f"\n\033[1;35mAssistant:\033[0m\n{response.text}\n")

    await mcp_tool.close()


if __name__ == "__main__":
    asyncio.run(main())
```

Make sure you save the program after pasting in the code. If you see a ⚫️ next to the file in VS Code, that mean's it's not yet saved. You can use File > Save or your standard keyboard shortcut for saving.

**Run it:**

In the VS Code terminal at the bottom of the editor, run:

```bash
python agent.py
```

**Try it:**

Send the message `What arepas do you have today?` to the agent.

Do *not* order an arepa yet! This step is just to confirm that the agent can call the MCP tools to list available arepas and their stock labels. You'll place a test order in the next step.

Type 'exit' when you're done to stop the agent.

The agent is now calling MCP tools on the Arepa Lab server. But it's
still acting like a generic assistant - it has no persona yet.

---

✅ **In this step you have:** connected your agent to the Arepa Lab
MCP server, and watched it call live tools to answer arepa
questions.

➡️ Click **Next** to give the agent its persona and welcome banner.
