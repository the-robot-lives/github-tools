INSTALL_DIR ?= $(HOME)/.local/bin
LIB_INSTALL_DIR ?= $(HOME)/.local/share/github-utils

.PHONY: compile build test install install-gh-wait clean docs

compile:
	@python3 -m py_compile lib/submodule_status.py
	@echo "✓ compile lib/submodule_status.py"
	@python3 -c 'import ast,sys; ast.parse(open("bin/gh-wait").read())'
	@echo "✓ compile bin/gh-wait"

build: compile

test: compile
	@bash -n bin/submodule-commit && echo "✓ bin/submodule-commit"
	@bash -n bin/submodule-status && echo "✓ bin/submodule-status"
	@python3 tests/test_submodule_status.py
	@python3 tests/test_gh_wait.py

install: compile
	@mkdir -p $(INSTALL_DIR)
	@for f in bin/submodule-* bin/gh-wait; do \
		install -m 755 "$$f" "$(INSTALL_DIR)/$$(basename $$f)"; \
		echo "✓ Installed $$(basename $$f)"; \
	done
	@mkdir -p $(LIB_INSTALL_DIR)
	@install -m 644 lib/submodule_status.py "$(LIB_INSTALL_DIR)/submodule_status.py"
	@echo "✓ Installed lib/submodule_status.py -> $(LIB_INSTALL_DIR)/submodule_status.py"

install-gh-wait:
	@mkdir -p $(INSTALL_DIR)
	@install -m 755 bin/gh-wait "$(INSTALL_DIR)/gh-wait"
	@echo "✓ Installed gh-wait"

docs:
	@python3 -m pip install -q -r docs/requirements.txt
	@python3 -m sphinx -b html docs docs/_build/html
	@echo "✓ docs → docs/_build/html/index.html"

clean:
	@find . -name '*.pyc' -delete
	@find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -rf docs/_build
