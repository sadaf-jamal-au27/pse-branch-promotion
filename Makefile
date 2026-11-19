.PHONY: demo test rulesets

demo:
	python3 scripts/demo_matrix.py

test:
	python3 -m unittest discover -s tests -v

rulesets:
	python3 scripts/configure_rulesets.py --repo OWNER/github-abacus-task --tenant pse --caller-style local
