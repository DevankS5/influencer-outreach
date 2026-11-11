# Owner to-do — credentials, decisions, verification and submission

All core prototype code is implemented. You do **not** need to write another integration module to use the included Bluesky pipeline, OpenAI-compatible LLM path, review dashboard or SMTP sender. This checklist covers external accounts, configuration, factual review and handoff. Optional YouTube and live sending are not required to view the delivered snapshot or demonstrate simulation.

## UI update: nothing extra to install

The visual redesign adds no new backend, framework or startup command. Open `dashboard-preview.html` for an offline, read-only preview without running code. To perform approval/simulation, use the existing dashboard server. Browse profile evidence in Overview; review and approve messages under Email pitch; Instagram DM is a separate manual-only tab. No extra coding action is needed for the redesign.

## 1. Run and inspect the supplied prototype — required

- [ ] Install Python 3.10+ and run the README setup commands.
- [ ] Copy `.env.example` to `.env`; keep `.env` private.
- [ ] Run `python -m pytest -q` and confirm all tests pass in your environment.
- [ ] Run `python scripts/restore_snapshot.py` if the local SQLite database is absent (for example after extracting the ZIP or cloning a repository).
- [ ] Start `python -m outreach.cli serve` and inspect the real supplied records.
- [ ] Open `data/export/influencers.csv`, `messages.csv`, and `outreach_tracker.csv`.
- [ ] Understand the final delivered counts: 100 discovered, 100 micro-range, 17 qualified, 57 emails across all profiles, **1 qualified profile with email**. Missing emails are not made up. Dataset is an observed snapshot, not a guarantee of continuing accuracy.

**Done when:** dashboard and exported evidence match, and you can explain why profiles pass/fail.

## 2. Supply the actual brand and campaign — required before real outreach

Edit these `.env` values; no Python changes are needed:

- [ ] `BRAND_NAME`: the authorized brand, not `Your Brand`.
- [ ] `BRAND_DESCRIPTION`: factual short description, no unverified claims.
- [ ] `CAMPAIGN_OFFER`: genuine paid/sponsorship/affiliate/UGC terms you can honor.
- [ ] `CAMPAIGN_ID`: one stable identifier for the genuine campaign. Do not change it just to bypass duplicate protection.
- [ ] Confirm budget, compensation, content deliverables, timeline, creative independence and advertising disclosures outside the system.
- [ ] Decide whether Technology and the current policy fit the brand. For the assignment, one complete category is already implemented. Unknown demographics must not be sold as a match.

**Done when:** the brand has authorized the offer and the campaign copy is accurate. Offline demo text is designed for paid educational collaboration; use the LLM path and review carefully for materially different campaign terms.

## 3. Connect a real LLM — required to submit an executed AI-personalized run

The current supplied messages are openly labeled **local fallback**, not AI model output. The AI client and prompt are already implemented.

- [ ] Create or use an account with OpenAI or a provider offering compatible `/chat/completions` and JSON response mode.
- [ ] Enable billing/credits, choose a spending limit, and verify a model is accessible to the account.
- [ ] Set `LLM_API_KEY` in `.env`.
- [ ] Set `LLM_MODEL` to your accessible model identifier (`gpt-4o-mini` is the default configuration, not a promise of account access).
- [ ] Set `LLM_BASE_URL` only if using another compatible provider; it should end at the API version root, **not** `/chat/completions`.
- [ ] Review provider retention/privacy terms and authorize transmitting public profile excerpts to that service.
- [ ] Run `python -m outreach.cli generate --generator llm --overwrite`.
- [ ] Inspect event logs/errors if the provider rejects JSON mode, quota, authentication or model access. Choose a compatible provider/model rather than disabling output validation.
- [ ] Inspect every generated pitch: 60–90 whitespace-separated words; each DM: 15–30. Review facts and tone, not just lengths.
- [ ] Run `python -m outreach.cli export` and confirm `messages.csv` contains `llm:<model>` generator values.
- [ ] Review/approve messages again; regeneration intentionally clears earlier approval.

