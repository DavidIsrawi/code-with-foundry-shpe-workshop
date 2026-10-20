# Workshop: Build an AI Agent with Microsoft Foundry & Microsoft Agent Framework

Welcome to **Arepa Lab** at the **2026 SHPE National Convention**,
October 28–31, 2026, in Indianapolis, Indiana. Today you'll build an AI
agent that greets guests, shows the available arepas, registers customers,
and places orders through an MCP server.

**Workshop training key:** `ArepasAtSHPE`. This public access/display value
is for the external training platform, not the rotating order voucher,
an MCP credential, or an admin password. The facilitator still needs to
configure platform acceptance and supply the workshop link.

You'll start by logging in to **Microsoft Foundry**, where you'll meet
**Claude Sonnet** waiting for you in the Playground. After a quick chat
to make sure you two get along, you'll grab the deployment's endpoint and
key and bring them home to your code editor.

From there, you'll build the agent up one small step at a time using the
**Microsoft Agent Framework**. First, a bare-bones "hello world" agent
that proves you can reach the model. Next, you'll plug it into the
**Arepa Lab MCP server** so it gains tools for listing
flavors, checking stock, placing orders. Finally, you'll let the MCP
server hand the agent its own persona and welcome banner, turning a
generic chatbot into an Arepa Lab ordering assistant.

By the end, you'll have placed a test arepa order from an agent you built from
scratch - and learned how Foundry, the Agent Framework, and MCP fit
together along the way. A real order is optional and should only be placed
when you intend to pick it up.

**Prerequisites**
- Access to an Azure subscription with Microsoft Foundry
- Python 3.10+ installed
- This repository cloned locally (or opened in a Codespace)
- A running Arepa Lab MCP server, locally or at a confirmed endpoint supplied by the facilitator

> **What is Microsoft Foundry?** Foundry is Microsoft's hosted platform
> for shipping AI applications. It's where you deploy models (OpenAI,
> Anthropic, Mistral, your own fine-tunes), give them an endpoint and a
> key, and then wire them into your code. Think of it as the cloud
> control panel for the brains of your agent.



## Part 1 - Log in to Microsoft Foundry

1. Open <https://ai.azure.com> in your browser.
2. Sign in with the account provided for the workshop.
3. In the top bar, toggle the **New Foundry** switch on.
4. Your **project** is selected by default - no need to pick one.

![Foundry landing page with the New Foundry toggle on and the project selected](images/01-foundry-home.png)


## Part 2 - Find a Model and Test It

A quick word on vocabulary before you click around: a **model** (like
`claude-sonnet-4`) is the underlying AI. A **deployment** is your
personal, named instance of that model running in your project, with its
own endpoint, key, and rate limits. Your code talks to the *deployment
name*, not the model name - that's the bit you'll wire into your `.env`
in a moment.

1. In the top navigation, make sure **Build** is selected.
2. In the left-hand navigation, click **Models**.
3. On the **Deployments** tab you'll see all models deployed to this project.
   For this workshop, pick **`claude-sonnet-4-6`**.
   The **Name** column is the **deployment name** - you'll need it later.
4. Click the deployment - you'll land directly in the **Playground** and can
   chat with it right there.
![Deployed models](images/02-models-deployments.png)

5. Take a moment to explore the **Playground** - it's the fastest way to
   sanity-check a model before you wire it into code:

   - **Model** (top of the panel) - shows which deployment you're chatting
     with. You can switch deployments here without leaving the page.
   - **Instructions** (system prompt) - the box on the left where you set
     the agent's persona and rules. Try pasting
     `You are a pirate. Answer every question in pirate slang.` and chat
     again to see the effect.
   - **Chat** - the main conversation area. Type `Hello world` and verify
     the model responds. Use it to iterate on prompts before committing
     them to code.
   - **View code** - opens a side panel with ready-to-paste snippets
     (Python, curl, etc.) that show exactly how to call this deployment
     from your own app, including the endpoint and headers.

![Deployed models](images/02b-playground-hello.png)



## Part 3 - Get the Endpoint and API Key

Now that you know the model works, you need three things to call it from
your own code: the **endpoint** (where to send requests), the **API key**
(proof you're allowed to), and the **deployment name** (which model
instance to use). All three live one click away.

1. In the playground - click the **Details** tab at the top.
2. On the **Details** tab, copy:
   - **Target URI** - the endpoint, e.g. `https://<your-resource>.services.ai.azure.com/anthropic`
   - **Key** - click the eye icon to reveal it, then the copy icon next to it
   - **Name** of the deployment (e.g. `claude-sonnet-4-6`) - shown under **Deployment info**

![Endpoint keys](images/03-endpoint-keys.png)

