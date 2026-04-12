import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import requests
load_dotenv()

def call_llm(prompt):
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
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        return None
    except Exception as e:
        print(f"LLM failed: {e}")
        return None

def generate_spec(idea="", focus=""):
    prompt = f"""
You are a senior product manager at a top AI startup.

Your job is to design a complete product specification based ONLY on the idea below.

PRODUCT IDEA:
{idea}

CEO FOCUS (optional guidance):
{focus}

IMPORTANT RULES:
- Do NOT use fixed templates or example names.
- Generate ALL content dynamically based on the idea.
- Personas must be realistic and relevant to the product.
- Features must directly solve user pain points.
- User stories must feel real and specific.
- Do NOT repeat generic or placeholder text.
- Return ONLY valid JSON.

OUTPUT FORMAT:
{{
    "value_proposition": "clear one-line description of product value",
    "personas": [
        {{
            "name": "realistic name",
            "role": "job or identity",
            "pain_point": "specific struggle related to the product"
        }}
    ],
    "features": [
        {{
            "name": "feature name",
            "description": "what it does and why it matters",
            "priority": 1
        }}
    ],
    "user_stories": [
        "As a ..., I want ..., so that ..."
    ]
}}
"""

    result = call_llm(prompt)

    if result:
        try:
            clean = result.strip()

            # safer JSON extraction
            start = clean.find("{")
            end = clean.rfind("}")

            if start != -1 and end != -1:
                clean = clean[start:end+1]

            parsed = json.loads(clean)
            print("LLM generated product spec successfully")
            return parsed

        except Exception as e:
            print(f"JSON parse failed: {e}")

    # fallback (ONLY emergency safety net)
    print("Using fallback product spec")

    return {
        "value_proposition": "AI-powered assistant that helps users manage and respond to emails instantly using smart contextual replies.",
        "personas": [
            {
                "name": "Default User",
                "role": "Email User",
                "pain_point": "Spends too much time writing repetitive email replies"
            }
        ],
        "features": [
            {
                "name": "Smart Reply Generation",
                "description": "Generates context-aware email responses",
                "priority": 1
            }
        ],
        "user_stories": [
            "As a user, I want AI to help me reply to emails faster so that I save time."
        ]
    }

def product_agent(bus=None):
    print("\n--- Product Agent starting ---")

    # Read CEO's task from message bus
    focus = ""
    if bus is not None:
        task_msgs = bus.peek("product")
        ceo_task = next((m for m in task_msgs if m.get("from_agent") == "ceo" 
                        and m.get("message_type") == "task"), None)
        if ceo_task:
            focus = ceo_task["payload"].get("focus", "")
            idea  = ceo_task["payload"].get("idea", "")
            if isinstance(focus, dict):
                focus_text = focus.get("value_proposition") or str(focus)
            else:
                focus_text = str(focus)
            print(f"Task received from CEO: {str(focus)[:100]}...")

    # Generate spec via LLM (with CEO's focus)
    spec = generate_spec(focus)

    with open("product_spec.json", "w") as f:
        json.dump(spec, f, indent=2)
    with open("product_specs.json", "w") as f:
        json.dump(spec, f, indent=2)

    print(f" --- Product Spec generated!")
    print(f"   Value Prop: {spec['value_proposition'][:70]}...")

    # Send confirmation to CEO via MessageBus
    if bus is not None:
        msg = {
            "message_id": str(uuid.uuid4()),
            "from_agent": "product",
            "to_agent": "ceo",
            "message_type": "confirmation",
            "payload": spec,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        bus.send(msg)
        print("Confirmation sent to CEO")

    return spec

if __name__ == "__main__":
    spec = product_agent()
    print(json.dumps(spec, indent=2))