**Done when:** the exported messages are actual reviewed model responses and the demo honestly shows which model was used. API costs are your account's responsibility.

## 4. Refresh discovery and verify contacts — required before outreach

- [ ] Confirm permission/terms for your source use and keep requests conservative.
- [ ] Run `python -m outreach.cli run --provider bluesky --limit 100 --generator llm` for a fresh end-to-end run, once your model key is configured. Existing drafts are preserved; use the explicit overwrite command above after rediscovery where appropriate.
- [ ] Use a separate `DATABASE_PATH` for a completely independent experiment, or preserve the original snapshot before exporting again.
- [ ] Broaden query sets if you need a higher yield. Discovery count is not the same as qualified or contactable count.
- [ ] Open the `email_source` for each contact. Confirm the literal email belongs to the creator and is appropriate for collaborations. Emails in quoted posts may belong to third parties.
- [ ] Verify creator identity, activity, recent content, micro-range followers and brand suitability manually. Keyword filtering is not an identity or brand-safety certificate.
- [ ] If enabling `--crawl-web`, review the source websites' terms and applicable privacy rules. Do not bypass robots/login/access restrictions.
- [ ] If required, request media kits or creator-provided audience geography/age/gender evidence. The system deliberately does not infer them.
- [ ] Keep unverified or unavailable contacts as `Not Found` rather than creating guesses. You do not need to source an email for every failed record.

**Done when:** every approved contact has current evidence and a lawful, appropriate purpose.

## 5. Optional: enable YouTube discovery

Only needed if you want this additional platform or the evaluator insists on it. The source adapter is implemented; it has not been live-tested with your account.

- [ ] Create a Google Cloud project and enable **YouTube Data API v3**.
- [ ] Create an API key, restrict it to that API, and follow the provider's key security guidance.
- [ ] Set `YOUTUBE_API_KEY` in `.env`.
- [ ] Check daily quota and expected costs. Channel searches are relatively expensive; avoid excessive queries.
- [ ] Run `python -m outreach.cli run --provider youtube --limit 60 --query 'software tutorials' --generator llm`.
- [ ] Inspect source errors/quota and increase permitted quota or narrow queries if needed.
- [ ] Verify API data retention/refresh requirements. Hidden subscriber and engagement counters must stay missing, not zero-filled.

**Done when:** a genuine official API run returns enough source-backed channels and qualified profiles are reviewed.

## 6. Review and simulate — required demonstration, no email account needed

- [ ] Choose a qualified contact with a valid source-backed email.
- [ ] Read the source evidence and the generated email/DM in the dashboard.
- [ ] Approve that creator's reviewed message through the dashboard or `approve --id`.
- [ ] Click **Simulate email**, or run `python -m outreach.cli send` without `--live`.
- [ ] Repeat simulation and show `duplicate_skipped`.
- [ ] Export and verify `mode=simulation`, `status=simulated`, `sent=False`.
- [ ] Demonstrate that missing-email/unapproved/failed records are not sent.

The delivered dataset already includes one genuine-contact simulation and repeat-attempt evidence. `scripts/restore_snapshot.py` restores profiles/drafts only, so a clean local demo needs its own review and simulation.

**Done when:** your video/dashboard clearly differentiates simulated from real delivery.

## 7. Optional: authorize real SMTP sending

Simulation is an accepted assignment option. Do this only if you actually intend and are authorized to contact creators.

