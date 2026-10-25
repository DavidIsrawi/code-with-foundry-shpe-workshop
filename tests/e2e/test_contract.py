"""Deterministic workshop-client -> HTTP MCP -> Azure Tables coverage."""

import unittest

from support import FLAVOR_ID, LocalServer, RecordingMCPTool, TOOL_ARGUMENTS


class MCPContractTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = cls.enterClassContext(LocalServer("contract"))

    async def asyncSetUp(self):
        self.server.set_stock(12)
        self.tool = RecordingMCPTool(name="contract", url=self.server.mcp_url)
        await self.tool.connect()
        self.addAsyncCleanup(self.tool.close)
        self.addCleanup(self.server.write_report, f"{self._testMethodName}.json", self.tool.calls)

    async def customer(self):
        result = await self.tool.call(
            "register_customer", first_name="María", last_name="Smoke", city="Bogotá",
        )
        self.assertTrue(result["success"])
        return result["customer_id"]

    async def order(self, registered_id, kind="real", **overrides):
        arguments = {
            "flavor_id": FLAVOR_ID, "customer_id": registered_id,
            "kind": kind, "voucher_code": self.server.voucher(),
        }
        arguments.update(overrides)
        return await self.tool.call("order_arepa", **arguments)

    def state(self, customer_id):
        state = self.server.snapshot()
        return (
            state["flavors"][0]["stock"],
            next(row for row in state["customers"] if row["RowKey"] == customer_id)["real_orders_count"],
            [row for row in state["orders"] if row["customer_id"] == customer_id],
        )

    async def test_discovery_prompts_schemas_and_annotations(self):
        discovered = (await self.tool.session.list_tools()).tools
        self.assertEqual({tool.name for tool in discovered}, set(TOOL_ARGUMENTS))
        expected = {
            "register_customer": (False, False, False),
            "list_arepas": (True, False, True),
            "order_arepa": (False, True, False),
            "check_order_status": (True, False, True),
            "cancel_order": (False, True, False),
            "voucher_status": (True, False, True),
        }
        for tool in discovered:
            with self.subTest(tool=tool.name):
                self.assertEqual(set(tool.inputSchema.get("required", [])), TOOL_ARGUMENTS[tool.name])
                annotations = tool.annotations
                self.assertIsNotNone(annotations)
                self.assertEqual((
                    annotations.readOnlyHint, annotations.destructiveHint, annotations.idempotentHint,
                ), expected[tool.name])
                self.assertIs(annotations.openWorldHint, False)
        prompts = (await self.tool.session.list_prompts()).prompts
        self.assertEqual({prompt.name for prompt in prompts}, {"agent_instructions", "welcome_banner"})
        self.assertIn("CONVERSATION FLOW", await self.tool.get_prompt("agent_instructions"))
        self.assertIn("AREPA LAB", await self.tool.get_prompt("welcome_banner"))

    async def test_all_six_tools_in_one_customer_journey(self):
        self.server.set_stock(4)
        customer_id = await self.customer()
        menu = await self.tool.call("list_arepas")
        self.assertEqual(menu[0]["id"], FLAVOR_ID)
        self.assertNotIn("stock", menu[0])
        timing = await self.tool.call("voucher_status")
        self.assertGreater(timing["seconds_until_rotation"], 0)
        self.assertLessEqual(timing["seconds_until_rotation"], 180)
        self.assertEqual(timing["window_seconds"], 180)
        self.assertEqual(set(timing), {"seconds_until_rotation", "window_seconds", "message"})
        self.assertFalse((await self.tool.call("check_order_status", customer_id=customer_id))["found"])

        test = await self.order(customer_id.lower(), "test")
        self.assertTrue(test["success"])
        stock, count, rows = self.state(customer_id)
        self.assertEqual((stock, count, rows[0]["status"]), (4, 0, "collected"))
        real = await self.order(customer_id)
        self.assertTrue(real["success"])
        self.assertEqual(self.state(customer_id)[:2], (3, 1))
        status = await self.tool.call("check_order_status", customer_id=customer_id)
        self.assertEqual((status["found"], status["status"]), (True, "pending"))
        self.assertFalse((await self.order(customer_id))["success"])

        cancelled = await self.tool.call("cancel_order", customer_id=customer_id, kind="real")
        self.assertTrue(cancelled["success"])
        self.assertEqual(self.state(customer_id)[:2], (4, 0))
        self.assertFalse((await self.tool.call("cancel_order", customer_id=customer_id, kind="real"))["success"])
        self.assertEqual(self.state(customer_id)[:2], (4, 0))
        self.assertTrue((await self.order(customer_id))["success"])
        self.assertEqual({call["tool"] for call in self.tool.calls}, set(TOOL_ARGUMENTS))
        self.server.write_report("all-tools.json", self.tool.calls)

    async def test_ready_collection_and_lifetime_limit(self):
        customer_id = await self.customer()
        order = await self.order(customer_id)
        self.assertTrue(order["success"])
        self.server.post(f"/admin/orders/{order['order_id']}/ready")
        status = await self.tool.call("check_order_status", customer_id=customer_id)
        self.assertEqual(status["status"], "ready")
        self.assertFalse((await self.tool.call("cancel_order", customer_id=customer_id, kind="real"))["success"])
        self.assertEqual(self.state(customer_id)[:2], (11, 1))
        self.server.post(f"/admin/orders/{order['order_id']}/collected")
        self.assertFalse((await self.tool.call("check_order_status", customer_id=customer_id))["found"])
        self.assertFalse((await self.order(customer_id))["success"])
        self.assertTrue((await self.order(customer_id, "test"))["success"])
        self.assertEqual(self.state(customer_id)[:2], (11, 1))

    async def test_registration_and_order_validation_has_no_side_effects(self):
        before = self.server.snapshot()
        for fields in [
            {"first_name": " "}, {"last_name": "x" * 51}, {"city": "<script>"},
        ]:
            with self.subTest(fields=fields):
                values = {"first_name": "Smoke", "last_name": "Test", "city": "Test City", **fields}
                self.assertFalse((await self.tool.call("register_customer", **values))["success"])
        self.assertEqual(self.server.snapshot(), before)
        registered = await self.tool.call(
            "register_customer", first_name=" María ", last_name=" O'Brien ", city=" Bogotá ",
        )
        self.assertEqual(
            (registered["first_name"], registered["last_name"], registered["city"]),
            ("María", "O'Brien", "Bogotá"),
        )
        customer_id = registered["customer_id"]
        for invalid in [
            {"customer_id": "invalid"}, {"customer_id": "ZZZZZZZZ"},
            {"flavor_id": "missing"}, {"voucher_code": "WRONG!"},
        ]:
            with self.subTest(invalid=invalid):
                self.assertFalse((await self.order(customer_id, **invalid))["success"])
        self.assertEqual(self.state(customer_id), (12, 0, []))

    async def test_stock_thresholds_and_sold_out_order(self):
        customer_id = await self.customer()
        for stock, status in [(1, "almost_finished"), (3, "almost_finished"),
                              (4, "limited"), (10, "limited"), (11, "plenty")]:
            with self.subTest(stock=stock):
                self.server.set_stock(stock)
                self.assertEqual((await self.tool.call("list_arepas"))[0]["stock_status"], status)
        self.server.set_stock(0)
        self.assertEqual(await self.tool.call("list_arepas"), [])
        self.assertFalse((await self.order(customer_id))["success"])
        stock, count, rows = self.state(customer_id)
        self.assertEqual((stock, count), (0, 0))
        self.assertTrue(all(row["status"] == "cancelled" for row in rows))
        self.assertFalse((await self.tool.call("check_order_status", customer_id=customer_id))["found"])

    async def test_voucher_throttling_is_shared_with_rest(self):
        customer_id = await self.customer()
        for _ in range(5):
            self.assertFalse((await self.order(customer_id, "test", voucher_code="WRONG!"))["success"])
            rejected = self.server.web.post("/orders", json={
                "flavor_id": FLAVOR_ID, "customer_id": customer_id,
                "kind": "test", "voucher_code": "WRONG!",
            })
            self.assertEqual(rejected.status_code, 403)
        locked = await self.order(customer_id, "test")
        self.assertFalse(locked["success"])
        self.assertIn("Too many", locked["message"])
        self.assertEqual(self.state(customer_id), (12, 0, []))

    async def test_rest_and_mcp_share_registration_ordering_and_cancellation(self):
        customer = self.server.post("/customers", json={
            "first_name": " Rémy ", "last_name": " Smoke ", "city": " Montréal ",
        }).json()
        self.assertEqual(customer["first_name"], "Rémy")
        customer_id = customer["customer_id"]
        response = self.server.post("/orders", json={
            "flavor_id": FLAVOR_ID, "customer_id": f" {customer_id.lower()} ",
            "kind": "real", "voucher_code": self.server.voucher(),
        })
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(self.state(customer_id)[:2], (11, 1))
        self.assertTrue((await self.tool.call("cancel_order", customer_id=customer_id, kind="real"))["success"])
        self.assertEqual(self.state(customer_id)[:2], (12, 0))
