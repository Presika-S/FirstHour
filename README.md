# FirstHour

**A stateful, voice-first MCP server for the first hour after a scam.** Built for the Amazon Developer Hackathon 2026, Alexa+ track (self-hosted MCP server, Streamable HTTP).

Someone who has just shared an OTP, installed a remote-access app or sent money is panicking, often mid-call, and does not know what to do first. FirstHour gives Alexa+ a deterministic playbook: triage what happened, read the next step aloud, count down the first hour, capture evidence, and produce the exact words to say to the bank or the 1930 helpline (India).

## Design choices
- **No LLM inside any tool.** Alexa+ does the language; the server does exact, reproducible logic. Measured locally: p95 about 3 ms per call (`python smoke_test.py`). The 500 ms figure is from Alexa's category add-on guide; check whether it applies to your add-on.
- **Stateless HTTP, incident state keyed by `incident_id`**, so any instance can serve any call (state is in memory in this build; use DynamoDB for production).
- **Jurisdiction-aware playbooks.** India (checked against public advisories, 2026-10-23) and US (**unverified: confirm before demo**).
- Tools: `start_incident`, `next_step`, `complete_step`, `record_evidence`, `get_call_script`, `get_status`.

## Run
```
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt httpx
python server.py            # MCP endpoint /mcp, simulator at /, health at /healthz
python smoke_test.py        # prints negotiated protocol version, asserts flows, measures latency
```
Set `PORT` to change the port. Behind a public hostname, you may need to allow that host in the MCP SDK's transport-security settings.

## What is real and what is not (say this in the submission)
- Real: the MCP server, Streamable HTTP, protocol negotiation (smoke test printed 2025-11-25), tools, tests.
- Simulated: Alexa+. The web page uses a keyword matcher in place of Alexa+'s model and calls the real `/mcp` endpoint.
- Not implemented: OAuth 2.1 with PKCE, and the MCP Apps UI. Alexa's docs list OAuth for onboarding, and Alexa AI CLI onboarding has not been tested.
- Not verified: US playbook steps; Alexa+ availability outside the US.
- New during the hackathon window: everything in this repo. If you reuse BankGuard scam categories, state that explicitly.

## Devpost text (draft)
**FirstHour** gives Alexa+ a calm, step-by-step plan for the first 60 minutes after a scam. Say what happened ("I told someone my OTP", "I installed AnyDesk"); the server triages it, reads one action at a time, runs a first-hour countdown, records evidence (amount, time, transaction ID, beneficiary) and generates a call script for the bank or India's 1930 helpline. Why voice: victims are stressed and on the phone. Why deterministic: no model in the tool path, so answers are exact, fast and testable. Built with: Python, MCP SDK (Streamable HTTP, protocol 2025-11-25), Starlette. Tracks: Alexa+. Product feedback: see friction log.

## Demo video (2:30)
0:00 Cold open: "I just gave a caller my OTP." Clock shows 60:00. 0:20 Triage and first step spoken. 0:50 "Done" advances; the checklist updates. 1:10 Record amount and transaction ID by voice. 1:30 "What do I say?" returns the filled script. 1:50 Switch to the US playbook. 2:05 Show the tool trace with real millisecond timings and the smoke test passing. 2:20 Close on what is next: OAuth, MCP Apps visual, real Alexa+ onboarding.
