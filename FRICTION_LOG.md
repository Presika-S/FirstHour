# Friction log (fill in as you go; only log what actually happened to you)

| # | Tool / API | Task I attempted | Steps | Expected | Actual | Severity | Workaround | Suggestion |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | critical / important / nice-to-have | | |

Seed observations from this build (confirm they match your experience before submitting):
- Python `mcp` 2.x renamed `FastMCP`; the code here needs `mcp<2` (pinned in requirements.txt).
- With `pip install mcp` on a system Python that already has Debian-packaged PyJWT, the install fails; a venv avoids it.
