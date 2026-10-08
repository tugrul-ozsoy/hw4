"""Campus Customs shop agent: PydanticAI + OpenAI through Portkey.

The FastAPI app (main.py) calls `run_chat()` for every message from the website's chat widget.
The agent answers from the live catalogue through the tools in tools.py and returns a ShopReply:
Markdown text plus the ids of the products it talked about (main.py turns those into product cards).

Every agent-loop iteration appends one AuditEntry to output/audit_trail.json (an append-only JSON list,
never wiped): time, tools called with short args and result previews, and the stop reason. Only the user
id is recorded, never names or emails.
"""

from __future__ import annotations

import functools
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext  # noqa: E402
from pydantic_ai.messages import (  # noqa: E402
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from pydantic import TypeAdapter  # noqa: E402
from pydantic_core import to_json  # noqa: E402

from backend.guardrails import foreign_emails  # noqa: E402
from backend.models import AuditEntry, AuditToolCall, ChatTurn, ShopDeps, ShopReply  # noqa: E402
from backend.tools import TOOLS  # noqa: E402

ROOT = Path(__file__).resolve().parent
PROMPT_PATH = ROOT / "prompts" / "prompt.md"
AUDIT_PATH = ROOT.parent / "output" / "audit_trail.json"

MODEL_NAME = os.getenv("CHAT_MODEL", "gpt-5.6-luna")
MODEL_SETTINGS = OpenAIResponsesModelSettings(
    openai_reasoning_effort=os.getenv("CHAT_REASONING_EFFORT", "low"),  # quick replies for a shop chat
    max_tokens=1200,
)
# Hard caps per chat turn so a confused or manipulated run cannot loop or run up cost.
USAGE_LIMITS = UsageLimits(request_limit=6, tool_calls_limit=10, total_tokens_limit=60_000)
MAX_HISTORY_TURNS = 20
PREVIEW_CHARS = 300

_audit_lock = threading.Lock()


class AgentUnavailable(RuntimeError):
    """The model API key is missing, so the chat cannot run."""


def portkey_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if api_key:  # course default: OpenAI models through the Portkey gateway
        headers = {"x-portkey-api-key": api_key, "x-portkey-provider": "openai"}
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.portkey.ai/v1", default_headers=headers,
                             max_retries=3, timeout=90)
    elif os.getenv("OPENAI_API_KEY"):  # fallback: a plain OpenAI key (set CHAT_MODEL to a model it can use)
        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=3, timeout=90)
    else:
        raise AgentUnavailable("No model key: set PORTKEY_API_KEY (or OPENAI_API_KEY) in HW4/.env")
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@functools.cache
def build_agent() -> Agent[ShopDeps, ShopReply]:
    agent = Agent(
        portkey_model(),
        deps_type=ShopDeps,
        output_type=ShopReply,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=TOOLS,
        model_settings=MODEL_SETTINGS,
        retries=2,
    )

    @agent.instructions
    def shopper_context(ctx: RunContext[ShopDeps]) -> str:
        """Per-request facts: who is chatting (first name only) and which product page is open."""
        d = ctx.deps
        lines = ["## This conversation"]
        if d.user_id:
            lines.append(f"- Logged-in shopper: {d.first_name} {d.last_name or ''} <{d.email}>, member since "
                         f"{d.member_since}. Their earlier chats with you are loaded as history, so you can refer "
                         "back to them. Call them by first name now and then; mention their email only if they ask.")
        else:
            lines.append("- The shopper is browsing as a guest (not logged in). You don't know their name or "
                         "email, and this chat is not saved. If asked, suggest logging in to save chats.")
        if d.current_product_id:
            lines.append(f'- They are on the product page for "{d.current_product_name}" '
                         f'(product_id: {d.current_product_id}). "This", "it" or "this one" means that product.')
            lines.append(f"  Page facts: {d.current_product_facts}. For price or stock, still call a tool.")
        else:
            lines.append("- They are not on a product page right now.")
        return "\n".join(lines)

    @agent.output_validator
    def numbers_come_from_the_database(ctx: RunContext[ShopDeps], output: ShopReply) -> ShopReply:
        """Reject replies that state a price or stock count no tool returned in this turn."""
        prices, quantities = _tool_facts(ctx.messages)
        prices |= {float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(ctx.prompt or ""))}  # shopper's own budget
        bad_prices = sorted({p for p in _stated_prices(output.reply) if p not in prices})
        bad_counts = sorted({q for q in _stated_quantities(output.reply) if q not in quantities})
        leaked = foreign_emails(output.reply, ctx.deps.email)
        if leaked:  # privacy: only the shopper's own email or the store's may appear
            raise ModelRetry("Remove these email addresses from your reply; you may only show the shopper's own "
                             f"email or the store's order email: {', '.join(leaked)}")
        if bad_prices or bad_counts:
            problems = [f"price ${p:g}" for p in bad_prices] + [f"quantity {q}" for q in bad_counts]
            raise ModelRetry(
                f"Your reply states {', '.join(problems)}, but no tool returned that in this turn. Call "
                "get_product_details, check_size or search_products and quote only the numbers they return."
            )
        return output

    return agent


