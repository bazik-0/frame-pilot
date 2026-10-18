"""FramePilot: local-first project-pack generator for freelance video creators.

Uses only Python's standard library. Real AI inference is performed by a local
Ollama server (default model: gemma3:4b); no external AI API is called.
"""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
HOST = os.getenv("FRAMEPILOT_HOST", "127.0.0.1")
PORT = int(os.getenv("FRAMEPILOT_PORT", "8000"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("FRAMEPILOT_MODEL", "gemma3:4b")
MAX_BODY_BYTES = 80_000


def round_to_hundred(value: float) -> int:
    """Round a positive estimate to the nearest ₹100."""
    return max(0, int((float(value) + 50) // 100) * 100)


def pricing_anchors(payload: dict) -> dict:
    """Create transparent, editable price anchors from user-supplied assumptions.

    These are estimates, not market-rate claims. The user should review them
    before sending a quote to a client.
    """
    shoot_hours = clamp_number(payload.get("shoot_hours", 3), 0, 72, 3)
    edit_hours = clamp_number(payload.get("edit_hours", 5), 0, 200, 5)
    hourly_rate = clamp_number(payload.get("hourly_rate", 700), 0, 1_000_000, 700)
    expenses = clamp_number(payload.get("expenses", 500), 0, 10_000_000, 500)
    overhead_pct = clamp_number(payload.get("overhead_pct", 10), 0, 100, 10)
    labour = (shoot_hours + edit_hours) * hourly_rate
    base = round_to_hundred((labour + expenses) * (1 + overhead_pct / 100))
    return {
        "currency": "INR",
        "assumptions": {
            "shoot_hours": shoot_hours,
            "edit_hours": edit_hours,
            "hourly_rate_inr": hourly_rate,
            "fixed_expenses_inr": expenses,
            "overhead_percent": overhead_pct,
            "formula": "((shoot hours + edit hours) × hourly rate + fixed expenses) × (1 + overhead %)"
        },
        "anchors": {
            "Starter": round_to_hundred(base * 0.75),
            "Standard": round_to_hundred(base),
            "Premium": round_to_hundred(base * 1.45),
        },
        "base_estimate_inr": base,
        "disclaimer": "Planning anchors based on your inputs, not verified market rates. Review all costs before quoting."
    }


def clamp_number(value, low, high, default):
    try:
        number = float(value)
        if number != number:  # NaN
            return default
        return min(high, max(low, number))
    except (TypeError, ValueError):
        return default


def clean_text(value, max_len=4000):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()[:max_len]


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    brief = clean_text(payload.get("brief"), 4000)
    client = clean_text(payload.get("client"), 160)
    if len(brief) < 12:
        raise ValueError("Add a little more detail to the project brief (at least 12 characters).")
    if not client:
        client = "Client not specified"
    safe = {
        "client": client,
        "project_type": clean_text(payload.get("project_type"), 100) or "Social media video",
        "brief": brief,
        "platforms": clean_text(payload.get("platforms"), 160) or "Instagram and YouTube Shorts",
        "timeline": clean_text(payload.get("timeline"), 120) or "Within 7 days",
        "style": clean_text(payload.get("style"), 100) or "Professional and warm",
        "shoot_hours": clamp_number(payload.get("shoot_hours", 3), 0, 72, 3),
        "edit_hours": clamp_number(payload.get("edit_hours", 5), 0, 200, 5),
        "hourly_rate": clamp_number(payload.get("hourly_rate", 700), 0, 1_000_000, 700),
        "expenses": clamp_number(payload.get("expenses", 500), 0, 10_000_000, 500),
        "overhead_pct": clamp_number(payload.get("overhead_pct", 10), 0, 100, 10),
    }
    return safe


SYSTEM_PROMPT = """You are FramePilot, a practical business assistant for independent video creators and small production teams.
Generate a useful, concise client-ready project pack from the supplied brief. Do not invent facts about the client, location, market prices, or equipment. Flag missing details as questions/assumptions. Avoid guaranteeing results such as virality. Keep deliverables scoped and practical. Return ONLY valid JSON (no markdown fences) with exactly this schema:
{
  "project_snapshot": "2-4 sentence summary of the work and intended outcome",
  "positioning": "A concise value proposition for the creator to use in a proposal",
  "packages": [
    {"name":"Starter","best_for":"...","deliverables":["..."],"revision_policy":"..."},
    {"name":"Standard","best_for":"...","deliverables":["..."],"revision_policy":"..."},
    {"name":"Premium","best_for":"...","deliverables":["..."],"revision_policy":"..."}
  ],
  "preproduction_checklist": ["..."],
  "shoot_checklist": ["..."],
  "postproduction_checklist": ["..."],
  "timeline": [{"stage":"...","timing":"...","client_action":"..."}],
  "client_pitch": "A friendly, ready-to-send message, without fake claims or placeholders unless needed",
  "scope_guardrails": ["..."],
  "clarifying_questions": ["..."],
  "upsell_idea": "One relevant optional add-on and why it helps"
}
Packages must be meaningfully different and realistic. Do not include any prices: the app calculates transparent price anchors separately from user-provided hours and costs. Make output specific to the brief. Keep list lengths concise (typically 3-6 items)."""


def build_user_prompt(payload, pricing):
    return f"""Create a project pack for this freelance job.
Client: {payload['client']}
Project type: {payload['project_type']}
Brief: {payload['brief']}
Target platforms: {payload['platforms']}
Desired deadline: {payload['timeline']}
Communication style: {payload['style']}
Creator's planning assumptions (prices are calculated separately):
- Shoot hours: {payload['shoot_hours']}
- Editing hours: {payload['edit_hours']}
- Hourly rate: INR {payload['hourly_rate']}
- Fixed expenses: INR {payload['expenses']}
- Overhead: {payload['overhead_pct']}%
Budget base estimate generated by transparent app formula: INR {pricing['base_estimate_inr']}
Flag the most important unknowns instead of silently making assumptions. Do not repeat the entire input."""


def call_ollama(payload, pricing):
    """Request structured output from an Ollama model running on this machine."""
    url = OLLAMA_URL.rstrip("/") + "/api/chat"
    body = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(payload, pricing)},
        ],
        "options": {
            "temperature": 0.2,
            "repeat_penalty": 1.15,
            "num_predict": 1200
        },
    }
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=240) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 404:
            raise RuntimeError(
                f"Ollama could not find model '{MODEL}'. In a terminal, run: ollama pull {MODEL}"
            ) from exc
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(
            "Can't reach Ollama at " + OLLAMA_URL + ". Install/start Ollama and pull model '" + MODEL + "'."
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError("The local model timed out. Try a smaller model or a shorter brief.") from exc

    message = raw.get("message", {}).get("content", "")
    try:
        parsed = json.loads(message)
    except json.JSONDecodeError as exc:
        raise RuntimeError("The model returned invalid structured output. Try again with a shorter brief.") from exc
    return normalize_result(parsed)


def normalize_result(result):
    """Limit the result shape and field sizes before returning it to the browser."""
    if not isinstance(result, dict):
        raise RuntimeError("The model response did not match the expected format.")

    def one_line(v, limit=1200):
        return clean_text(v, limit)

    def list_text(key, limit=10, item_len=320):
        val = result.get(key, [])
        if not isinstance(val, list):
            return []
        return [one_line(x, item_len) for x in val[:limit] if one_line(x, item_len)]

    packages_in = result.get("packages", [])
    packages = []
    if isinstance(packages_in, list):
        tier_names = ["Starter", "Standard", "Premium"]
        for index, pkg in enumerate(packages_in[:3]):
            if not isinstance(pkg, dict):
                continue
            supplied_name = one_line(pkg.get("name"), 60).lower()
            fixed_name = next((name for name in tier_names if name.lower() == supplied_name), tier_names[index])
            packages.append({
                "name": fixed_name,
                "best_for": one_line(pkg.get("best_for"), 320),
                "deliverables": [one_line(x, 240) for x in pkg.get("deliverables", [])[:8] if one_line(x, 240)] if isinstance(pkg.get("deliverables", []), list) else [],
                "revision_policy": one_line(pkg.get("revision_policy"), 320),
            })
    timeline_in = result.get("timeline", [])
    timeline = []
    if isinstance(timeline_in, list):
        for item in timeline_in[:8]:
            if isinstance(item, dict):
                timeline.append({
                    "stage": one_line(item.get("stage"), 100),
                    "timing": one_line(item.get("timing"), 140),
                    "client_action": one_line(item.get("client_action"), 240),
                })
    return {
        "project_snapshot": one_line(result.get("project_snapshot")),
        "positioning": one_line(result.get("positioning")),
        "packages": packages,
        "preproduction_checklist": list_text("preproduction_checklist", 8),
        "shoot_checklist": list_text("shoot_checklist", 8),
        "postproduction_checklist": list_text("postproduction_checklist", 8),
        "timeline": timeline,
        "client_pitch": str(result.get("client_pitch", "") or "").strip()[:1800],
        "scope_guardrails": list_text("scope_guardrails", 8),
        "clarifying_questions": list_text("clarifying_questions", 8),
        "upsell_idea": one_line(result.get("upsell_idea"), 500),
    }


def health_status():
    request = Request(OLLAMA_URL.rstrip("/") + "/api/tags", method="GET")
    try:
        with urlopen(request, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        model_loaded = any(name == MODEL or name.startswith(MODEL + ":") for name in models)
        return {
            "ollama_reachable": True,
            "model": MODEL,
            "model_available": model_loaded,
            "models": models[:30],
        }
    except Exception:
        return {"ollama_reachable": False, "model": MODEL, "model_available": False, "models": []}


class Handler(BaseHTTPRequestHandler):
    server_version = "FramePilot/1.0"

    def _send(self, status, body, content_type="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._send(200, json.dumps(health_status()))
        if path in ("/", "/index.html"):
            file_path = WEB_DIR / "index.html"
            return self._send(200, file_path.read_bytes(), "text/html; charset=utf-8")
        if path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        return self._send(404, json.dumps({"error": "Not found"}))

    def do_POST(self):
        if self.path != "/api/generate":
            return self._send(404, json.dumps({"error": "Not found"}))
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_BYTES:
                return self._send(413, json.dumps({"error": "Request body missing or too large."}))
            raw = self.rfile.read(length)
            payload = validate_payload(json.loads(raw.decode("utf-8")))
            pricing = pricing_anchors(payload)
            result = call_ollama(payload, pricing)
            return self._send(200, json.dumps({
                "result": result,
                "pricing": pricing,
                "model": MODEL,
                "mode": "local-ai",
            }, ensure_ascii=False))
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"error": "Request body must be valid JSON."}))
        except ValueError as exc:
            return self._send(400, json.dumps({"error": str(exc)}))
        except RuntimeError as exc:
            return self._send(503, json.dumps({"error": str(exc)}))
        except Exception as exc:
            # Keep implementation details out of the browser response.
            print(f"[FramePilot] Unexpected error: {type(exc).__name__}: {exc}")
            return self._send(500, json.dumps({"error": "Something went wrong. Check the terminal for details."}))

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {fmt % args}")


def main():
    print("\nFramePilot is starting")
    print(f"Open http://{HOST}:{PORT} in your browser")
    print(f"AI model: {MODEL} | Ollama: {OLLAMA_URL}")
    print("Privacy: briefs are sent only to the Ollama endpoint you configured; no cloud AI API is called.\n")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down FramePilot…")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
