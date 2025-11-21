.PHONY: lint release

lint:
	@echo "Running linters... 🔄"
	pre-commit install
	pre-commit run -a
	@echo "Linters completed. ✅"

release:
	@python tools/prepare_release.py
	@uv sync
	@uv lock --upgrade
