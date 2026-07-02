from __future__ import annotations

import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class FakeFunctionApp:
    def service_bus_queue_trigger(self, **_kwargs):  # noqa: ANN003, ANN201
        return lambda function: function


azure_module = ModuleType("azure")
functions_module = ModuleType("azure.functions")
functions_module.FunctionApp = FakeFunctionApp
functions_module.ServiceBusMessage = object
azure_module.functions = functions_module
sys.modules["azure"] = azure_module
sys.modules["azure.functions"] = functions_module

import function_app


class FakeServiceBusMessage:
    delivery_count = 2

    def get_body(self) -> bytes:
        return (
            b'{"version":1,"job_id":"job-1","place_id":"place-1",'
            b'"restaurant_name":"Test Place","website_url":"https://example.com/menu",'
            b'"document_urls":[],"menu_version":null}'
        )


class FunctionAppTests(unittest.TestCase):
    def test_service_bus_trigger_parses_and_processes_message(self) -> None:
        completed = SimpleNamespace(id="job-1", place_id="place-1", status="complete", item_count=4)

        with patch("function_app.process_menu_refresh_message", return_value=completed) as process, patch(
            "function_app.logging.info"
        ) as log_info:
            function_app.process_menu_refresh(FakeServiceBusMessage())

        message = process.call_args.args[0]
        self.assertEqual(message.job_id, "job-1")
        self.assertEqual(message.place_id, "place-1")
        self.assertEqual(process.call_args.kwargs["attempt"], 2)
        self.assertIn("job_id=%s", log_info.call_args.args[0])
        self.assertEqual(log_info.call_args.args[1:], ("job-1", "place-1", "complete", 4))

    def test_service_bus_trigger_reraises_worker_exception_for_azure_retry(self) -> None:
        with patch(
            "function_app.process_menu_refresh_message",
            side_effect=RuntimeError("worker failed"),
        ):
            with self.assertRaises(RuntimeError):
                function_app.process_menu_refresh(FakeServiceBusMessage())


if __name__ == "__main__":
    unittest.main()
