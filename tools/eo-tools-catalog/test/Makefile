.PHONY: help test test-simple test-pytest test-msi test-sar test-match test-utility test-all install clean

help:
	@echo "EO Tools Catalog API - Test Commands"
	@echo "===================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make test              - Run simple test (recommended)"
	@echo "  make test-all          - Run full pytest suite"
	@echo ""
	@echo "Test Categories:"
	@echo "  make test-msi          - Test MSI search functionality"
	@echo "  make test-sar          - Test SAR search functionality"
	@echo "  make test-match        - Test multi-collection matching"
	@echo "  make test-utility      - Test utility endpoints"
	@echo ""
	@echo "Setup:"
	@echo "  make install           - Install test dependencies"
	@echo "  make clean             - Clean test artifacts"
	@echo ""
	@echo "Details:"
	@echo "  make test-pytest       - Run pytest with verbose output"

test:
	@echo "Running simple test suite..."
	python test_catalog_api_simple.py

test-simple:
	@echo "Running simple test suite..."
	python test_catalog_api_simple.py

test-all:
	@echo "Running full pytest suite..."
	pytest test_catalog_api_pytest.py -v

test-pytest:
	@echo "Running pytest with verbose output..."
	pytest test_catalog_api_pytest.py -vv --tb=short

test-msi:
	@echo "Running MSI search tests..."
	pytest test_catalog_api_pytest.py -v -m msi

test-sar:
	@echo "Running SAR search tests..."
	pytest test_catalog_api_pytest.py -v -m sar

test-match:
	@echo "Running multi-collection match tests..."
	pytest test_catalog_api_pytest.py -v -m match

test-utility:
	@echo "Running utility endpoint tests..."
	pytest test_catalog_api_pytest.py -v -m utility

install:
	@echo "Installing test dependencies..."
	pip install -r test_requirements.txt

install-minimal:
	@echo "Installing minimal dependencies (requests only)..."
	pip install requests

clean:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache __pycache__ *.pyc .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"
