"""FirstHour: a stateful, deterministic MCP server (Streamable HTTP) for the first hour after a scam.
No LLM runs inside any tool, so responses stay fast and exactly reproducible.
Alexa+ (or any MCP client) supplies the language understanding; this server supplies the playbook."""
import os, time, uuid
from pathlib import Path
from typing import Literal
from mcp.server.fastmcp import FastMCP
from starlette.responses import FileResponse, JSONResponse

mcp = FastMCP("FirstHour", stateless_http=True, json_response=True,
              host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))

Country = Literal["IN", "US"]
Scam = Literal["otp_shared", "remote_app", "payment_sent", "card_details", "link_clicked"]
Field = Literal["amount", "time", "method", "txn_id", "beneficiary", "contact"]

# Suggested pacing in minutes since discovery. Our pacing, NOT an official deadline.
COMMON = {
    "disconnect": ("Cut the scammer off", "Hang up. If you installed a remote-access app, uninstall it and switch off wifi and mobile data on that device.", 3),
    "creds": ("Change passwords", "From a different, clean device, change your banking and email passwords and turn on two-step login.", 40),
}
LIB = {
    "IN": {
        "bank": ("Call your bank or UPI app", "Call your bank's fraud line or your UPI app's support now. Ask them to block further transactions and register a fraud complaint.", 5),
        "helpline": ("Call 1930", "If money left your account, call 1930, the national cyber fraud helpline, now. Early reports give the best chance of a freeze.", 10),
        "portal": ("File on cybercrime.gov.in", "File the complaint at cybercrime dot gov dot in. Keep screenshots and transaction details ready.", 45),
        **COMMON,
    },
    "US": {
        "bank": ("Call your bank or card issuer", "Call the number on the back of your card or your bank's fraud line. Ask them to stop or reverse the payment and lock the account.", 5),
        "ic3": ("Report to the FBI's IC3", "If money was wired or sent online, also report it at i c 3 dot gov.", 30),
        "ftc": ("Report to the FTC", "Report the scam at reportfraud dot ftc dot gov.", 45),
        "credit": ("Fraud alert on your credit", "Ask the credit bureaus for a fraud alert or a freeze, since your personal details were exposed.", 40),
        **COMMON,
    },
}
ORDER = {
    "IN": {"otp_shared": ["bank", "helpline", "portal", "creds"],
           "remote_app": ["disconnect", "bank", "helpline", "portal", "creds"],
           "payment_sent": ["helpline", "bank", "portal"],
           "card_details": ["bank", "helpline", "portal"],
           "link_clicked": ["disconnect", "creds", "bank", "portal"]},
    "US": {"otp_shared": ["bank", "creds", "ftc"],
           "remote_app": ["disconnect", "bank", "creds", "credit", "ftc"],
           "payment_sent": ["bank", "ic3", "ftc"],
           "card_details": ["bank", "credit", "ftc"],
           "link_clicked": ["disconnect", "creds", "bank", "ftc"]},
}
SOURCE_STATUS = {"IN": "Checked against public Indian government and bank advisories, 2026-10-23.",
                 "US": "UNVERIFIED: confirm every US step against official sources before relying on it."}
LIMITS = "Not legal or financial advice. Pacing targets are suggestions, not official limits."
INCIDENTS: dict = {}


