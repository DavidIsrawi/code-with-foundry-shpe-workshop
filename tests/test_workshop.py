"""Offline checks for the reference client and copy-paste workshop code."""

import ast
import asyncio
import contextlib
import io
import os
from pathlib import Path
import re
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, call, patch, sentinel


ROOT = Path(__file__).resolve().parents[1]
LOCAL_MCP_URL = "http://127.0.0.1:8000/mcp/"
TOOL_ARGUMENTS = {
    "register_customer": ("first_name", "last_name", "city"),
    "get_customer": ("customer_id",),
    "list_arepas": (),
    "order_arepa": ("flavor_id", "customer_id", "kind", "voucher_code"),
    "check_order_status": ("customer_id",),
    "cancel_order": ("customer_id", "kind"),
    "voucher_status": (),
}


def python_blocks(path):
    return re.findall(r"```python(?:-notype)?\n(.*?)```", path.read_text(), re.S)


def agent_sources():
    yield "reference", 3, (ROOT / "workshop/sample-code/agent.py").read_text()
    for stage, source in enumerate(python_blocks(ROOT / "workshop/workshop.md"), 1):
        yield f"workshop-step-{stage}", stage, source
    for stage in range(1, 4):
        path = ROOT / f"workshop/skillable/part-4-step-{stage}.md"
        for source in python_blocks(path):
            yield f"skillable-step-{stage}", stage, source


