
import json
import re
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from session_state import SessionState
from prompts_scripts import get_intent_system_prompt




def extract_intent(llm: BaseChatModel, user_message: str) -> dict:
    """
    Sends user message to Qwen for structured intent extraction.
    Returns a dict of confirmed facts (nulls excluded).
    """
    messages = [
        SystemMessage(content=get_intent_system_prompt()),
        HumanMessage(content=user_message),
    ]

    try:
        response = llm.invoke(messages)
        raw = response.content.strip()

        raw = re.sub(r"^```json\s*|```$", "", raw.strip(), flags=re.MULTILINE).strip()

        parsed = json.loads(raw)

        # Return only non-null values
        return {k: v for k, v in parsed.items() if v is not None}

    except (json.JSONDecodeError, AttributeError) as e:
        # Fail safe — return empty, don't crash the pipeline
        print(f"[Intent extraction failed] {e}")
        return {}


def update_session_from_turn(
    llm: BaseChatModel,
    session: SessionState,
    user_message: str,
) -> SessionState:
    """
    Main entry point. Call this at the start of every turn BEFORE retrieval.
    Updates session state with any newly confirmed facts.
    """
    extracted = extract_intent(llm, user_message)

    if extracted:
        session.update(**extracted)
        print(f"[Session updated] {session.summary()}")
    else:
        print(f"[Session unchanged] {session.summary()}")

    return session