import os
import json
import base64
import requests
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "tooba393/LaunchMind-ATP"

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN is not set in environment variables.")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def call_llm(prompt):
    import time, re
    for attempt in range(3):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000
            }
            response = requests.post(url, headers=headers, json=data, timeout=60)
            result = response.json()
            if "error" in result:
                err = result["error"]
                if "rate_limit" in str(err).lower():
                    match = re.search(r'try again in ([\d.]+)s', str(err))
                    wait = float(match.group(1)) + 1 if match else 10
                    print(f"   Rate limited, waiting {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                print(f"LLM error: {err}")
                return None
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            return None
        except Exception as e:
            print(f"LLM failed (attempt {attempt+1}): {e}")
            time.sleep(3)
    return None

def load_spec():
    for filename in ["product_spec.json", "product_specs.json"]:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
    raise FileNotFoundError("No product spec file found!")

def generate_html(spec):
    print("LLM generating HTML landing page from product spec...")

    value_prop = spec.get("value_proposition", "AI Email Reply Assistant")
    features   = spec.get("features", [])
    personas   = spec.get("personas", [])
    stories    = spec.get("user_stories", [])

    features_text = "\n".join([f"- {f['name']}: {f['description']}" for f in features])
    personas_text = "\n".join([f"- {p['name']} ({p['role']}): {p['pain_point']}" for p in personas])
    stories_text  = "\n".join([f"- {s}" for s in stories[:3]])

    # ── CALL 1: HEAD + HERO + FEATURES ────────────────────────
    prompt_part1 = f"""You are an expert web developer. Generate PART 1 of an HTML landing page.
Return ONLY raw HTML. No markdown, no code fences, no explanation.
Start with <!DOCTYPE html> and end after the closing </section> of the features section.
Do NOT write </body> or </html> yet.

Product: Smart ReplyAI — AI Email Reply Assistant
Value Proposition: {value_prop}
Features:
{features_text}

Requirements:
- <!DOCTYPE html>, <html lang="en">, <head> with Inter font from Google Fonts
- CSS variables: --pink:#f472b6 --pink-light:#fbcfe8 --pink-dark:#db2777 --teal:#2dd4bf --teal-light:#99f6e4 --teal-dark:#0d9488 --bg:#07101a --bg2:#0a1520
- All CSS in one <style> tag
- Fixed navbar: gradient logo text "✦ Smart ReplyAI", nav links for Features/Who It's For/Stories/Get Started
- Hero section full viewport height, background-image url('https://images.unsplash.com/photo-1596526131083-e8c633c948d2?w=1600&q=80') brightness 0.35
- Dark overlay gradient on hero
- Hero content: badge pill "✨ Powered by AI · Built for Productivity", H1 "Reply Smarter. Not Harder." in gradient text, subheadline "Your AI Email Co-pilot", paragraph "{value_prop}", two buttons Get Started Free and Watch Demo
- Features section id="features": grid of cards, each with ✦ icon, feature name h3, description p, hover lift effect"""

    part1 = call_llm(prompt_part1)

    # ── CALL 2: PERSONAS + STORIES + CTA + FOOTER ─────────────
    prompt_part2 = f"""You are an expert web developer. Generate PART 2 of an HTML landing page.
Return ONLY raw HTML. No markdown, no code fences, no explanation.
Start directly with <section id="users"> and end with </html>.
This continues a page that already has nav, hero, and features. CSS variables already defined.

Target Users:
{personas_text}

User Stories:
{stories_text}

Requirements:
- Section id="users" "Who It's For": persona cards in a grid
  Each card: avatar circle showing first letter of name, h4 name, role badge pill, italic pain point in quotes
- Section id="stories" "Real Use Cases": ul.stories-list with li.story-item for each story, left pink border
- CTA section id="cta": h2 "Ready to Transform Your Inbox?", paragraph "Join thousands saving 2+ hours weekly.", button "Start For Free Today ✦", three badge pills "✓ No credit card required" "✓ Free forever plan" "✓ Setup in 2 minutes"
- Footer: "Generated by EngineerAgent <agent@launchmind.ai>"
- Close </body> and </html>"""

    part2 = call_llm(prompt_part2)

    # ── Combine ────────────────────────────────────────────────
    if part1 and part2:
        def clean(html):
            if "```html" in html:
                html = html.split("```html")[1].split("```")[0].strip()
            elif "```" in html:
                html = html.split("```")[1].split("```")[0].strip()
            return html.strip()

        part1 = clean(part1)
        part2 = clean(part2)

        # Remove any premature closing tags from part1
        part1 = part1.replace("</body>", "").replace("</html>", "").strip()

        combined = part1 + "\n\n" + part2

        if "<!doctype" in combined.lower() and "</html>" in combined.lower():
            print("LLM generated HTML successfully!")
            return combined
        else:
            print("LLM HTML incomplete — using spec-driven fallback")
    else:
        print("LLM HTML generation failed — using spec-driven fallback")

    return build_fallback_html(spec)


def build_fallback_html(spec):
    """Fallback spec-driven HTML — only used if both LLM calls fail."""
    value_prop = spec.get("value_proposition", "AI Email Reply Assistant")

    features_html = ""
    for f in spec.get("features", []):
        features_html += f"""
        <div class="feature-card">
            <div class="feature-icon">✦</div>
            <h3>{f['name']}</h3>
            <p>{f['description']}</p>
        </div>"""

    personas_html = ""
    for p in spec.get("personas", []):
        personas_html += f"""
        <div class="persona-card">
            <div class="persona-avatar">{p['name'][0]}</div>
            <h4>{p['name']}</h4>
            <span class="persona-role">{p['role']}</span>
            <p>"{p['pain_point']}"</p>
        </div>"""

    stories_html = ""
    for s in spec.get("user_stories", []):
        stories_html += f'<li class="story-item">💌 {s}</li>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart ReplyAI — AI Email Assistant</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
        :root {{--pink:#f472b6;--pink-light:#fbcfe8;--pink-dark:#db2777;--teal:#2dd4bf;--teal-light:#99f6e4;--teal-dark:#0d9488;--bg:#07101a;--bg2:#0a1520;--card:rgba(255,255,255,0.04);--border:rgba(45,212,191,0.18);--text:#e2f0ee;--muted:#5a8080;}}
        *{{margin:0;padding:0;box-sizing:border-box;}}
        body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;}}
        nav{{display:flex;justify-content:space-between;align-items:center;padding:18px 60px;background:rgba(7,16,26,0.92);backdrop-filter:blur(20px);position:fixed;top:0;left:0;right:0;z-index:100;border-bottom:1px solid rgba(45,212,191,0.1);}}
        .nav-logo{{font-size:1.4em;font-weight:900;background:linear-gradient(135deg,var(--teal),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
        .nav-links a{{color:rgba(255,255,255,0.5);text-decoration:none;margin-left:28px;font-size:0.9em;font-weight:500;}}
        .hero{{min-height:100vh;position:relative;display:flex;align-items:center;overflow:hidden;}}
        .hero-bg{{position:absolute;inset:0;z-index:0;background-image:url('https://images.unsplash.com/photo-1596526131083-e8c633c948d2?w=1600&q=80');background-size:cover;background-position:center right;filter:brightness(0.35);}}
        .hero-overlay{{position:absolute;inset:0;z-index:1;background:linear-gradient(105deg,rgba(7,16,26,0.97) 0%,rgba(7,16,26,0.85) 50%,transparent 100%);}}
        .hero-content{{position:relative;z-index:2;padding:140px 80px 100px;max-width:680px;}}
        .hero-badge{{display:inline-flex;align-items:center;background:rgba(45,212,191,0.12);border:1px solid rgba(45,212,191,0.35);color:var(--teal);padding:8px 22px;border-radius:50px;font-size:0.82em;font-weight:600;margin-bottom:32px;}}
        .hero h1{{font-size:clamp(2.8em,5.5vw,4.5em);font-weight:900;line-height:1.06;margin-bottom:12px;background:linear-gradient(135deg,#fff 0%,var(--pink-light) 50%,var(--teal-light) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
        .hero-sub{{font-size:1.25em;font-weight:700;margin-bottom:22px;background:linear-gradient(135deg,var(--pink),var(--teal));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
        .hero p{{font-size:1.05em;color:rgba(255,255,255,0.55);max-width:520px;line-height:1.85;margin-bottom:40px;}}
        .hero-buttons{{display:flex;gap:14px;flex-wrap:wrap;}}
        .btn-primary{{background:linear-gradient(135deg,var(--pink-dark),var(--pink),var(--teal));color:white;border:none;padding:16px 36px;font-size:0.95em;font-weight:700;border-radius:12px;cursor:pointer;box-shadow:0 4px 28px rgba(244,114,182,0.45);}}
        .btn-secondary{{background:rgba(255,255,255,0.06);color:white;border:1.5px solid rgba(255,255,255,0.2);padding:15px 36px;font-size:0.95em;font-weight:600;border-radius:12px;cursor:pointer;}}
        section{{padding:90px 24px;max-width:1200px;margin:0 auto;}}
        .section-label{{text-align:center;background:linear-gradient(135deg,var(--teal),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-size:0.78em;font-weight:700;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;}}
        .section-title{{text-align:center;font-size:clamp(1.8em,4vw,2.6em);font-weight:800;margin-bottom:14px;color:#f0faf8;}}
        .section-subtitle{{text-align:center;color:var(--muted);max-width:500px;margin:0 auto 56px;line-height:1.8;}}
        .features-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px;}}
        .feature-card{{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:28px 24px;transition:all 0.35s;}}
        .feature-card:hover{{transform:translateY(-10px);border-color:rgba(45,212,191,0.35);box-shadow:0 20px 50px rgba(244,114,182,0.1);}}
        .feature-icon{{font-size:1.5em;margin-bottom:16px;display:inline-block;background:linear-gradient(135deg,var(--pink),var(--teal));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
        .feature-card h3{{font-size:1em;font-weight:700;color:#e2f8f5;margin-bottom:8px;}}
        .feature-card p{{color:var(--muted);font-size:0.88em;line-height:1.75;}}
        .personas-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;}}
        .persona-card{{background:var(--card);border:1px solid rgba(244,114,182,0.15);border-radius:18px;padding:28px 22px;text-align:center;transition:all 0.3s;}}
        .persona-card:hover{{transform:translateY(-6px);border-color:rgba(244,114,182,0.4);}}
        .persona-avatar{{width:60px;height:60px;background:linear-gradient(135deg,var(--pink-dark),var(--teal-dark));border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.5em;font-weight:800;color:white;margin:0 auto 16px;}}
        .persona-card h4{{font-size:1em;font-weight:700;color:#f0faf8;margin-bottom:6px;}}
        .persona-role{{background:rgba(45,212,191,0.1);border:1px solid rgba(45,212,191,0.2);color:var(--teal-light);padding:3px 12px;border-radius:50px;font-size:0.76em;font-weight:600;display:inline-block;margin-bottom:14px;}}
        .persona-card p{{color:var(--muted);font-size:0.86em;line-height:1.7;font-style:italic;}}
        .stories-list{{list-style:none;max-width:700px;margin:0 auto;display:flex;flex-direction:column;gap:12px;}}
        .story-item{{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--pink);border-radius:10px;padding:16px 22px;color:#8ab8b3;font-size:0.92em;line-height:1.7;transition:all 0.3s;}}
        .story-item:hover{{background:rgba(45,212,191,0.05);color:#e2f8f5;transform:translateX(8px);}}
        .cta-section{{text-align:center;padding:110px 24px;background:var(--bg2);}}
        .cta-section h2{{font-size:clamp(2em,5vw,3.2em);font-weight:900;margin-bottom:14px;background:linear-gradient(135deg,#fff,var(--pink-light),var(--teal-light));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
        .cta-section p{{color:rgba(255,255,255,0.45);margin-bottom:36px;}}
        .cta-badges{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:24px;}}
        .cta-badge{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);color:var(--muted);padding:5px 14px;border-radius:50px;font-size:0.8em;}}
        footer{{text-align:center;padding:28px;color:#1e3535;font-size:0.8em;border-top:1px solid rgba(45,212,191,0.06);}}
        .footer-logo{{background:linear-gradient(135deg,var(--teal),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-weight:700;}}
    </style>
</head>
<body>
<nav>
    <div class="nav-logo">✦ Smart ReplyAI</div>
    <div class="nav-links">
        <a href="#features">Features</a>
        <a href="#users">Who It's For</a>
        <a href="#stories">Stories</a>
        <a href="#cta">Get Started</a>
    </div>
</nav>
<div class="hero">
    <div class="hero-bg"></div>
    <div class="hero-overlay"></div>
    <div class="hero-content">
        <div class="hero-badge">✨ Powered by AI · Built for Productivity</div>
        <h1>Reply Smarter.<br>Not Harder.</h1>
        <div class="hero-sub">Your AI Email Co-pilot</div>
        <p>{value_prop}</p>
        <div class="hero-buttons">
            <button class="btn-primary">Get Started Free ✦</button>
            <button class="btn-secondary">Watch Demo →</button>
        </div>
    </div>
</div>
<section id="features">
    <p class="section-label">✦ What We Offer</p>
    <h2 class="section-title">Everything You Need</h2>
    <p class="section-subtitle">Powerful features designed to eliminate email overwhelm.</p>
    <div class="features-grid">{features_html}</div>
</section>
<section id="users">
    <p class="section-label">✦ Who It's For</p>
    <h2 class="section-title">Built For Real People</h2>
    <p class="section-subtitle">Smart ReplyAI fits your workflow perfectly.</p>
    <div class="personas-grid">{personas_html}</div>
</section>
<section id="stories">
    <p class="section-label">✦ Real Use Cases</p>
    <h2 class="section-title">How People Use Smart ReplyAI</h2>
    <ul class="stories-list">{stories_html}</ul>
</section>
<div class="cta-section" id="cta">
    <h2>Ready to Transform<br>Your Inbox?</h2>
    <p>Join thousands of professionals saving 2+ hours every week.</p>
    <button class="btn-primary">Start For Free Today ✦</button>
    <div class="cta-badges">
        <span class="cta-badge">✓ No credit card required</span>
        <span class="cta-badge">✓ Free forever plan</span>
        <span class="cta-badge">✓ Setup in 2 minutes</span>
    </div>
</div>
<footer>
    <p>Generated by <span class="footer-logo">EngineerAgent &lt;agent@launchmind.ai&gt;</span> · ReplyAI © 2026</p>
</footer>
</body>
</html>"""


def create_issue(spec):
    url = f"https://api.github.com/repos/{REPO}/issues"
    prompt = f"""Generate a GitHub issue description for creating an HTML landing page.
Product: {spec.get('value_proposition')}
Features: {[f['name'] for f in spec.get('features', [])]}
Keep it under 150 words. Professional tone."""
    body_text = call_llm(prompt) or f"Create HTML landing page for: {spec.get('value_proposition')}"
    data = {"title": "Initial landing page", "body": body_text}
    r = requests.post(url, headers=HEADERS, json=data)
    if r.status_code == 201:
        issue_url = r.json().get("html_url")
        print(f" --- Issue created: {issue_url} ---")
        return issue_url
    else:
        print(f"Issue creation failed: {r.status_code}")
        return None

def get_sha(branch="main"):
    url = f"https://api.github.com/repos/{REPO}/git/refs/heads/{branch}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        raise Exception(f"Could not get SHA: {r.text}")
    return r.json()["object"]["sha"]

def create_branch(branch):
    check = requests.get(f"https://api.github.com/repos/{REPO}/git/refs/heads/{branch}", headers=HEADERS)
    if check.status_code == 200:
        print(f"Branch '{branch}' exists, using it!")
        return
    try:
        sha = get_sha("main")
    except Exception as e:
        print(f"Could not get SHA: {e}")
        return
    r = requests.post(f"https://api.github.com/repos/{REPO}/git/refs", headers=HEADERS,
                      json={"ref": f"refs/heads/{branch}", "sha": sha})
    if r.status_code in [200, 201]:
        print(f"Branch '{branch}' created!")

def commit_file(branch, content, spec):
    url = f"https://api.github.com/repos/{REPO}/contents/index.html"
    encoded = base64.b64encode(content.encode()).decode()
    existing = requests.get(url + f"?ref={branch}", headers=HEADERS)
    file_sha = existing.json().get("sha") if existing.status_code == 200 else None
    data = {
        "message": "feat: Add AI Email Reply Assistant landing page",
        "content": encoded,
        "branch": branch,
        "author": {"name": "EngineerAgent", "email": "agent@launchmind.ai"}
    }
    if file_sha:
        data["sha"] = file_sha
    r = requests.put(url, headers=HEADERS, json=data)
    if r.status_code in [200, 201]:
        print(f" --- File committed! ---")
    else:
        print(f"Commit failed: {r.status_code}")

def create_pr(branch, spec):
    existing_prs = requests.get(
        f"https://api.github.com/repos/{REPO}/pulls?head=tooba393:{branch}&state=open",
        headers=HEADERS)
    if existing_prs.status_code == 200 and existing_prs.json():
        pr_url = existing_prs.json()[0]["html_url"]
        print(f" --- PR already exists: {pr_url} ---")
        return pr_url
    pr_data = {
        "title": "feat: Add AI Email Reply Assistant Landing Page",
        "head": f"{REPO.split('/')[0]}:{branch}",
        "base": "main",
        "body": f"Landing page for {spec.get('value_proposition')}\n\nGenerated by EngineerAgent <agent@launchmind.ai>"
    }
    r = requests.post(f"https://api.github.com/repos/{REPO}/pulls", headers=HEADERS, json=pr_data)
    if r.status_code == 201:
        pr_url = r.json().get("html_url")
        print(f" --- PR created: {pr_url} ---")
        return pr_url
    else:
        print(f"PR creation failed: {r.status_code}")
        return None

def run_engineer(bus=None, revision_feedback=None):
    print("\n Engineer Agent starting...")
    spec = load_spec()

    if revision_feedback:
        print("--- Revising based on CEO feedback...")
        feedback_text = revision_feedback.get("payload", {}).get("feedback", "")
        print(f"   Feedback: {feedback_text[:150]}...")

    html = generate_html(spec)
    issue_url = create_issue(spec)
    branch = f"landing-page-{uuid.uuid4().hex[:6]}"
    create_branch(branch)
    commit_file(branch, html, spec)
    pr_url = create_pr(branch, spec)

    result = {
        "issue": issue_url or "Issue creation failed",
        "pr": pr_url or "PR creation failed",
        "html": html
    }

    print(f"\n --- Engineer Agent DONE\n   Issue: {result['issue']}\n   PR: {result['pr']} ---")

    if bus is not None:
        msg = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "engineer",
            "to_agent": "ceo",
            "message_type": "result",
            "payload": result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        bus.send(msg)

    return result

if __name__ == "__main__":
    run_engineer()