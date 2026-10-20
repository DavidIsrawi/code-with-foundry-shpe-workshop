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

    # 4. Get the instructions and welcome banner from the MCP server
    instructions = await mcp_tool.get_prompt("agent_instructions")
    banner = await mcp_tool.get_prompt("welcome_banner")

    # 5. Create the agent
    agent = Agent(
        client=chat_client,
        name="arepa-lab-agent",
        instructions=instructions,
        tools=mcp_tool,
    )

    # 6. Start a chat session and talk to the agent
    session = agent.create_session()
    print(banner)
    print("Type 'exit' to quit.\n")

    # Kick things off automatically
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
