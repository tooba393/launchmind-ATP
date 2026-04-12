from dotenv import load_dotenv
load_dotenv()

import json
from Message_Bus import MessageBus
from agents.CEO_Agent import CEOAgent
from agents.Product_Agent import product_agent
from agents.Engineer_Agent import run_engineer
from agents.Marketing_Agent import marketing_agent
from agents.QA_Agent import qa_agent

def main():
    print("\n" + "="*60)
    print(" ------ AI EMAIL REPLY ASSISTANT - Multi Agent System ------")
    print("="*60 + "\n")

    bus = MessageBus()
    bus.clear()

    # Step 1: CEO
    ceo = CEOAgent(bus)
    startup_idea = (
        "An AI-powered email reply assistant that reads your inbox "
        "and drafts smart, context-aware replies instantly "
        "for busy professionals and students."
    )
    ceo.receive_idea(startup_idea)

    # Step 2: Product Agent
    print("\n PRODUCT AGENT running...\n")
    spec = product_agent(bus)
    print("--- Product spec ready! ---")

    # Step 3: CEO reviews Product
    print("\n CEO reviewing product spec...")
    ceo.process_messages()

    # Step 4: Engineer Agent
    print("\n ENGINEER AGENT running...")
    engineer_result = run_engineer(bus)

    # Step 5: Marketing Agent
    print("\n MARKETING AGENT running...")
    pr_url = engineer_result.get("pr", "https://github.com/tooba393/launchmind-ATP/pull/2")
    marketing_result = marketing_agent(spec, pr_url, bus)

    # Step 6: QA Agent
    print("\n QA AGENT running...")
    html_content   = engineer_result.get("html", "")
    marketing_copy = marketing_result.get("payload", marketing_result)
    qa_result      = qa_agent(html_content, marketing_copy, spec, pr_url, bus)

    # Step 7: CEO Feedback Loop 1
    print("\n CEO processing QA feedback ...")
    ceo.process_messages()

    # Step 7.5: Engineer revision
    engineer_msgs = bus.peek("engineer")
    revision_for_engineer = [m for m in engineer_msgs if m.get("message_type") == "revision_request"]
    if revision_for_engineer:
        print("\n Engineer Agent REVISING based on CEO feedback...")
        feedback = revision_for_engineer[-1]
        bus.receive("engineer")
        engineer_result = run_engineer(bus, revision_feedback=feedback)
        pr_url = engineer_result.get("pr", pr_url)

    # Step 7.6: Marketing revision
    marketing_msgs = bus.peek("marketing")
    revision_for_marketing = [m for m in marketing_msgs if m.get("message_type") == "revision_request"]
    if revision_for_marketing:
        print("\n Marketing Agent REVISING based on CEO feedback...")
        bus.receive("marketing")
        marketing_result = marketing_agent(spec, pr_url, bus, skip_send=True)

    # Step 8: CEO Feedback Loop 2
    print("\n CEO re-reviewing revised outputs ...")
    ceo.process_messages()

    # Step 9: Final Slack summary
    print("\n CEO posting final summary to Slack...")
    ceo.post_final_summary(pr_url)

    # Step 10: FULL MESSAGE LOG — poora JSON schema dikhao
    print("\n" + "="*60)
    print("FULL MESSAGE LOG — STRUCTURED JSON MESSAGES:")
    print("="*60)
    print("\nSchema: message_id | from_agent | to_agent | message_type | payload | timestamp")
    print("-"*60)

    log = bus.get_log()
    if not log:
        print("Log is empty.")
    else:
        for i, msg in enumerate(log, 1):
            if isinstance(msg, dict):
                print(f"\n[Message {i}]")
                print(json.dumps(msg, indent=2))

    print(f"\n[MESSAGE BUS]: Redis Pub/Sub ")
    print("\n" + "="*60)
    print(" --- ALL AGENTS DONE! System complete! ---")
    print("="*60)

if __name__ == "__main__":
    main()
