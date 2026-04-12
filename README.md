# LaunchMind — AI-Powered Startup Multi-Agent System

## Startup Idea
**Smart ReplyAI** is an AI-powered email reply assistant that reads your inbox and drafts smart, context-aware replies instantly. Built for busy professionals, university students, and freelancers who spend too much time writing emails. Agents autonomously define the product, build a landing page, market it, and review quality — without any human doing it manually.

---

## Agent Architecture

```
                    CEO Agent (Orchestrator)
                         |
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    Product Agent  Engineer Agent  Marketing Agent
          |              |              |
          └──────────────┼──────────────┘
                         ▼
                      QA Agent
                         |
                    CEO Agent (Review + Feedback Loops)
```

**Message Bus:** Redis Pub/Sub (Option C — Bonus)

---

## Group Members

| Member | Agent |
|--------|-------|
| Asma Riaz| CEO Agent + Bonus |
| Tooba Arshad |  Product Agent+ Engineer Agent |
| Amna Javaid | Marketing Agent + QA Agent |

---

## Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/tooba393/launchmind-ATP.git
cd launchmind-ATP
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set environment variables
```bash
cp .env.example .env
# Edit .env and fill in your real API keys
```

### 4. Start Redis
```bash
# Windows: Run redis-server.exe from extracted Redis folder
redis-server.exe



### 5. Run the system
```bash
python main.py
```

---

## Platform Integrations

| Platform | Agent | What it does |
|----------|-------|-------------|
| **GitHub** | Engineer Agent | Creates issues, commits `index.html` to branch, opens Pull Request |
| **Slack** | Marketing Agent + CEO | Posts launch message to `#launches` using Block Kit. CEO posts final summary. |
| **SendGrid** | Marketing Agent | Sends outreach email to test inbox |
| **Redis** | Message Bus | All agents communicate via Redis Pub/Sub channels |
| **Groq (LLaMA 3.1)** | All Agents | LLM reasoning for all agent decisions |

---

## Links

- **GitHub PR (Engineer Agent):** [[landing-page-a3a07b](https://github.com/tooba393/launchmind-ATP/tree/landing-page-a3a07b)](https://github.com/tooba393/launchmind-ATP/pull/188)
- **GitHub Repository:** https://github.com/tooba393/launchmind-ATP
- **Slack Workspace:** https://join.slack.com/t/agenticai-dzg8459/shared_invite/zt-3umfteltu-qL6_XXiyHJ2sRcKmic3qfA
- **Demo Video:**      https://drive.google.com/file/d/1qkWKMPtJMzBTu8pnqc_s3gWkyiGPwO30/view?usp=drive_link
---

## Repository Structure

```
launchmind-ATP/
├── README.md
├── main.py                 ← runs entire system end-to-end
├── Message_Bus.py          ← Redis Pub/Sub message bus (Option C bonus)
├── requirements.txt
├── .env.example            ← template with placeholder keys
├── .gitignore              ← .env excluded
└── agents/
    ├── CEO_Agent.py        ← orchestrator, LLM reasoning, 2 feedback loops
    ├── Product_Agent.py    ← generates product spec via LLM
    ├── Engineer_Agent.py   ← builds HTML, commits to GitHub, opens PR
    ├── Marketing_Agent.py  ← generates copy, sends email, posts to Slack
    └── QA_Agent.py         ← reviews HTML + copy, posts PR comments
```

---

## Bonus Features

| Bonus | Marks | Status |
|-------|-------|--------|
| Redis Pub/Sub | +3% | Implemented |
| Graceful failure handling | +3% | Implemented |
| Multiple CEO feedback loops | +2% | Implemented (2 loops) |


---

## Environment Variables (.env.example)

```
GROQ_API_KEY=groq_api
GITHUB_TOKEN=your_github_pat
SLACK_BOT_TOKEN=slack-bot
SENDGRID_API_KEY=sendgrid_key
FROM_EMAIL=sender@email.com
TEST_EMAIL=receiver@email.com
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## Message Schema

Every agent message follows this structure:
```json
{
  "message_id": "uuid",
  "from_agent": "ceo",
  "to_agent": "product",
  "message_type": "task | result | revision_request | confirmation",
  "payload": {},
  "timestamp": "2026-04-12T02:54:47Z"
}
```
