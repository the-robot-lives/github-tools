#!/usr/bin/env python3
"""Scripted stand-in for `gh` / `kubectl` used by tests/test_gh_wait.py.

Installed on PATH as `gh` and `kubectl` (symlinks). Reads the scenario from
$FAKE_SCENARIO (JSON): {"<tool>": [{"match": [tokens...], "responses": [...]}]}.
The first rule whose tokens all appear in argv wins; its responses are served
in order (the last one repeats). Each response: {"stdout": str|obj, "rc": int,
"stderr": str}. Calls are appended to $FAKE_STATE/calls.log.
"""
import json
import os
import sys

tool = os.path.basename(sys.argv[0])
argv = sys.argv[1:]
state_dir = os.environ["FAKE_STATE"]
with open(os.path.join(state_dir, "calls.log"), "a") as fh:
    fh.write(json.dumps([tool, *argv]) + "\n")

with open(os.environ["FAKE_SCENARIO"]) as fh:
    scenario = json.load(fh)

for idx, rule in enumerate(scenario.get(tool, [])):
    if all(tok in argv for tok in rule["match"]):
        counter = os.path.join(state_dir, f"{tool}.{idx}.count")
        n = int(open(counter).read()) if os.path.exists(counter) else 0
        with open(counter, "w") as fh:
            fh.write(str(n + 1))
        resp = rule["responses"][min(n, len(rule["responses"]) - 1)]
        out = resp.get("stdout", "")
        if not isinstance(out, str):
            out = json.dumps(out)
        sys.stdout.write(out)
        sys.stderr.write(resp.get("stderr", ""))
        sys.exit(resp.get("rc", 0))

sys.stderr.write(f"fake {tool}: no rule for {argv}\n")
sys.exit(99)
