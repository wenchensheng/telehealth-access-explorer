.PHONY: all test serve verify
all: ; python run_all.py
test: ; pytest -q
serve: ; python -m http.server -d docs 8000
verify: ; python scripts/verify_mobile.py
