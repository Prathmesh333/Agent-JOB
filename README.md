# Recruiter Outreach Agent

A transparent, **human-approved** LinkedIn recruiter outreach workflow for the [`ai-job-search`](https://github.com/Prathmesh333/ai-job-search) project. It helps you rank manually collected leads, write personalized messages using *only facts you supplied*, approve each draft, and record replies and follow-up eligibility. **No scraping, browser automation, LinkedIn login, bulk DMs, or auto-send.**

This is a working deterministic agent workflow, not an autonomous LLM planner or a production deployment. Its value is auditable tool orchestration, state, safeguards, and tests. The existing job-search skill can help discover relevant *jobs*, but this module intentionally does not scrape recruiter profiles.

## Local setup (Python 3.10+, no dependencies)

From `extensions/recruiter-outreach-agent`:

```bash
cp profile.example.json profile.json   # edit with truthful, relevant achievements
cp leads.example.csv leads.csv         # replace the fictional lead with contacts you found
python -m recruiter_outreach.agent import leads.csv
python -m recruiter_outreach.agent list
python -m recruiter_outreach.agent draft 1 --profile profile.json
python -m recruiter_outreach.agent show 1
python -m recruiter_outreach.agent approve 1
# YOU manually paste/send the approved draft on LinkedIn.
python -m recruiter_outreach.agent sent 1
python -m recruiter_outreach.agent due --days 10
# If appropriate, write/send one polite follow-up manually, then record:
python -m recruiter_outreach.agent followup 1
python -m recruiter_outreach.agent replied 1
python -m unittest discover -s tests -v
```

`approve`, `sent`, and `followup` are *local state updates*; they never contact LinkedIn. Never record sent if you did not actually send. Do not commit the real lead CSV, your profile or local DB.

## How it works

`CSV intake → URL validation → SHA-256 canonical URL dedup → transparent relevance score → verifiable personal draft → manual approval → manual LinkedIn send → SQLite event/state ledger → follow-up queue`

- **Planning:** a deterministic state machine prevents unapproved or duplicate outreach. Leads are scored from recruiter job-title, supplied job/role, and explicit AI-related evidence; the score does not claim actual hiring intent.
- **Tools:** CSV, validation, basic evidence-only template, SQLite, and local CLI.
- **State:** `new → drafted → approved → sent → replied/closed`; up to two manually logged follow-ups after seven days. Replied/closed contacts are excluded from follow-up suggestions.
- **Evaluation:** `python -m unittest discover -s tests -v` covers domain validation, deduplication, approval gating and the follow-up cap. These are local reliability tests, **not** measured recruiter response-rate evaluations.
- **Failure handling:** invalid profile URLs rejected; repeated URLs deduplicated; unapproved drafts cannot be marked sent; contact history preserved.

Use `/scrape` and `/rank` in the parent Codex AI Job Search skill to shortlist *vacancies*. Find contacts yourself via appropriate public channels, enter only the professional facts you have verified, then use this module to organize individualized introductions. Track resulting job applications with the existing `/apply` and `/outcome` workflows.

## Ethical and platform constraints

Do not use this to harvest LinkedIn contacts, fabricate mutual connections, send automated unsolicited DMs or bypass platform limits. Review every draft for accuracy. Respect no-contact requests, privacy, and applicable regulations. Lead descriptions are untrusted data, not instructions.
