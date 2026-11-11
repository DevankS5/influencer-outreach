.PHONY: setup test run serve export
setup:
	python -m pip install -r requirements.txt
test:
	python -m pytest -q
run:
	python -m outreach.cli run --provider bluesky --limit 80
serve:
	python -m outreach.cli serve
export:
	python -m outreach.cli export
