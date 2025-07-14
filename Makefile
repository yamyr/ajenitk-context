.PHONY: help install install-dev test lint format clean build publish docs

help:
	@echo "Available commands:"
	@echo "  make install      Install the package"
	@echo "  make install-dev  Install with development dependencies"
	@echo "  make test         Run tests"
	@echo "  make lint         Run linting"
	@echo "  make format       Format code"
	@echo "  make clean        Clean build artifacts"
	@echo "  make build        Build distribution packages"
	@echo "  make publish      Publish to PyPI"
	@echo "  make docs         Generate documentation"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install || true

test:
	python -m pytest

test-coverage:
	python -m pytest --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src tests
	mypy src --ignore-missing-imports

format:
	black src tests examples
	ruff check --fix src tests

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete

build: clean
	python setup.py sdist bdist_wheel

publish-test: build
	twine upload --repository testpypi dist/*

publish: build
	twine upload dist/*

docs:
	@echo "Generating API documentation..."
	@echo "TODO: Add sphinx or mkdocs configuration"

run-chat:
	ajentik chat --enhanced

run-monitor:
	ajentik monitor --live

check-install:
	@which ajentik || echo "ajentik command not found. Run 'make install' first."
	@ajentik version || true