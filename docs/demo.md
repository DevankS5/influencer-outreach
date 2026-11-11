# Working demonstration script (3–5 minutes)

## No-setup visual preview

Open `dashboard-preview.html` directly. It includes the actual observations and supports browsing without any code execution or server setup. It is explicitly read-only, so review/sending actions are disabled with an explanation. For the operational demo below, use the same server as before.

## 0. Restore and launch

```bash
python -m pip install -r requirements.txt
python scripts/restore_snapshot.py
python -m outreach.cli serve
```

Open `http://127.0.0.1:8000`. If using the temporary hosted preview created with this deliverable, enter `signal-demo-access-2026-local` in the token field and Connect. This is a demonstration access token, **not a production credential**; replace it in any deployment.

## 1. Show discovery and truthful data

Show 100 actual public profiles. Open `data/export/profiles.json`: profile URLs, observation times and original content URLs are present. All 100 observed audience counts are in micro range, but that does not mean every discovered profile is a good-fit individual creator. Mention that searches include irrelevant/organizational results and filtering rejects them.

A fresh run requires network but no Bluesky key:

```bash
# Separate database protects the supplied observation snapshot:
DATABASE_PATH=data/fresh.sqlite3 python -m outreach.cli discover --provider bluesky --limit 60
```

On Windows set `DATABASE_PATH` using PowerShell environment syntax instead. Fresh results change over time. The default `run` command exports to `data/export`, so preserve originals before rerunning it.

## 2. Show classification

Filter to **Qualified**, then **Not qualified**. Inspect failure reasons, content evidence, technical bio, follower limits and source-specific engagement proxy. Explain that audience age/gender/geography are unknown, and no demographic facts are invented.

## 3. Show enrichment and personalization

Find **Andy Greenberg** (`did:plc:zbxq6fbw575t4nakfot3epen` in the supplied snapshot). Open the email-source profile and verify the bio contains the exact address. Use the Email pitch and Instagram DM tabs to show drafts, word counts and generator labels. The Overview tab contains bio, contact provenance, qualification notes and real content evidence. Demonstrate a second qualified creator with `Not Found` email: a draft can exist but sending is disabled.

The delivered run is an offline fallback, not LLM-generated. With your API key configured:

```bash
python -m outreach.cli generate --generator llm --overwrite
python -m outreach.cli export
```

Show actual `llm:<model>` output only if you performed that run. Regeneration clears approval.

## 4. Review and simulate

On a fresh restored database, open the **Email pitch** tab, approve the reviewed qualified contact and click **Simulate email**. No SMTP network call occurs. Try again: `duplicate_skipped`. If the bundled runtime database already has the demo simulation, the existing log is the evidence; do not delete it to make a second attempt look new.

CLI equivalent for this genuine delivered record:

```bash
python -m outreach.cli approve --id did:plc:zbxq6fbw575t4nakfot3epen
python -m outreach.cli send
python -m outreach.cli send
python -m outreach.cli export
```

No `--live` flag. Show tracker `mode=simulation`, `status=simulated`, `sent=False`. Explain unique constraints prevent race-condition duplicates and a live attempt has a different namespace than a simulation.

## 5. Show DM safety and tests

Copy an Instagram-ready DM. Explain it is a draft, and the actual Instagram handle/account must be verified manually. No automated Instagram send is claimed.

```bash
python -m pytest -q
```

Show passing tests and `to-do.md`: owner supplies API credentials, real brand terms, lawful contact review, optional SMTP/domain settings and submission assets. End on the exported influencer dataset, messages, tracker and architecture document.