def _view(inc_id, inc, speech, **extra):
    now = time.time()
    lib = LIB[inc["country"]]
    checklist = [{"id": s, "title": lib[s][0], "target_min": lib[s][2], "done": s in inc["done"]} for s in inc["steps"]]
    left = max(0, 60 - int((now - inc["started"]) // 60))
    return {"incident_id": inc_id, "speech": speech, "minutes_left": left,
            "started_at_ms": int(inc["started"] * 1000), "checklist": checklist,
            "evidence": inc["evidence"], "source_status": SOURCE_STATUS[inc["country"]], **extra}


def _get(inc_id):
    inc = INCIDENTS.get(inc_id)
    return inc, (None if inc else {"error": "unknown_incident",
                                  "speech": "I can't find that incident. Say start over and tell me what happened."})


def _next(inc):
    return next((s for s in inc["steps"] if s not in inc["done"]), None)


@mcp.tool()
def start_incident(country: Country, scam_type: Scam, minutes_since_discovery: int = 0) -> dict:
    """Start a scam-response incident. scam_type: otp_shared (gave a code or PIN), remote_app (installed a remote-access or screen-share app), payment_sent (sent money), card_details (gave card number), link_clicked (opened a suspicious link or app)."""
    inc_id = uuid.uuid4().hex[:8]
    inc = {"country": country, "scam": scam_type, "steps": ORDER[country][scam_type], "done": set(),
           "evidence": {}, "started": time.time() - max(0, min(minutes_since_discovery, 59)) * 60}
    INCIDENTS[inc_id] = inc
    first = LIB[country][inc["steps"][0]]
    return _view(inc_id, inc, f"Stay calm, we have a plan. Step one: {first[1]}", current_step=inc["steps"][0], disclaimer=LIMITS)


@mcp.tool()
def next_step(incident_id: str) -> dict:
    """Read the next unfinished step for this incident."""
    inc, err = _get(incident_id)
    if err: return err
    s = _next(inc)
    if not s:
        return _view(incident_id, inc, "Every step is done. Keep your evidence. Say script if you want the words to use on a call.")
    t = LIB[inc["country"]][s]
    return _view(incident_id, inc, t[1], current_step=s)


@mcp.tool()
def complete_step(incident_id: str, step_id: str = "") -> dict:
    """Mark a step done (defaults to the current step) and return the next one."""
    inc, err = _get(incident_id)
    if err: return err
    sid = step_id or _next(inc)
    if sid not in inc["steps"]:
        return _view(incident_id, inc, "That step isn't in your plan.")
    inc["done"].add(sid)
    s = _next(inc)
    if not s:
        return _view(incident_id, inc, "That was the last step. Keep your screenshots and receipts safe.")
    return _view(incident_id, inc, f"Done. Next: {LIB[inc['country']][s][1]}", current_step=s)


@mcp.tool()
def record_evidence(incident_id: str, field: Field, value: str) -> dict:
    """Save one fact for the complaint: amount, time, method, txn_id, beneficiary or contact."""
    inc, err = _get(incident_id)
    if err: return err
    inc["evidence"][field] = value[:200]
    return _view(incident_id, inc, f"Saved {field.replace('_', ' ')}.")


@mcp.tool()
def get_call_script(incident_id: str, target: Literal["helpline", "bank"] = "bank") -> dict:
    """Return the words to say on a call, filled with recorded evidence."""
    inc, err = _get(incident_id)
    if err: return err
    e = {k: inc["evidence"].get(k, "not recorded") for k in ("amount", "time", "method", "txn_id", "beneficiary", "contact")}
    who = "the national cyber fraud helpline" if target == "helpline" and inc["country"] == "IN" else "my bank's fraud team"
    script = (f"Hello, I am calling {who} to report online fraud. I lost {e['amount']} at {e['time']} by {e['method']}. "
              f"Transaction reference: {e['txn_id']}. The money went to: {e['beneficiary']}. The scammer contacted me via: {e['contact']}. "
              "Please block further transactions and register a complaint. Can you give me a reference number?")
    return _view(incident_id, inc, script, script=script)


@mcp.tool()
def get_status(incident_id: str) -> dict:
    """Minutes left in the first hour, steps done and evidence saved."""
    inc, err = _get(incident_id)
    if err: return err
    d = len(inc["done"])
    return _view(incident_id, inc, f"{d} of {len(inc['steps'])} steps done. About {max(0, 60 - int((time.time() - inc['started']) // 60))} minutes left in the first hour.")


@mcp.custom_route("/", methods=["GET"])
async def home(request):
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@mcp.custom_route("/healthz", methods=["GET"])
async def health(request):
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