class WorkshopTests(unittest.TestCase):
    def test_clients_use_configured_endpoint_and_server_prompts(self):
        sources = list(agent_sources())
        self.assertEqual(len(sources), 7)
        for name, stage, source in sources:
            for endpoint in (None, "http://127.0.0.1:8765/mcp/"):
                for exit_word in ("exit", "quit"):
                    with self.subTest(source=name, endpoint=endpoint, exit=exit_word):
                        self.check_client(source, stage, endpoint, exit_word)

    def test_clients_route_openai_and_foundry_project_endpoints(self):
        for name, stage, source in agent_sources():
            for model_endpoint, expected_url in [
                ("https://example.invalid/openai/v1/", "https://example.invalid/openai/v1"),
                ("https://example.invalid/api/projects/test", "https://example.invalid/api/projects/test/openai/v1"),
                ("https://example.invalid/api/projects/test/openai/v1", "https://example.invalid/api/projects/test/openai/v1"),
            ]:
                with self.subTest(source=name, endpoint=model_endpoint):
                    self.check_client(
                        source, stage, None, "exit",
                        model_endpoint=model_endpoint, expected_url=expected_url,
                    )

    def check_client(self, source, stage, endpoint, exit_word, *,
                     model_endpoint="https://example.invalid/anthropic", expected_url=None):
        environment = {
            "FOUNDRY_ENDPOINT": model_endpoint,
            "FOUNDRY_API_KEY": "offline-test-key",
            "FOUNDRY_MODEL_DEPLOYMENT": "claude-sonnet-4-6",
        }
        if endpoint is not None:
            environment["MCP_SERVER_URL"] = endpoint

        mcp = Mock(
            connect=AsyncMock(),
            close=AsyncMock(),
            get_prompt=AsyncMock(side_effect=[sentinel.instructions, "Arepa Lab"]),
        )
        agent = Mock(
            create_session=Mock(return_value=sentinel.session),
            run=AsyncMock(return_value=SimpleNamespace(text="Offline response")),
        )
        framework = ModuleType("agent_framework")
        framework.Agent = Mock(return_value=agent)
        framework.MCPStreamableHTTPTool = Mock(return_value=mcp)
        foundry = ModuleType("agent_framework.foundry")
        foundry.AnthropicFoundryClient = Mock(return_value=sentinel.client)
        openai = ModuleType("agent_framework.openai")
        openai.OpenAIChatClient = Mock(return_value=sentinel.client)
        dotenv = ModuleType("dotenv")
        dotenv.load_dotenv = Mock()
        modules = {
            "agent_framework": framework,
            "agent_framework.foundry": foundry,
            "agent_framework.openai": openai,
            "dotenv": dotenv,
        }
        output = io.StringIO()
        namespace = {"__name__": "workshop_test"}
        with (
            patch.dict(sys.modules, modules),
            patch.dict(os.environ, environment, clear=True),
            patch("builtins.input", side_effect=["What arepas are available?", exit_word]),
            contextlib.redirect_stdout(output),
        ):
            exec(compile(source, "<workshop-agent>", "exec"), namespace)
            asyncio.run(namespace["main"]())

        dotenv.load_dotenv.assert_called_once_with()
        model_client = openai.OpenAIChatClient if expected_url else foundry.AnthropicFoundryClient
        unused_client = foundry.AnthropicFoundryClient if expected_url else openai.OpenAIChatClient
        unused_client.assert_not_called()
        model_client.assert_called_once_with(
            model=environment["FOUNDRY_MODEL_DEPLOYMENT"],
            api_key=environment["FOUNDRY_API_KEY"],
            base_url=expected_url or environment["FOUNDRY_ENDPOINT"],
        )
        expected_agent = {"client": sentinel.client, "name": "arepa-lab-agent"}
        if stage >= 2:
            framework.MCPStreamableHTTPTool.assert_called_once_with(
                name="arepa-lab", url=endpoint or LOCAL_MCP_URL
            )
            mcp.connect.assert_awaited_once_with()
            mcp.close.assert_awaited_once_with()
            expected_agent["tools"] = mcp
        else:
            framework.MCPStreamableHTTPTool.assert_not_called()
        expected_calls = [call("What arepas are available?", session=sentinel.session)]
        if stage == 3:
            self.assertEqual(
                mcp.get_prompt.await_args_list,
                [call("agent_instructions"), call("welcome_banner")],
            )
            expected_agent["instructions"] = sentinel.instructions
            expected_calls.insert(0, call("hello", session=sentinel.session))
            self.assertIn("Arepa Lab", output.getvalue())
        else:
            mcp.get_prompt.assert_not_awaited()
        framework.Agent.assert_called_once_with(**expected_agent)
        agent.create_session.assert_called_once_with()
        self.assertEqual(agent.run.await_args_list, expected_calls)

    def test_final_lab_snippets_match_reference(self):
        reference = ast.dump(ast.parse((ROOT / "workshop/sample-code/agent.py").read_text()))
        for name, stage, source in agent_sources():
            if stage == 3:
                with self.subTest(source=name):
                    self.assertEqual(ast.dump(ast.parse(source)), reference)

    def test_environment_templates_match(self):
        starter = (ROOT / "arepa-lab-agent/.env.sample").read_text()
        reference = (ROOT / "workshop/sample-code/.env.sample").read_text()
        self.assertEqual(starter, reference)
        self.assertIn(f'MCP_SERVER_URL="{LOCAL_MCP_URL}"', starter)
        self.assertEqual(
            set(re.findall(r"^(\w+)=", starter, re.M)),
            {"FOUNDRY_ENDPOINT", "FOUNDRY_API_KEY", "FOUNDRY_MODEL_DEPLOYMENT", "MCP_SERVER_URL"},
        )

    def test_documented_tool_argument_shapes(self):
        paths = [
            ROOT / "README.md",
            ROOT / "workshop/workshop.md",
            ROOT / "workshop/skillable/part-4-step-2.md",
        ]
        for path in paths:
            documented = {}
            for name, parameters in re.findall(r"`(\w+)\(([^)]*)\)`", path.read_text()):
                if name in TOOL_ARGUMENTS:
                    arguments = tuple(p.strip() for p in parameters.split(",") if p.strip())
                    with self.subTest(path=path, tool=name):
                        self.assertEqual(arguments, TOOL_ARGUMENTS[name])
                    documented[name] = arguments
            with self.subTest(path=path):
                self.assertEqual(documented, TOOL_ARGUMENTS)

    def test_local_document_links_resolve(self):
        paths = [ROOT / "README.md", ROOT / "arepa-lab-agent/README.md"]
        paths.extend((ROOT / "workshop").rglob("*.md"))
        for path in paths:
            for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
                if "://" in link or link.startswith("#"):
                    continue
                target = link.split("#", 1)[0]
                with self.subTest(path=path, target=target):
                    self.assertTrue((path.parent / target).exists())


if __name__ == "__main__":
    unittest.main()
