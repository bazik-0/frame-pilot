# FramePilot: I built a local AI business kit for freelance video creators

**Tags:** `#hacktoberfest` `#hf26challenge` `#ai` `#showdev`

> Submission draft for the Hacktoberfest 2026 Week 2 “Side Hustle” challenge. Before publishing, replace this note with the actual live demo or video URL and GitHub repository URL, and include honest first-user feedback if available.

## The problem: creative work is only half the job

Freelance video creators don't just shoot and edit. Every small client project also means interpreting a vague brief, deciding what's included, pricing the work, planning the shoot, setting revision limits and writing the message that wins the job. Those little business tasks eat into the hours that should be spent creating.

I built **FramePilot** for independent video creators and small production teams. The idea is simple: paste in the client's rough brief, add your own time and cost assumptions, and get a project pack you can actually work from.

## What it does

- Turns a loose brief into a project snapshot and an offer position.
- Proposes three distinct packages with scoped deliverables and revision boundaries.
- Creates pre-production, shoot-day and post-production checklists.
- Builds a timeline with clear client hand-offs.
- Drafts a first message to the client and suggests a relevant optional add-on.
- Calculates pricing anchors from the creator's own shoot hours, editing hours, hourly rate, fixed expenses and overhead, then exports the pack as Markdown.

The pricing is deliberately transparent. It is not a magic “AI knows the market” number: the app shows the formula and labels the values as estimates that need review.

## Why local open-weight AI?

A freelance brief can contain an unreleased campaign, a client's budget or details about a shoot location. FramePilot uses Gemma through Ollama, running on the creator's own machine. That means the app doesn't need a paid AI API key, the project brief doesn't need to leave the device, and the creator can swap models or adapt the prompt for their niche.

That openness also has a trade-off: the model download takes space and generation speed depends on the hardware. The app includes a clearly labeled sample preview so people can explore the workflow even before setting up a local model. The sample is fixed content, not presented as AI-generated output.

## How I built it

The interface is plain HTML/CSS/JavaScript and the backend uses Python's standard library. The backend sends a structured prompt to the locally configured Ollama API, normalizes the response, and separately calculates price anchors from the creator's own assumptions. No third-party cloud AI service is called by default.

**Stack:** Python, Ollama, Gemma, HTML, CSS and JavaScript.

## A quick example

Imagine a local cafe launching a seasonal menu. Instead of immediately agreeing to “a few reels,” the creator can turn that request into a hero video, cut-downs, a shoot checklist, a client approval timeline and three scope options. The client gets clarity; the creator gets a better-defined job.

## What I learned / what comes next

The part I care about most is making AI produce useful work product rather than another chat window. The first version focuses on the hand-offs around a real freelance job. Next, I'd like to test it with creators, save reusable client profiles locally, and add a polished PDF proposal export.

**Try it:** [add demo or video link]

**Source code:** [add repository link]

**One thing I'd love feedback on:** Which part of the freelance workflow burns the most unpaid time for you—pricing, client communication, scope creep or planning the shoot?

---