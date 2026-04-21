# WorkFlex Bridge Agent

A LangGraph-powered agent that reads Microsoft Teams `#feature-requests`
messages, enriches them with HubSpot ARR data, checks the Jira backlog for
duplicates, and drafts either a new Jira ticket or a follow-up comment —
all gated by a human-in-the-loop Gradio review step.

---

## Architecture

```
┌────────────────────────┐         ┌─────────────────────────┐
│  Gradio UI (main.py)   │◄──────► │  Compiled LangGraph      │
│  - Process Messages    │         │  (agent.py)              │
│  - Review drafts       │         │                          │
│  - Confirm & Submit    │         │  fetch_messages          │
└────────────────────────┘         │      │                   │
          ▲                         │  fetch_backlog          │
          │                         │      │                   │
          │                         │  extract   (Claude)     │
          │                         │      │                   │
          │                         │  enrich_arr (HubSpot)   │
          │                         │      │                   │
          │                         │  match_duplicate (Claude)│
          │                         │      │                   │
          │                         │  draft     (Claude)     │
          │                         └─────────────────────────┘
          │                                     │
          └──────── human approval ─────────────┘
                        │
                        ▼
           submit_all() → Jira + Teams
```

All HTTP is done with `httpx` through three small wrapper clients in
`backend/clients.py`. Claude (`claude-haiku-4-5-20251001`) is used for every
LLM step.

---

## Prerequisites

1. **Mock server running at `http://localhost:8080`.**
   From the repo root:
   ```bash
   cd challenge && docker compose up --build -d
   ```
   The token dashboard lives at <http://localhost:8080/dashboard>. You can
   generate tokens there and paste them into `.env`, **or** just leave those
   fields blank — the agent will auto-provision tokens on first run.

2. **Anthropic API key.** Already wired into `.env` for this case study.

3. **Python 3.11+** with the deps installed:
   ```bash
   pip install -r backend/requirements.txt
   ```

---

## Run

```bash
cd backend
python main.py
```

Then open <http://localhost:7860>.

### Using the UI

1. Pick how many of the newest Teams messages to process (default 20).
2. Click **▶️ Process Messages**. The agent fetches Teams + Jira, runs the
   LangGraph pipeline, and renders one card per message with:
   - The AI decision (🆕 CREATE / 🔁 UPDATE / ⏭️ SKIP)
   - Extracted *requester*, *client*, and *request*
   - HubSpot ARR
   - The drafted ticket title + body (CREATE) or comment body (UPDATE)
   - The target existing ticket key (UPDATE)
3. Review the drafts. Nothing has been written yet.
4. Click **✅ Confirm & Submit** to push every actionable draft to Jira
   (create issue / add comment) and post the feedback message back to the
   Teams channel.

The feedback messages follow the required format:
- `"Got it! Added to Ticket #JIRA-1063"`
- `"Created new Ticket #JIRA-1200 for Weyland-Yutani ($720k ARR)"`

---

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `ANTHROPIC_MODEL` | Defaults to `claude-haiku-4-5-20251001` |
| `MOCK_API_BASE_URL` | Mock server base URL (default `http://localhost:8080`) |
| `JIRA_EMAIL`, `JIRA_TOKEN` | Jira Basic auth credentials. Blank → auto-provision |
| `HUBSPOT_TOKEN` | HubSpot bearer token. Blank → auto-provision |
| `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET` | OAuth2 client-credentials for MS Graph. Blank → auto-provision |
| `GRADIO_HOST`, `GRADIO_PORT` | Defaults to `0.0.0.0:7860` |

---

## Files

```
backend/
├── main.py          # Gradio UI + orchestration
├── agent.py         # LangGraph StateGraph + Claude prompts + submit_all()
├── clients.py       # JiraClient, HubSpotClient, TeamsClient + auto-provisioning
└── requirements.txt
.env                 # All API keys and tokens
challenge/           # Provided case-study assets + mock server
```

---

## Future Improvements

### Performance

- **Batch LLM extraction**: extract multiple Teams messages in one Claude call
  (JSON array) instead of one-call-per-message to reduce latency and token cost.
- **Parallel stage execution**: run independent per-item enrichment/matching
  work in parallel where safe.

### Observability

- **Structured logging** with per-item stage details:
  - `stage`
  - `duration_ms`
  - `outcome`
  - `error_code` (if failed)
- **Basic metrics** dashboard/counters:
  - extraction success rate
  - skip rate
  - average latency per stage

### Configurability

- Move operational knobs to `.env`, for example:
  - `MAX_MESSAGES`
  - duplicate confidence thresholds
  - retry counts / retry backoff parameters
