"""AfterMess Strands agent. LLM drafts copy and parses messy text. Python owns safety and match."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from strands import Agent

from aftermess.tools import (
    assign_next_rider,
    export_schedule_ii,
    parse_party_text,
    record_dropped,
    record_mess_no,
    record_mess_release,
    record_need,
    record_paid,
    record_picked,
    record_received,
    record_rider_accept,
    record_rider_cancel,
    remind_rider_pay,
    run_safety_and_match,
    send_whatsapp,
    sitting_status,
)

load_dotenv()

SYSTEM_PROMPT = """
You are AfterMess, the IIITD lunch and dinner leftover closeout clerk.

You coordinate two mess vendors, two named drops, and a named rider roster
on WhatsApp. You do real work. You are not a chatbot and not a food marketplace.

Hard rules:
- Food is leftover unused plates that were never served. Never ask a mess to cook extra.
- Food is free. Rider UPI is transport only. Never call a batch an "order" for paid food.
- Never override the safety gate. If a tool returns refused_unsafe, the batch is dead.
- Matching and roster walks are Python. Call run_safety_and_match and assign_next_rider.
  Do not invent plate math.
- Never recruit a rider who is not on the roster.
- Never remind the drop to pay the rider before RECEIVED.
- If parse_party_text is ambiguous, ask one closed follow-up. Do not guess plates.
- Do not claim 80G, CSR, or legal immunity.
""".strip()

TOOLS = [
    record_need,
    record_mess_release,
    record_mess_no,
    run_safety_and_match,
    assign_next_rider,
    record_rider_accept,
    record_rider_cancel,
    record_picked,
    record_dropped,
    record_received,
    remind_rider_pay,
    record_paid,
    export_schedule_ii,
    sitting_status,
    send_whatsapp,
    parse_party_text,
]


def _model():
    provider = os.getenv("MODEL_PROVIDER", "bedrock").lower()
    if provider == "openai":
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={"api_key": os.environ["OPENAI_API_KEY"]},
            model_id=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        )
    from strands.models import BedrockModel

    return BedrockModel(
        model_id=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.2,
    )


def build_agent() -> Agent:
    return Agent(
        model=_model(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
    )


def tick_prompt(sitting: str, sitting_date: str, phase: str | None) -> str:
    phase_line = f"Phase hint: {phase}." if phase else "Clocks may be unset; inspect sitting_status first."
    return f"""
AfterMess tick for {sitting} on {sitting_date}. {phase_line}

1. Call sitting_status for this sitting.
2. If every trip is already state=settled (or there are no open trips and match_result is set),
   do not call more tools. Reply in one sentence: lunch/dinner is already closed.
3. If needs exist and messes have not been shown them, do not invent a needs_cutoff
   WhatsApp yourself — the operator should run `python -m aftermess tick --phase needs_cutoff`.
4. If leftover has been released and not matched, call run_safety_and_match.
5. Never pay anyone. Call remind_rider_pay only if a trip is in awaiting_pay.
   Do not call it for settled, awaiting_received, or already_matched trips.
6. Summarize trip states in one short paragraph. Do not claim tax benefits.
""".strip()