- [ ] Choose an email provider that explicitly permits your lawful use case and supports authenticated TLS SMTP.
- [ ] Obtain the SMTP host, port (587 or 465), username, password/app password, and authorized From address from that provider.
- [ ] Fill `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` in `.env`.
- [ ] Configure/verify sender domain **SPF, DKIM and DMARC** where applicable; follow the provider's instructions and applicable sender-identification rules.
- [ ] Verify sender reputation, provider rate limits and permission to send. Use low volume.
- [ ] Check applicable privacy/direct-marketing rules with appropriate guidance. Publicly listed email is not automatically consent.
- [ ] Supply any legally required business identity/address/disclosures in the campaign copy and confirm a working reply/opt-out channel. The sender adds a simple reply-to-opt-out instruction, but that is not a legal compliance guarantee.
- [ ] Verify the actual brand/offer configuration and approve only final reviewed messages.
- [ ] Set `LIVE_SEND_ENABLED=yes` only for the intended test window.
- [ ] For a controlled first live test, use your own authorized test contact in a **separate test database**, never replace real discovered profiles with invented data in the submission dataset. The synthetic test suite itself never uses live delivery.
- [ ] Run `python -m outreach.cli send --live --id 'the-real-reviewed-profile-id'` only when ready.
- [ ] Check the provider's sent/delivery/bounce records; `sent` in this system is SMTP acceptance, not inbox delivery.
- [ ] For `sending` or `unknown`, reconcile using `message_id` and provider logs. Do not blindly retry or delete deduplication records.
- [ ] Monitor replies and apply `python -m outreach.cli suppress --email 'redacted@example.com' --reason 'Opt-out'` for opt-outs. Maintain appropriate records and retention/deletion rules.
- [ ] Return `LIVE_SEND_ENABLED=no` after testing if ongoing sending is not intended.

**Done when:** provider-side evidence and application tracker agree, and opt-outs can be honored. No live SMTP or mailbox verification has been performed in the delivered run.

## 8. Instagram DMs — manual workflow only

- [ ] Verify that a shortlisted creator actually has an Instagram account; confirm the official handle independently.
- [ ] Review the supplied DM draft for the actual offer and content source.
- [ ] Copy the draft and send manually only where appropriate/permitted, or leave it as an explicitly simulated draft for the assignment.
- [ ] Keep a separate manual note/screenshot if demonstrating a permitted send. Do not label a copied draft as delivered.
- [ ] Do not use password-sharing bots, headless login automation or unofficial DM APIs to bypass restrictions.

**Done when:** the submission accurately distinguishes generated drafts from actual communication. No Instagram credentials are required by this prototype.

## 9. Optional deployment and secrets

- [ ] Choose local-only usage or your hosting provider. Local loopback is simplest.
- [ ] For a hosted server, set `HOST=0.0.0.0` and a newly generated `DASHBOARD_TOKEN` of at least 24 characters. The demonstration token, if provided, is not a production secret.
- [ ] Put the prototype behind HTTPS and an authenticated reverse proxy; configure a private deployment and persistent `data/` storage.
- [ ] Configure managed secrets and network egress restrictions; do not expose the standard-library server directly as a production service.
- [ ] Back up the SQLite data securely, define retention/deletion, and restrict access to contact data.
- [ ] Never commit `.env`, real tokens, SMTP passwords, API keys or unreviewed personal-data logs.

## 10. Final submission — required

- [ ] Create your own private/public Git repository as appropriate, or submit the included ZIP/project files.
- [ ] Decide whether publishing creator contact details is justified and lawful. Prefer a private evaluator-access repository or redact **public** copies while retaining the source-backed private submission.
- [ ] Include README, architecture, this checklist, source code, test output, final dataset, messages and outreach tracker.
- [ ] If you ran the LLM, export and replace the fallback message artifacts with your actual reviewed AI outputs while retaining honest generator labels.
- [ ] Record a short demonstration using `docs/demo.md`: discovery → evidence → filter reasons → draft → review → simulation → duplicate prevention → tracker.
- [ ] Explain explicitly: real observations, unknown demographics, source-specific engagement proxy, missing emails, manual-only DMs, and which optional integrations were not activated.
- [ ] Verify a fresh extraction/cloning setup works using requirements and restore instructions.
- [ ] Submit the repository link/archive and demo link/screenshots/video through the assignment's official channel.

**Acceptance note:** the code and default public-source demonstration are complete. The principal remaining evaluation gap is an **executed real LLM generation run with your account**; the delivered local fallback must not be misrepresented as one. Live email sending is optional because simulation is expressly permitted.
