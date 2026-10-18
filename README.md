# FramePilot

**Make the brief billable.** FramePilot is a local-first business kit for freelance video creators and small production teams. It turns a rough client brief into scoped service packages, a transparent pricing guide, a production checklist, a hand-off timeline and a first client message.

Built for the Hacktoberfest 2026 Week 2 **Side Hustle** challenge: small, specific, useful software that someone could plausibly pay for.

## What's in the MVP

- **Client-ready project pack:** summary, positioning, three offer tiers, scope guardrails, clarifying questions and one relevant upsell.
- **Shoot workflow:** checklists for pre-production, shoot day and post-production, plus a timeline with client hand-offs.
- **Transparent price anchors:** calculated from hours, hourly rate, fixed expenses and overhead that the creator supplies. They are not presented as verified market rates.
- **Export:** download the project pack as Markdown; copy the pitch, checklist or pricing assumptions.
- **Local inference:** by default, a Gemma open-weight model runs through Ollama on the creator's own machine. No paid cloud AI key is needed.
- **Sample preview:** a clearly labeled, fixed example that lets people inspect the interface without installing a model. Preview content is not a live AI result.

## Run it locally

Requirements: Python 3.10+ and [Ollama](https://ollama.com/) for live generation. Python dependencies are from the standard library only.

1. Install and start Ollama.
2. Download the default model:

   ```bash
   ollama pull gemma3:4b
   ```

3. From this directory, start the app:

   ```bash
   python app.py
   ```

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).
5. Enter a brief and click **Build my project pack**. For a no-model tour, use **Explore sample preview**.

The first generation may take longer while the model loads. A machine with limited RAM can try a smaller Gemma variant by pulling that model and setting the environment variable, for example:

```bash
# macOS / Linux
FRAMEPILOT_MODEL=gemma3:1b python app.py

# Windows PowerShell
$env:FRAMEPILOT_MODEL="gemma3:1b"; python app.py
```

You can also configure the Ollama endpoint and app port:

```bash
OLLAMA_URL=http://127.0.0.1:11434 FRAMEPILOT_PORT=8000 python app.py
```

The app binds to `127.0.0.1` by default so it is not exposed to your local network. To intentionally host it on a network interface, set `FRAMEPILOT_HOST=0.0.0.0` and configure a firewall accordingly.

## How it works

```text
Browser (form + results)
        |
        | POST /api/generate
        v
Python standard-library server
        |-- calculates price anchors from creator-owned assumptions
        |-- sends the brief to the configured local Ollama endpoint
        v
Gemma open-weight model on the creator's machine
        |
        v
Structured project pack -> browser -> Markdown export
```

The model creates the creative scope and workflow. The Python app calculates the price anchors separately using this disclosed formula:

`((shoot hours + editing hours) × hourly rate + fixed expenses) × (1 + overhead %) `

Starter is anchored at 0.75× the calculated base, Standard at 1.0×, and Premium at 1.45×. These are editable planning suggestions, **not** authoritative local rates or financial advice. The creator should validate costs, revisions, taxes, usage rights and payment terms before quoting.

## Why open-weight AI matters here

Independent creators often work with unpublished campaigns, budgets, locations and client contact details. A local model lets the creator draft plans without sending briefs to a third-party AI API. There is no per-request cloud-AI bill, and a creator can switch models or change the prompts to fit a niche workflow. The trade-off is that model downloads take disk space and generation speed depends on the computer.

FramePilot does not upload briefs, add analytics, or persist project inputs on a remote service. In live mode, brief data is sent to the local Ollama endpoint configured by the user. In sample preview, there is no model call. If you deliberately change `OLLAMA_URL` to a remote server, the privacy boundary changes accordingly.

## Limitations / next steps

This is an early MVP, not a replacement for a signed contract or a creator's judgment. The demo uses a fixed INR pricing formula and no region-specific market database. Model output can be incomplete or wrong, so review before sending a proposal. Inputs and checklist state are not stored after the session.

Ideas for the next iteration: saved client profiles stored locally, a PDF proposal export, payment milestone terms, calendar integration and a real creator usability test.

## Test

Run the unit tests for the pricing and input-validation helpers:

```bash
python -m unittest discover -s tests -v
```

## Built with

- Python standard library (HTTP server, JSON and URL client)
- [Ollama](https://ollama.com/) for local inference
- [Gemma](https://ai.google.dev/gemma) open-weight model by default
- HTML, CSS and vanilla JavaScript

## License

MIT. See [LICENSE](LICENSE).
