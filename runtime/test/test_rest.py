from __future__ import annotations

import unittest

from pydantic import BaseModel

from geosprite.eo.tools import Tool, ToolContext, ToolRegistry
from geosprite.eo.tools.runtime.adapters.rest import create_app


class EchoIn(BaseModel):
    value: str


class EchoOut(BaseModel):
    value: str


class EchoTool(Tool[EchoIn, EchoOut]):
    name = "echo"
    domain = "catalog"
    summary = "Echo input."
    InputModel = EchoIn
    OutputModel = EchoOut

    async def run(self, ctx: ToolContext, inputs: EchoIn) -> EchoOut:
        return EchoOut(value=inputs.value)


class RestServicePathTests(unittest.TestCase):
    def test_service_path_moves_service_endpoints_without_prefixing_tool_routes(self):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI test client is not installed")

        registry = ToolRegistry()
        registry.register(EchoTool())
        app = create_app(registry, root_path="/eo-tools", service_path="/catalog")
        client = TestClient(app)

        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/catalog/health").status_code, 200)
        self.assertEqual(client.get("/catalog/").status_code, 200)
        self.assertEqual(client.get("/catalog/openapi.json").status_code, 200)
        self.assertEqual(client.get("/catalog/docs").status_code, 200)

        schema = client.get("/catalog/openapi.json").json()
        self.assertIn("/catalog/echo", schema["paths"])
        self.assertIn("/catalog/health", schema["paths"])
        self.assertNotIn("/catalog/catalog/echo", schema["paths"])


if __name__ == "__main__":
    unittest.main()
