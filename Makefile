.PHONY: init
init:
	@uv sync

.PHONY: ci
ci:
	@uvx tox run-parallel -m ci --parallel-no-spinner --parallel-live

.PHONY: dev
dev:
	pip install --editable .

.PHONY: install
install:
	pip install .

.PHONY: dist
dist:
	uv run python setup.py sdist

.PHONY: clean
clean:
	@rm -rf build dist .pytest_cache .tox
	@find . -name "*.egg" -exec rm -rf {} +
	@find . -name "*.egg-info" -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -exec rm -rf {} +
