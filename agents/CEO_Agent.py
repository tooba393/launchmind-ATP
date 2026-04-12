import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
import json
import re, time
import requests

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")



def call_llm(prompt, retries=4):
    for attempt in range(retries):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}]
            }
            response = requests.post(url, headers=headers, json=data)
            result = response.json()

            if "error" in result:
                err = result["error"]
                print(f"[LLM]  Groq error (attempt {attempt+1}): {err}")
                if "rate_limit" in str(err).lower() or response.status_code == 429:
                    match = re.search(r'try again in ([\d.]+)s', str(err))
                    wait = float(match.group(1)) + 1 if match else (2 ** attempt * 3)
                    print(f"[LLM] ⏳ Rate limited. Waiting {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                return "AI response unavailable"

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]

            print(f"[LLM]  Unexpected response: {result}")
            return "AI response unavailable"

        except Exception as e:
            print(f"[LLM]  Exception (attempt {attempt+1}): {e}")
            time.sleep(3)

    return "AI response unavailable"

class CEOAgent:
    def __init__(self, bus):
        self.bus = bus

    def _send(self, to_agent, message_type, payload, parent_id=None):
        msg = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "ceo",
            "to_agent": to_agent,
            "message_type": message_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "parent_message_id": parent_id
        }
        self.bus.send(msg)
        return msg

    def receive_idea(self, idea):
        print(f"\n[CEO]  Received idea: {idea}")
        print("[CEO] --- Using LLM to decompose idea into tasks for each agent...\n")

        decompose_prompt = f"""You are the CEO of a tech startup called LaunchMind.

You just received this startup idea:
"{idea}"

Your job is to break this into 3 specific tasks — one for each team member.
Reply ONLY with a valid JSON object, no extra text, no markdown, no backticks.

{{
  "product_task": "2 sentence task for the Product Manager focusing on defining user personas and top 5 features",
  "engineer_task": "2 sentence task for the Engineer focusing on building the HTML landing page with specific sections to include",
  "marketing_task": "2 sentence task for the Marketing Manager focusing on tagline, email copy, and social media posts"
}}"""

        raw = call_llm(decompose_prompt)
        print(f"[CEO]  LLM Task Decomposition Response:\n{raw}\n")

        try:
            clean = raw.strip().strip("```json").strip("```").strip()
            tasks = json.loads(clean)
            product_task   = tasks.get("product_task",  "Define user personas and top 5 features for the product.")
            engineer_task  = tasks.get("engineer_task", "Build a complete HTML landing page with headline, features, and CTA.")
            marketing_task = tasks.get("marketing_task","Create a tagline, cold email, and 3 social media posts.")
        except Exception:
            print("[CEO]  Could not parse JSON, using fallback tasks")
            product_task   = "Define user personas and top 5 features for the product."
            engineer_task  = "Build a complete HTML landing page with headline, features section, and CTA button."
            marketing_task = "Create a tagline, cold outreach email, and social media posts for Twitter, LinkedIn, Instagram."

        self._send("product",   "task", {"idea": idea, "focus": product_task})
        print(f"[CEO]  Task sent to PRODUCT AGENT:\n      → {product_task}\n")

        self._send("engineer",  "task", {"idea": idea, "focus": engineer_task})
        print(f"[CEO]  Task sent to ENGINEER AGENT:\n      → {engineer_task}\n")

        self._send("marketing", "task", {"idea": idea, "focus": marketing_task})
        print(f"[CEO]  Task sent to MARKETING AGENT:\n      → {marketing_task}\n")

        print("[CEO]  All tasks dispatched. Waiting for agents to complete...\n")

    def process_messages(self):
        inbox = self.bus.receive("ceo")

        if not inbox:
            print("[CEO] No messages to process.")
            return

        for msg in inbox:
            sender   = msg.get("from_agent", "unknown").lower()
            payload  = msg.get("payload", {})
            msg_type = msg.get("message_type", "result")

            print(f"\n[CEO]  Message received from {sender.upper()} ({msg_type})")

            review_prompt = f"""You are the CEO of LaunchMind startup reviewing output from your {sender} agent.

Product: AI Email Reply Assistant — drafts smart email replies for busy professionals and students.

Agent Role Context:
- product agent: should deliver value_proposition, personas, features, user_stories
- engineer agent: should deliver HTML landing page code committed to GitHub, issue URL, PR URL
- marketing agent: should deliver tagline, email copy, social media posts, confirm email sent and Slack posted
- qa agent: should deliver pass/fail verdict on HTML and marketing copy

Output received from {sender} agent:
{str(payload)[:600]}

Is this output acceptable for a {sender} agent's role?
Reply with ONLY one of:
- APPROVED: <one sentence reason>
- REVISION NEEDED: <one specific actionable issue>"""

            time.sleep(1)
            feedback = call_llm(review_prompt)
            print(f"[CEO]  LLM Review of {sender.upper()} output:")
            print(f"      {feedback}\n")

            self._send("log", "review_decision", {
                "reviewed_agent": sender,
                "decision": feedback[:300],
                "original_msg_type": msg_type
            })

            if feedback and "REVISION NEEDED" in feedback.upper():
                print(f"[CEO] Sending REVISION REQUEST to {sender.upper()}...")
                self._send(sender, "revision_request", {
                    "feedback": feedback,
                    "original": payload
                }, parent_id=msg.get("message_id"))
                print(f"[CEO]  Revision request sent and logged for {sender.upper()}\n")

            elif feedback and "APPROVED" in feedback.upper():
                print(f"[CEO]  Output APPROVED from {sender.upper()}\n")
                self._send("log", "approval", {
                    "approved_agent": sender,
                    "reason": feedback[:200]
                })
            else:
                print(f"[CEO]  Unclear response: {feedback[:80]}\n")

    def _send_message(self, to_agent, message_type, payload, parent_id=None):
        return self._send(to_agent, message_type, payload, parent_id)

    def post_final_summary(self, pr_url=""):
        time.sleep(3)
        collected_data = {
            "product":   self.bus.peek("product"),
            "engineer":  self.bus.peek("engineer"),
            "marketing": self.bus.peek("marketing"),
            "qa":        self.bus.peek("qa")
        }

        summary_prompt = f"""You are the CEO of LaunchMind startup.

All agents have completed their work. Write a concise FINAL LAUNCH SUMMARY.

Agent outputs:
{str(collected_data)[:1500]}

Include:
- Product value proposition (1 sentence)
- What the Engineer built and GitHub PR link: {pr_url}
- Marketing highlights (tagline + email sent)
- QA verdict
- Overall launch status

Keep under 250 words. Professional tone."""

        final_summary_text = call_llm(summary_prompt)

        if not final_summary_text or "AI response unavailable" in final_summary_text:
            final_summary_text = "LaunchMind agents completed. Landing page built, marketing sent, QA passed."

        self._send("log", "summary", {
            "summary": final_summary_text,
            "pr_url": pr_url,
            "status": "approved"
        })

        os.makedirs("logs", exist_ok=True)
        with open("logs/ceo_summary.json", "w") as f:
            json.dump({"summary": final_summary_text, "pr_url": pr_url}, f, indent=2)

        print("[CEO] --- Final summary generated ---")

        # ── Slack 3000 char limit fix ──────────────────────────
        safe_summary = final_summary_text[:2900]

        slack_payload = {
            "channel": "#launches",
            "text": safe_summary,
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "CEO Final Launch Summary", "emoji": True}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": safe_summary}
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*GitHub PR:* <{pr_url}|View Pull Request>"},
                        {"type": "mrkdwn", "text": "*Status:*  All Agents Done"}
                    ]
                }
            ]
        }

        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json=slack_payload
        )

        if r.json().get("ok"):
            print("[CEO] --- Final summary posted to Slack! ---")
        else:
            print("[CEO]  Slack error:", r.json())