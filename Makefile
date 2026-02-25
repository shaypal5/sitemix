.PHONY: install-dev lint test

install-dev:
	pip install -e .[dev]

lint:
	ruff check .

test:
	pytest