> 🔐 Treat the API key like a password. Don't paste it into chats,
> screenshots, or commits. The `.env` file you'll edit next is already
> listed in `.gitignore` so it stays on your machine.

3. Copy `.env.sample` to `.env` in the `arepa-lab-agent/` folder, then
   replace the Foundry placeholder values with the ones you just copied.
   Keep the populated `.env` local; only `.env.sample` belongs in Git.

   ```env
   FOUNDRY_ENDPOINT="https://<your-resource>.services.ai.azure.com/anthropic"
   FOUNDRY_API_KEY="<your-api-key>"
   FOUNDRY_MODEL_DEPLOYMENT="<your-deployment-name>"
   MCP_SERVER_URL="http://127.0.0.1:8000/mcp/"
   ```

   `MCP_SERVER_URL` is separate from the Foundry endpoint. The local default
   requires the Arepa Lab server to run in the same machine/container as
   the client. For a hosted lab or Codespace without that server, replace
   it with the facilitator-provided Streamable HTTP URL, including `/mcp/`.
   The workshop demo MCP endpoint has no authentication; do not send your
   Foundry key or training key to it. The rebranded hosted endpoint has
   not yet been confirmed deployed.


## Part 4 - Build the Agent

With Foundry on the line, time to write some code. You'll be using the
**Microsoft Agent Framework** - a small Python library that wraps a chat
model, a session (the conversation history), and any tools you give it
into a single `Agent` object you can talk to.

### Setup

Open a terminal in the `arepa-lab-agent/` folder of this repo:

```bash
cd arepa-lab-agent
```

The folder already contains a `requirements.txt` with the dependencies you need:

```txt
agent-framework
agent-framework-foundry
python-dotenv
```

- `agent-framework` - the core `Agent`, sessions, and tool plumbing.
- `agent-framework-foundry` - the Foundry-specific chat clients (this is
  what knows how to talk to your Anthropic deployment on Foundry).
- `python-dotenv` - loads your `.env` file into environment variables.

Install them:

```bash
pip install -r requirements.txt
```

> 💡 **Tip:** if you're working locally, create a virtual environment
> first (`python -m venv .venv && source .venv/bin/activate`) so these
> packages don't pollute your global Python. In Codespaces this is
> already taken care of.

Open the starter `agent.py` file in the same folder. You'll build it up in
three small steps - run it after each step to see the agent grow.



### Step 1 - Hello World Agent

Start with a minimal agent that just talks to the model. No tools, no
persona - just confirm we can reach Foundry. Three pieces show up here
that you'll see in every agent you build:

- **Chat client** - the connection to the model. `AnthropicFoundryClient`
  knows how to call your Claude deployment on Foundry using the values
  from `.env`.
- **Agent** - wraps the chat client (and later, tools and instructions).
- **Session** - holds the conversation history so the agent remembers
  what was said earlier in the chat.

```python
"""Arepa Lab - The arepa ordering agent."""

import asyncio
import os

from dotenv import load_dotenv

from agent_framework import Agent
from agent_framework.foundry import AnthropicFoundryClient

# 1. Load environment variables from .env
load_dotenv()


async def main() -> None:
    # 2. Configure the chat model (Claude on Microsoft Foundry)
    chat_client = AnthropicFoundryClient(
        model=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],
        api_key=os.environ["FOUNDRY_API_KEY"],
        base_url=os.environ["FOUNDRY_ENDPOINT"],
    )

    # 3. Create the agent
    agent = Agent(
        client=chat_client,
        name="arepa-lab-agent",
    )

    # 4. Start a chat session and talk to the agent
    session = agent.create_session()
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("\033[1;35mYou:\033[0m\n")
        if user_input.lower() in ("exit", "quit"):
            break

        response = await agent.run(user_input, session=session)
        print(f"\n\033[1;35mAssistant:\033[0m\n{response.text}\n")


if __name__ == "__main__":
    asyncio.run(main())
```

**Try it:**

```bash
python agent.py
```

```
You:
Hello!

Assistant:
Hi there! How can I help you today?
```

![Hello world](images/04-step1-hello.png)



### Step 2 - Connect to the Arepa Lab MCP Server

A chatbot that only chats is just an expensive parrot. To actually *do*
things - list in-stock arepas, place an order, check its status - the
agent needs **tools**. Staff, not the client, mark real orders ready for pickup.

> **What is MCP?** The **Model Context Protocol** is an open standard
> for letting AI agents talk to external systems. An MCP server publishes
> a set of tools (functions the agent can call), prompts (reusable
> instruction snippets), and resources (data) over HTTP. Your agent just
> needs the URL - the framework handles discovery and invocation.
> Arepa Lab uses **Streamable HTTP**, not the legacy SSE transport.

Two changes to your `agent.py`:

