"""Run the reference client with real Foundry and MCP connections."""

import asyncio
from contextlib import redirect_stdout
import io
import os
import runpy
import unittest
from unittest.mock import patch

from support import FLAVOR_ID, FLAVOR_NAME, LocalServer, RecordingMCPTool, ROOT, TOOL_ARGUMENTS


class WorkshopAgentTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = cls.enterClassContext(LocalServer("agent"))

    async def test_reference_agent_uses_every_tool_in_a_conversation(self):
        test = self
        instances = []
        messages = []
        output = io.StringIO()
        completed = False

        class ObservedTool(RecordingMCPTool):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                instances.append(self)

        def calls():
            test.assertEqual(len(instances), 1)
            return instances[0].calls

        def called_since(name, start, success=None):
            matching = [call for call in calls()[start:] if call["tool"] == name]
            if success is not None:
                matching = [call for call in matching
                            if call["result"].get("success") is success]
            test.assertTrue(matching, f"Agent did not call {name} as expected after turn {len(messages)}")
            return matching[-1]

        def assert_state(customer_id, stock, allowance):
            state = test.server.snapshot()
            test.assertEqual(state["flavors"][0]["stock"], stock)
            customer = next(row for row in state["customers"] if row["RowKey"] == customer_id)
            test.assertEqual(customer["real_orders_count"], allowance)

        def order_message(kind, code):
            return (
                f"I explicitly want a {kind.upper()} order for {FLAVOR_NAME}. "
                f"The dashboard voucher I read is {code}. "
                "Use the customer ID you already registered for me."
            )

        def conversation():
            start = len(calls())
            yield (
                "I am a new customer and do not have a customer ID. "
                "My first name is Ana, my last name is Smoke, and my city is Test City. "
                "Please register me using these details."
            )
            registration = called_since("register_customer", start, success=True)
            customer_id = registration["result"]["customer_id"]
            test.assertEqual(registration["arguments"], {
                "first_name": "Ana", "last_name": "Smoke", "city": "Test City",
            })
            assert_state(customer_id, 12, 0)

            start = len(calls())
            yield "Please refresh and show me the currently available arepas."
            called_since("list_arepas", start)

            start = len(calls())
            yield order_message("test", test.server.wrong_voucher())
            called_since("order_arepa", start, success=False)
            assert_state(customer_id, 12, 0)
            if not any(call["tool"] == "voucher_status" for call in calls()[start:]):
                start = len(calls())
                yield (
                    "That voucher failed. Please use voucher_status to check how long the "
                    "dashboard code is valid, then ask me to reread it. Do not place another order yet."
                )
                called_since("voucher_status", start)

            start = len(calls())
            yield order_message("test", test.server.voucher())
            test_order = called_since("order_arepa", start, success=True)
            test.assertEqual(test_order["arguments"]["kind"], "test")
            test.assertEqual(test_order["arguments"]["flavor_id"], FLAVOR_ID)
            assert_state(customer_id, 12, 0)
            state = test.server.snapshot()
            test.assertEqual(
                next(row for row in state["orders"] if row["RowKey"] == test_order["result"]["order_id"])["status"],
                "collected",
            )

            start = len(calls())
            yield order_message("real", test.server.voucher())
            called_since("order_arepa", start, success=True)
            assert_state(customer_id, 11, 1)

            start = len(calls())
            yield "Please check the status of my active real order now."
            pending = called_since("check_order_status", start)
            test.assertEqual(pending["result"]["status"], "pending")

            start = len(calls())
            yield "Please cancel my pending real order. I have changed my mind."
            called_since("cancel_order", start, success=True)
            assert_state(customer_id, 12, 0)

            start = len(calls())
            yield order_message("real", test.server.voucher())
            replacement = called_since("order_arepa", start, success=True)
            order_id = replacement["result"]["order_id"]
            assert_state(customer_id, 11, 1)
            test.server.post(f"/admin/orders/{order_id}/ready")

            start = len(calls())
            yield "Please check the status of my replacement real order now."
            ready = called_since("check_order_status", start)
            test.assertEqual(ready["result"]["status"], "ready")
            test.server.post(f"/admin/orders/{order_id}/collected")

            start = len(calls())
            yield "Staff have handed me my arepa. Please check whether I still have an active real order."
            collected = called_since("check_order_status", start)
            test.assertFalse(collected["result"]["found"])
            assert_state(customer_id, 11, 1)

            start = len(calls())
            yield (
                f"I'm a returning customer and my customer ID is {customer_id}. "
                "Please look me up and tell me whether I can still order a real arepa."
            )
            if not any(call["tool"] == "get_customer" for call in calls()[start:]):
                start = len(calls())
                yield (
                    f"Please use get_customer with my customer ID {customer_id} to confirm "
                    "that from the server rather than from memory."
                )
            returning = called_since("get_customer", start)
            test.assertTrue(returning["result"]["found"])
            test.assertFalse(returning["result"]["can_order_real"])
            test.assertIsNone(returning["result"]["active_real_order"])

            test.assertEqual({call["tool"] for call in calls()}, set(TOOL_ARGUMENTS))
            test.assertEqual(sum(call["tool"] == "register_customer" for call in calls()), 1)
            for call in calls():
                if "customer_id" in call["arguments"]:
                    test.assertEqual(call["arguments"]["customer_id"], customer_id)
            rows = [row for row in test.server.snapshot()["orders"] if row["customer_id"] == customer_id]
            test.assertEqual(len(rows), 3)
            test.assertCountEqual([row["status"] for row in rows], ["collected", "cancelled", "collected"])

        script = conversation()

        def next_input(prompt):
            nonlocal completed
            try:
                message = next(script)
            except StopIteration:
                completed = True
                return "exit"
            messages.append(message)
            return message

        try:
            with patch.dict(os.environ, {"MCP_SERVER_URL": self.server.mcp_url}):
                namespace = runpy.run_path(str(ROOT / "workshop/sample-code/agent.py"))
                main = namespace["main"]
                # Only replace terminal input and observe the real MCP adapter.
                # Agent, Foundry client, prompts, and network calls stay unchanged.
                main.__globals__["input"] = next_input
                main.__globals__["MCPStreamableHTTPTool"] = ObservedTool
                with redirect_stdout(output):
                    await asyncio.wait_for(main(), timeout=300)
            self.assertTrue(completed, "Reference client stopped before the scenario completed")
            self.assertEqual(instances[0].prompts[:2], ["agent_instructions", "welcome_banner"])
            self.assertFalse(instances[0].is_connected, "Reference client did not close its MCP connection")
        finally:
            try:
                for tool in instances:
                    if tool.is_connected:
                        await tool.close()
            finally:
                self.server.write_report("conversation.json", {
                    "completed": completed,
                    "user_messages": messages,
                    "tool_calls": instances[0].calls if instances else [],
                    "transcript": output.getvalue(),
                })
