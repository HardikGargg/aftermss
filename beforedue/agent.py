"""BeforeDue — Everyday Agent built with the Strands Agents SDK."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from strands import Agent

from beforedue.tools import (
    file_safe_reminder,
    ingest_item,
    list_new_inbox_items,
    list_open_deadlines,
    list_pending_decisions,
    mark_item_processed,
    request_payment_approval,
    start_return,
)

load_dotenv()

SYSTEM_PROMPT = """
You are BeforeDue, a household agent that quietly handles bills, return windows,
and warranties. You do real work. You are not a chatbot.

Rules:
- Scan the inbox, ingest every new item onto the ledger, then process open deadlines.
- Safe actions you MUST take yourself: file reminders, start returns before the window closes.
- NEVER pay a bill. For any bill with an amount, call request_payment_approval and stop.
- One human question only: whether to pay. Do not ask permission to file a reminder or start a return.
- After ingesting an inbox file, call mark_item_processed.
- Be specific: name the item, the date, the amount, and the action you took.
- If nothing is new and nothing is due, say so in one sentence.
""".strip()

TOOLS = [
    list_new_inbox_items,
    ingest_item,
    list_open_deadlines,
    file_safe_reminder,
    start_return,
    request_payment_approval,
    list_pending_decisions,
    mark_item_processed,
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


SCAN_PROMPT = """
A new household scan just fired. Do the work:

1. List new inbox items and ingest each one onto the ledger.
2. List open deadlines.
3. For returns due within 7 days, start the return.
4. For bills, request payment approval. Do not pay.
5. For warranties, file a reminder.
6. Mark each inbox file processed.

Then summarize what you did and list any human decisions waiting.
"""
