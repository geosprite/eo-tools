from __future__ import annotations

import unittest

from geosprite.eo.tools.runtime.adapters.cli import build_parser


class RuntimeCliTests(unittest.TestCase):
    def test_run_parser_defaults_store_config_to_none(self):
        args = build_parser().parse_args(
            ["run", "raster.compose", "--workdir", "C:/work"]
        )

        self.assertEqual(args.workdir, "C:/work")
        self.assertIsNone(args.store_config)

    def test_run_parser_accepts_optional_store_config(self):
        args = build_parser().parse_args(
            [
                "run",
                "raster.compose",
                "--workdir",
                "C:/work",
                "--store-config",
                "store.json",
            ]
        )

        self.assertEqual(args.store_config, "store.json")

    def test_serve_parsers_accept_optional_store_config(self):
        rest_args = build_parser().parse_args(
            ["serve-rest", "--store-config", "store.json"]
        )
        mcp_args = build_parser().parse_args(
            ["serve-mcp", "--store-config", "store.json"]
        )

        self.assertEqual(rest_args.store_config, "store.json")
        self.assertEqual(mcp_args.store_config, "store.json")

    def test_serve_rest_accepts_service_path(self):
        args = build_parser().parse_args(
            ["serve-rest", "--root-path", "/eo-tools", "--service-path", "/catalog"]
        )

        self.assertEqual(args.root_path, "/eo-tools")
        self.assertEqual(args.service_path, "/catalog")


if __name__ == "__main__":
    unittest.main()
