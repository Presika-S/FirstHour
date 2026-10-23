"""Run against a live server: python smoke_test.py [http://127.0.0.1:8000/mcp]. Prints measured protocol version and latency."""
import json, statistics, sys, time
import httpx
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
H = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
c, n = httpx.Client(timeout=10), 0

def rpc(method, params=None):
    global n; n += 1
    r = c.post(URL, headers=H, json={"jsonrpc": "2.0", "id": n, "method": method, "params": params or {}})
    r.raise_for_status(); return r.json()["result"]

def call(name, **a):
    res = rpc("tools/call", {"name": name, "arguments": a})
    d = res.get("structuredContent") or json.loads(res["content"][0]["text"])
    return d.get("result", d) if list(d) == ["result"] else d

init = rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}})
print("negotiated protocol:", init["protocolVersion"])
tools = {t["name"] for t in rpc("tools/list")["tools"]}
assert {"start_incident", "next_step", "complete_step", "record_evidence", "get_call_script", "get_status"} <= tools
a = call("start_incident", country="IN", scam_type="remote_app")
assert a["current_step"] == "disconnect" and a["minutes_left"] == 60
iid = a["incident_id"]
assert call("complete_step", incident_id=iid)["current_step"] == "bank"
call("record_evidence", incident_id=iid, field="amount", value="Rs 25,000")
assert "Rs 25,000" in call("get_call_script", incident_id=iid, target="helpline")["script"]
assert call("next_step", incident_id="nope")["error"] == "unknown_incident"
lat = []
for _ in range(200):
    t = time.perf_counter(); call("next_step", incident_id=iid); lat.append((time.perf_counter() - t) * 1000)
lat.sort()
print(f"next_step over HTTP: p50 {statistics.median(lat):.1f} ms, p95 {lat[189]:.1f} ms (local, measured now)")
print("ALL CHECKS PASSED")
