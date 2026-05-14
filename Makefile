.PHONY: test-migration test-migration-offline

test-migration:
	pytest tests/migration/ -v --tb=short

test-migration-offline:
	pytest tests/migration/ -m "not external and not llm" -v --tb=short
