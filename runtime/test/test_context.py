from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from geosprite.eo.tools.runtime.core import store_context_factory


class RuntimeContextTests(unittest.TestCase):
    def test_store_context_factory_allows_missing_store_without_config(self):
        def fail_import(name, *args, **kwargs):
            if name == "geosprite.eo.store":
                raise ImportError("missing eo-store")
            return original_import(name, *args, **kwargs)

        original_import = __import__
        with patch("builtins.__import__", side_effect=fail_import):
            ctx = store_context_factory(workdir="C:/work")("run-1")

        self.assertIsNone(ctx.store)
        self.assertEqual(str(ctx.workdir), "C:\\work")
        self.assertEqual(ctx.run_id, "run-1")

    def test_store_context_factory_uses_default_store_without_config_when_available(self):
        class Store:
            @staticmethod
            def with_defaults() -> object:
                return {"store": "default"}

        fake_store_module = SimpleNamespace(Store=Store)
        with patch.dict("sys.modules", {"geosprite.eo.store": fake_store_module}):
            ctx = store_context_factory(workdir="C:/work")("run-1")

        self.assertEqual(ctx.store, {"store": "default"})
        self.assertEqual(str(ctx.workdir), "C:\\work")
        self.assertEqual(ctx.run_id, "run-1")

    def test_store_context_factory_lazy_loads_store_when_config_is_supplied(self):
        calls: list[str] = []

        class Store:
            @staticmethod
            def with_config(path: str) -> object:
                calls.append(path)
                return {"store": path}

        fake_store_module = SimpleNamespace(Store=Store)
        with patch.dict("sys.modules", {"geosprite.eo.store": fake_store_module}):
            ctx = store_context_factory(store_config="store.json")()

        self.assertEqual(calls, ["store.json"])
        self.assertEqual(ctx.store, {"store": "store.json"})


if __name__ == "__main__":
    unittest.main()
