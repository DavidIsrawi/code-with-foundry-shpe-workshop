## Part 4 - Step 3: Load Instructions and a Welcome Banner from MCP

The agent works, but it still sounds like a generic assistant. The
Arepa Lab defines how its agent should behave - registration, vouchers,
order confirmation, and allergy guidance - and it doesn't want every
developer to copy-paste the latest version of that persona into their
code. So those instructions live on the **server**, not in your repo.

MCP servers can expose **prompts** - reusable text snippets curated by
the server owner. When the persona changes, the server updates; your
code keeps working without a redeploy. Arepa Lab exposes two:

- **agent_instructions** - the canonical agent conversation instructions
- **welcome_banner** - a friendly greeting to print at startup

Fetch both from the server, pass 'agent_instructions' to the 'Agent', and
print the banner before the chat starts.

```python-notype
"""Arepa Lab - The arepa ordering agent."""

import asyncio
import os
from urllib.parse import urlsplit

from dotenv import load_dotenv

from agent_framework import Agent, MCPStreamableHTTPTool  
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

    # 3. Connect to the Arepa Lab MCP server
    mcp_tool = MCPStreamableHTTPTool(
        name="arepa-lab",
        url=os.environ.get("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp/"),
    )
    await mcp_tool.connect()

    # 4. Get the instructions and welcome banner from the MCP server   👈 new
    instructions = await mcp_tool.get_prompt("agent_instructions")
    banner = await mcp_tool.get_prompt("welcome_banner")

    # 5. Create the agent
    agent = Agent(
        client=chat_client,
        name="arepa-lab-agent",
        instructions=instructions,                                     # 👈 new
        tools=mcp_tool,
    )

    # 6. Start a chat session and talk to the agent
    session = agent.create_session()
    print(banner)                                                      # 👈 new
    print("Type 'exit' to quit.\n")

    # Kick things off automatically                                    👈 new
    response = await agent.run("hello", session=session)
    print(f"\033[1;35mAssistant:\033[0m\n{response.text}\n")

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

The agent now also kicks off the conversation itself by sending a 'hello',
so the user sees the persona greet them right away.

**Run it:**

Back in the VS Code terminal at the bottom of the editor, run:

```bash
python agent.py
```

**Try it:** Ask for a **test arepa order** first.

Send `I'd like to place a test arepa order.` to the agent.

1. Reuse your customer ID, or give your first name, last name, and city to
   `register_customer`. Save the returned eight-character `customer_id`.
2. Choose an arepa from the live menu and explicitly confirm `kind="test"`.
3. Enter the **current six-character voucher** shown on the room's
   `/dashboard`. Both test and real orders require it. `ArepasAtSHPE`
   is the training key, not this voucher.
4. The test order completes immediately without consuming stock. It is
   not a pickup order and is not returned by `check_order_status`.
5. Only if you want a real arepa and the facilitator is ready, explicitly
   confirm `kind="real"` with the current voucher. A real order consumes
   one unit; each customer ID has a lifetime limit of one real order.
6. Use `check_order_status(customer_id)` or watch the room's dashboard
   for your active real order. Follow the facilitator's pickup instructions
   when staff mark it ready.

`cancel_order(customer_id, kind)` works only on pending orders. Cancelling
a pending real order restores stock and your real-order allowance; completed
test orders cannot be cancelled. If a voucher expires, read the current
dashboard code and retry with it. Do not guess a code or create another
customer ID to bypass the real-order limit.

Type 'exit' when you're done to stop the agent.

---

✅ **In this step you have:** built a Hello World agent, connected it to
the Arepa Lab MCP server for tools, loaded its persona and welcome
banner from MCP prompts, and placed a test arepa order.

➡️ Click **Next** for the recap and ideas on where to go from here.
