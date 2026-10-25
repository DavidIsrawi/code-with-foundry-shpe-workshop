"""Real HTTP clients and disposable local services for the v0 E2E suites."""

from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time

from agent_framework import MCPStreamableHTTPTool
import httpx


ROOT = Path(__file__).resolve().parents[2]
TOOL_ARGUMENTS = {
    "register_customer": {"first_name", "last_name", "city"},
    "list_arepas": set(),
    "order_arepa": {"flavor_id", "customer_id", "kind", "voucher_code"},
    "check_order_status": {"customer_id"},
    "cancel_order": {"customer_id", "kind"},
    "voucher_status": set(),
}
FLAVOR_ID = "e2e-arepa"
FLAVOR_NAME = "E2E Arepa"
# Public Azurite development credential, never a real Azure account key.
AZURITE_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6"
    "tq/K1SZFPTOtr/KBHBeksoGMGw=="
)


def decode_result(result):
    text = result if isinstance(result, str) else "".join(item.text for item in result)
    value = json.loads(text)
    if isinstance(value, dict) and set(value) == {"result"}:
        return value["result"]
    return value


class RecordingMCPTool(MCPStreamableHTTPTool):
    """Observe the real adapter; never replace network calls or tool results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []
        self.prompts = []

    async def call_tool(self, tool_name, **kwargs):
        if len(self.calls) >= 60:
            raise RuntimeError("E2E tool-call budget exceeded")
        result = await super().call_tool(tool_name, **kwargs)
        self.calls.append({
            "tool": tool_name,
            "arguments": {key: value for key, value in kwargs.items()
                          if key in TOOL_ARGUMENTS.get(tool_name, set())},
            "result": decode_result(result),
        })
        return result

    async def get_prompt(self, name, *args, **kwargs):
        result = await super().get_prompt(name, *args, **kwargs)
        self.prompts.append(name)
        return result

    async def call(self, name, **arguments):
        return decode_result(await self.call_tool(name, **arguments))


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


class LocalServer:
    def __init__(self, label):
        self.repo = Path(os.environ["AREPA_SERVER_REPO"]).resolve()
        self.python = os.environ.get("AREPA_SERVER_PYTHON", sys.executable)
        self.directory = Path(os.environ["AREPA_E2E_ARTIFACTS"]) / label
        self.stack = ExitStack()

    def __enter__(self):
        try:
            self.start()
        except BaseException:
            self.stack.close()
            raise
        return self

    def __exit__(self, *args):
        self.stack.close()

    def start_process(self, name, command, env=None, cwd=None):
        output = self.stack.enter_context((self.directory / f"{name}.log").open("w"))
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
        )
        self.stack.callback(stop_process, process)
        return process

    def wait_for_http(self, process, url, expected_status):
        deadline = time.monotonic() + 45
        with httpx.Client(timeout=1, trust_env=False) as client:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Local service exited; inspect logs in {self.directory}")
                try:
                    response = client.get(url)
                except httpx.TransportError:
                    pass
                else:
                    if response.status_code == expected_status:
                        return
                time.sleep(0.1)
        raise TimeoutError(f"Local service did not become ready; inspect {self.directory}")

    def start(self):
        if not (self.repo / "backend/main.py").is_file():
            raise RuntimeError(f"AREPA_SERVER_REPO is not an Arepa Lab checkout: {self.repo}")
        azurite = shutil.which("azurite-table")
        if not azurite:
            raise RuntimeError("azurite-table is required; install Azurite with npm install -g azurite")
        self.directory.mkdir(parents=True)
        table_port = free_port()
        table_url = f"http://127.0.0.1:{table_port}/devstoreaccount1"
        storage = self.start_process("azurite", [
            azurite, "--tableHost", "127.0.0.1", "--tablePort", str(table_port),
            "--location", str(self.directory / "storage"), "--silent",
        ])
        self.wait_for_http(storage, f"{table_url}/Tables", 403)
        self.environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith("FOUNDRY_")
        }
        self.password = secrets.token_urlsafe(24)
        self.environment.update({
            "AZURE_STORAGE_CONNECTION_STRING": (
                "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
                f"AccountKey={AZURITE_KEY};TableEndpoint={table_url};"
            ),
            "SESSION_SECRET": secrets.token_urlsafe(32),
            "SESSION_COOKIE_SECURE": "false",
            "INITIAL_ADMIN_PASSWORD": self.password,
            "VOUCHER_SECRET": secrets.token_urlsafe(32),
            "WORKSHOP_URL": "",
            "WORKSHOP_TRAINING_KEY": "",
        })
        port = free_port()
        self.url = f"http://127.0.0.1:{port}"
        self.mcp_url = f"{self.url}/mcp/"
        app = self.start_process("server", [
            self.python, "-m", "uvicorn", "backend.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning",
        ], env=self.environment, cwd=self.repo)
        self.wait_for_http(app, f"{self.url}/arepas", 200)
        self.web = self.stack.enter_context(httpx.Client(
            base_url=self.url, follow_redirects=True, timeout=15, trust_env=False,
        ))
        login = self.post("/admin/login", data={"username": "admin", "password": self.password})
        token = re.search(r'name="csrf-token" content="([^"]+)"', login.text)
        if token is None:
            raise AssertionError("Admin login did not return a CSRF token")
        self.web.headers["X-CSRF-Token"] = token.group(1)
        self.post("/admin/flavors", data={
            "name": FLAVOR_NAME, "description": "Synthetic E2E fixture",
            "price": "0", "stock": "12",
        })
        assert self.snapshot()["flavors"][0]["RowKey"] == FLAVOR_ID

    def post(self, path, **kwargs):
        response = self.web.post(path, **kwargs)
        response.raise_for_status()
        return response

    def voucher(self):
        response = self.web.get("/dashboard/data")
        response.raise_for_status()
        return response.json()["voucher"]

    def set_stock(self, stock):
        self.post(f"/admin/flavors/{FLAVOR_ID}/edit", data={"stock": str(stock)})

    def snapshot(self):
        # A read-only storage oracle verifies exact counts, not just stock labels.
        result = subprocess.run([
            self.python, "-c",
            "import json; from backend import storage; "
            "print(json.dumps({'flavors': storage.list_flavors(), "
            "'orders': storage.list_orders(), 'customers': storage.list_customers()}, default=str))",
        ], cwd=self.repo, env=self.environment, capture_output=True, text=True,
            check=True, timeout=20)
        return json.loads(result.stdout)

    def write_report(self, name, value):
        (self.directory / name).write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n")