def _walk(value: object, prices: set[float], quantities: set[int]) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("price", "min_price", "max_price") and isinstance(item, (int, float)):
                prices.add(float(item))
            elif key == "price_range" and item:
                prices.update(float(x) for x in item)
            elif key in ("quantity", "total_stock") and isinstance(item, int):
                quantities.add(item)
            else:
                _walk(item, prices, quantities)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _walk(item, prices, quantities)


def _tool_facts(messages: list[ModelMessage]) -> tuple[set[float], set[int]]:
    """Every price and stock quantity returned by a tool in this run."""
    prices: set[float] = set()
    quantities: set[int] = set()
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolReturnPart):
                _walk(part.content, prices, quantities)
    return prices, quantities


def _stated_prices(text: str) -> set[float]:
    return {float(x.replace(",", "")) for x in re.findall(r"\$\s?(\d[\d,]*(?:\.\d{1,2})?)", text)}


def _stated_quantities(text: str) -> set[int]:
    patterns = [r"\bonly\s+(\d+)\b", r"\b(\d+)\s+(?:left|in stock|units?|available|remaining)\b"]
    return {int(n) for pattern in patterns for n in re.findall(pattern, text, flags=re.IGNORECASE)}


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Earlier chat turns from the website, as PydanticAI messages (most recent MAX_HISTORY_TURNS)."""
    messages: list[ModelMessage] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def _preview(value: object) -> str:
    text = value if isinstance(value, str) else to_json(value).decode("utf-8", "replace")
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 1] + "…"


AUDIT_ROWS = TypeAdapter(list[AuditEntry])


def append_audit(entry: AuditEntry) -> None:
    """Append one record to output/audit_trail.json, keeping every earlier record (never wiped)."""
    with _audit_lock:
        rows = AUDIT_ROWS.validate_json(AUDIT_PATH.read_bytes()) if AUDIT_PATH.exists() else []
        rows.append(entry)
        AUDIT_PATH.parent.mkdir(exist_ok=True)
        temp = AUDIT_PATH.with_suffix(".json.tmp")
        temp.write_bytes(AUDIT_ROWS.dump_json(rows, indent=2))
        temp.replace(AUDIT_PATH)  # swap in whole, so a crash mid-write can't corrupt the trail


def _calls(response: ModelResponse | None) -> list[ToolCallPart]:
    return [p for p in (response.parts if response else []) if isinstance(p, ToolCallPart)]


def _outcome(response: ModelResponse, after: object) -> tuple[dict[str, str], str]:
    """Tool results and stop reason for one iteration, read from the graph node that came after it."""
    finish = f"finish_reason={response.finish_reason}"
    if Agent.is_end_node(after):
        return {}, f"run finished: final answer returned ({finish})"
    parts = after.request.parts
    results = {p.tool_call_id: _preview(p.content if isinstance(p, ToolReturnPart) else p.model_response())
               for p in parts if isinstance(p, (ToolReturnPart, RetryPromptPart)) and p.tool_call_id}
    retried = [p.tool_name or "output" for p in parts if isinstance(p, RetryPromptPart)]
    if any(name == "final_result" for name in retried):
        reason = "output check rejected the answer and asked for a retry (e.g. a number no tool returned)"
    elif retried:
        reason = f"{', '.join(retried)} asked for a retry"
    else:
        reason = "tool results sent back to the model; loop continues"
    return results, f"{reason} ({finish})"


async def run_chat(message: str, history: list[ChatTurn], deps: ShopDeps, user_id: int | None) -> ShopReply:
    """Answer one shopper message, appending an audit record as each agent-loop iteration finishes."""
    agent = build_agent()
    run_id, iteration, pending = uuid.uuid4().hex[:8], 0, None
    base = dict(run_id=run_id, model=MODEL_NAME, user_id=user_id, page_product_id=deps.current_product_id,
                message=_preview(message))

    def record(response: ModelResponse | None, results: dict[str, str], stop_reason: str,
               reply: ShopReply | None = None) -> None:
        usage = getattr(response, "usage", None)
        append_audit(AuditEntry(
            **base, iteration=iteration, time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            tool_calls=[AuditToolCall(tool=c.tool_name, args=c.args_as_dict(), result=results.get(c.tool_call_id))
                        for c in _calls(response) if c.tool_name != "final_result"],
            reply=_preview(reply.reply) if reply else None, product_ids=reply.product_ids if reply else [],
            stop_reason=stop_reason, input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        ))

    try:
        async with agent.iter(message, deps=deps, message_history=to_message_history(history),
                              usage_limits=USAGE_LIMITS) as run:
            async for node in run:
                if pending is not None:  # the previous model response's tools have now run
                    iteration += 1
                    results, stop_reason = _outcome(pending, node)
                    final = run.result.output if Agent.is_end_node(node) else None
                    record(pending, results, stop_reason, final)
                    pending = None
                if Agent.is_call_tools_node(node):
                    pending = node.model_response
            return run.result.output
    except Exception as exc:
        iteration += 1
        record(pending, {}, f"error: {type(exc).__name__}: {exc}"[:300])
        raise