1. Import `MCPStreamableHTTPTool`, read the server URL from `MCP_SERVER_URL`, and call `connect()`.
2. Pass it to the `Agent` via `tools=`.

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

```python
"""Arepa Lab - The arepa ordering agent."""

import asyncio
import os

from dotenv import load_dotenv

from agent_framework import Agent, MCPStreamableHTTPTool   # 👈 updated
from agent_framework.foundry import AnthropicFoundryClient

# 1. Load environment variables from .env
load_dotenv()

async def main() -> None:
    # 2. Configure the chat model (Claude on Microsoft Foundry)
    chat_client = AnthropicFoundryClient(
        model=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],
        api_key=os.environ["FOUNDRY_API_KEY"],
        base_url=os.environ["FOUNDRY_ENDPOINT"],
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

**Run it:**

```bash
python agent.py
```

**Try it:**

```
You:
What arepas do you have today?

Assistant:
Here's what we have in stock today: ...
```

Use the live menu response; item names and availability can change.
Do not place an order yet. This step only checks menu discovery.

The agent is now calling MCP tools on the Arepa Lab server. But it's
still acting like a generic assistant - it has no persona yet.



### Step 3 - Load Instructions and a Welcome Banner from MCP

The agent works, but it still sounds like a generic assistant. The
Arepa Lab defines how its agent should behave - registration, vouchers,
order confirmation, and allergy guidance - and it doesn't want every
developer to copy-paste the latest version of that persona into their
code. So those instructions live on the **server**, not in your repo.

MCP servers can expose **prompts** - reusable text snippets curated by
the server owner. When the persona changes, the server updates; your
code keeps working without a redeploy. Arepa Lab exposes two:

- `agent_instructions` - the canonical agent conversation instructions
- `welcome_banner` - a friendly greeting to print at startup

Fetch both from the server, pass `agent_instructions` to the `Agent`, and
print the banner before the chat starts.

```python
"""Arepa Lab - The arepa ordering agent."""

import asyncio
import os

from dotenv import load_dotenv

from agent_framework import Agent, MCPStreamableHTTPTool  
from agent_framework.foundry import AnthropicFoundryClient

# 1. Load environment variables from .env
load_dotenv()


async def main() -> None:
    # 2. Configure the chat model (Claude on Microsoft Foundry)
    chat_client = AnthropicFoundryClient(
        model=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],
        api_key=os.environ["FOUNDRY_API_KEY"],
        base_url=os.environ["FOUNDRY_ENDPOINT"],
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

The agent now also kicks off the conversation itself by sending a `"hello"`,
so the user sees the persona greet them right away.

**Run it:**

```bash
python agent.py
```

**Try it:** Ask for a **test arepa order** first.

```txt
You:
I'd like to place a test arepa order.
```

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

## Recap

In under a hundred lines of Python, you built an AI agent that:

- ✅ Uses a model deployment from Microsoft Foundry
- ✅ Calls live tools through an MCP server
- ✅ Loads its persona and welcome banner from MCP **prompts** and greets
  the user automatically

The pattern you just used - **Foundry for the model, Agent Framework for
the glue, MCP for tools and prompts** - is the same one you'd use to
build a support bot, a coding assistant, or an internal company helper.
Swap the MCP server, change the persona, and you have a different agent.

The full source is in [`sample-code/agent.py`](sample-code/agent.py).

### Where to go next

- **Add another MCP server.** The framework can connect to multiple at
  once - try giving the agent a weather server or a calendar server in
  addition to Arepa Lab.
- **Swap the model.** Deploy a different model on Foundry, change
  `FOUNDRY_MODEL_DEPLOYMENT`, and see how the personality shifts.
- **Stream the responses.** Use `agent.run_stream(...)` for token-by-token
  output so the chat feels snappier.
- **Build your own MCP server.** Once you've consumed one, writing one
  is the natural next step - and now your agent can use it.



## Troubleshooting

| Problem | Fix |
| -- | -- |
| `Missing required environment variable` | Copy `.env.sample` to `.env` in `arepa-lab-agent/` (or `workshop/sample-code/` for the reference agent), then fill in the Foundry values |
| Foundry `401 Unauthorized` | Wrong API key or endpoint - re-copy from Foundry; the demo MCP endpoint needs no authentication |
| MCP connection fails or tools are missing | Check `MCP_SERVER_URL`, including `/mcp/`, points to a running Arepa Lab server. `127.0.0.1` means the client's machine/container; the hosted endpoint must come from the facilitator |
| Order voucher is rejected | Read the current six-character dashboard voucher; both `test` and `real` orders require it, not `ArepasAtSHPE` |
| `DeploymentNotFound` | `FOUNDRY_MODEL_DEPLOYMENT` must match the **deployment** name, not the model name |
| `ImportError: cannot import name 'Agent'` | Run `pip install -r requirements.txt` again |