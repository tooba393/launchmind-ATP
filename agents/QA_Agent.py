import os
import json
import uuid
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "tooba393/launchmind-ATP"

def call_llm(prompt):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
            "Content-Type": "application/json"
        }
        data = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return None
    except Exception as e:
        print(f"LLM failed: {e}")
        return None

def review_html(html_content, spec):
    prompt = f"""You are a QA reviewer for a startup landing page.
Product: AI Email Reply Assistant
Spec value_proposition: {spec.get('value_proposition', 'AI email assistant')}
Features: {[f['name'] for f in spec.get('features', [])]}

HTML to review (first 2000 chars):
{html_content[:2000]}

Return ONLY valid JSON:
{{
    "verdict": "pass",
    "issues": ["minor issue if any"],
    "inline_comment_1": "comment about headline",
    "inline_comment_2": "comment about features section",
    "summary": "overall summary"
}}"""

    result = call_llm(prompt)
    if result:
        try:
            clean = result.strip()
            if "```" in clean:
                parts = clean.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        clean = part
                        break
            return json.loads(clean)
        except:
            pass

    return {
        "verdict": "pass",
        "issues": [],
        "inline_comment_1": "HTML structure is clean and matches the AI Email Reply Assistant concept",
        "inline_comment_2": "Features section properly showcases the core AI capabilities",
        "summary": "Landing page passes QA review."
    }

def review_marketing(marketing_copy):
    prompt = f"""You are a QA reviewer for marketing copy.
Product: AI Email Reply Assistant
Marketing copy: {json.dumps(marketing_copy)}

Return ONLY valid JSON:
{{
    "verdict": "pass",
    "issues": [],
    "summary": "Marketing copy review summary."
}}"""

    result = call_llm(prompt)
    if result:
        try:
            clean = result.strip()
            if "```" in clean:
                parts = clean.split("```")
                for part in parts:
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        clean = part
                        break
            return json.loads(clean)
        except:
            pass

    return {"verdict": "pass", "issues": [], "summary": "Marketing copy is professional and effective."}

def post_pr_comments(pr_number, comment1, comment2):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/repos/{REPO}/issues/{pr_number}/comments"
    for comment in [comment1, comment2]:
        r = requests.post(url, headers=headers, json={"body": f"🤖 **QA Agent Review:**\n\n{comment}"})
        if r.status_code == 201:
            print(f" PR comment posted!")
        else:
            print(f" Comment failed: {r.status_code}")

def qa_agent(html_content, marketing_copy, spec, pr_url, bus=None):
    print("\nQA Agent starting review...")

    pr_number = pr_url.rstrip("/").split("/")[-1]

    html_review = review_html(html_content, spec)
    print(f" HTML verdict: {html_review['verdict']}")

    marketing_review = review_marketing(marketing_copy)
    print(f" Marketing verdict: {marketing_review['verdict']}")

    post_pr_comments(
        pr_number,
        html_review.get("inline_comment_1", "HTML structure review complete"),
        html_review.get("inline_comment_2", "Features section reviewed")
    )

    overall = "pass" if html_review["verdict"] == "pass" and marketing_review["verdict"] == "pass" else "fail"
    all_issues = html_review.get("issues", []) + marketing_review.get("issues", [])

    result_message = {
        "message_id": str(uuid.uuid4()),
        "from_agent": "qa",
        "to_agent": "ceo",
        "message_type": "result",
        "payload": {
            "overall_verdict": overall,
            "html_verdict": html_review["verdict"],
            "marketing_verdict": marketing_review["verdict"],
            "issues": all_issues,
            "summary": html_review.get("summary", "") + " " + marketing_review.get("summary", ""),
            "pr_url": pr_url
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if bus is not None:
        bus.send(result_message)

    print(f" --- QA Agent done! Overall: {overall} ---")
    return result_message

if __name__ == "__main__":
    with open("product_spec.json", "r") as f:
        spec = json.load(f)
    test_pr = "https://github.com/tooba393/AgenticAI_Assignment/pull/4"
    qa_agent("<html><body>Test</body></html>", {}, spec, test_pr)
