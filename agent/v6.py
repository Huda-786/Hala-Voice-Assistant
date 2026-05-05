# Imports
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    TurnHandlingOptions,
)
from edge_TTS import EdgeTTSPlugin
from hala import hala_reply
from livekit.agents.llm import ChatMessage
import asyncio
from seamless_stt import SeamlessSTT
from transformers import AutoProcessor, SeamlessM4TModel
import torch
import json
from livekit.plugins import openai, silero, lemonslice
import os
load_dotenv()

# ==============================
# PREWARM
# ==============================

AVATAR_MAP = {
    "south_asia": "https://raw.githubusercontent.com/Huda-786/Avatars/e6b3de740cab3789333d973b31979eb462e934c2/SA.png",
    "africa": "https://raw.githubusercontent.com/Huda-786/Avatars/e6b3de740cab3789333d973b31979eb462e934c2/AA.png",
    "europe": "https://raw.githubusercontent.com/Huda-786/Avatars/e6b3de740cab3789333d973b31979eb462e934c2/SP.png",
    "middle_east": "https://raw.githubusercontent.com/Huda-786/Avatars/e6b3de740cab3789333d973b31979eb462e934c2/UAE.png",
    "usa": "https://raw.githubusercontent.com/Huda-786/Avatars/e6b3de740cab3789333d973b31979eb462e934c2/USA.png",
    "east_asia": "https://raw.githubusercontent.com/Huda-786/Avatars/3da684f0d2fc88df77ae84afaac4efa170fa3d5a/EA.png"
}


def prewarm(proc):
    print("Prewarming SeamlessM4T...")
    model_id = "facebook/hf-seamless-m4t-medium"

    processor = AutoProcessor.from_pretrained(model_id)
    model = SeamlessM4TModel.from_pretrained(model_id)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()

    proc.userdata["seamless_processor"] = processor
    proc.userdata["seamless_model"] = model
    proc.userdata["seamless_device"] = device
    print(f"SeamlessM4T ready on {device}.")

# ==============================
# PROMPTS
# ==============================

SYSTEM_PROMPT = """
You are Hala, a warm and friendly AI assistant stationed on a tablet inside the Ajman Happiness Center in Al Jurf, run by ICP.
The working hour of the center is from 7 AM till 4:30 PM from Monday till Friday.
The visitor is physically standing inside the Ajman Happiness Center, Al Jurf.
If asked about location, remind them they are already here.

PERSONALITY:
- Welcoming, calm, and reassuring.
- Speak naturally, like a kind staff member.
- Never sound robotic.
- Keep responses to 2 short sentences maximum.
- Do not use bullet points unless the visitor explicitly asks for a list.
- Use phrases like "Here at this center..." or "You can do that right here..."
- Ask only ONE follow-up question per turn.

SCOPE:
You only help with ICP-related services and center guidance.
If the request is unrelated, politely say you can only help with ICP services at this center.
You cannot answer anything outside the ICP services.

IMPORTANT: DO NOT ASSUME ANYTHING ABOUT THE USER UNLESS THE USER SPECIFICALLY STATES WHO THEY ARE.
RULES:
- Keep answers very short — 1-2 sentences.
- Only ask ONE question at a time.
- Only tell them what's in the provided Information below. Never guess or invent.
- Ask their category (UAE national, resident, GCC national) only when needed for a service.
- If the visitor is a GCC national and subcategory is UNKNOWN, ask whether they are employee, investor, student, property owner, scholar, or family connection.
- Even when reference material is available, always ask clarifying questions if the visitor's situation is ambiguous.
- Never assume the visitor's category, age, or specific situation unless they have explicitly stated it.
"""

RAG_INJECTION_TEMPLATE = """

---
RELEVANT ICP INFORMATION (use only what applies to this visitor's confirmed situation — do not assume their category or details):
{rag_context}

---

Visitor message: {user_text}"""

RETRIEVAL_SKIP_PHRASES = {
    "okay", "ok", "yes", "no", "thank you", "thanks", "sure",
    "alright", "got it", "great", "fine", "yep", "nope", "bye",
    "goodbye", "hello", "hi", "hey", "good morning", "good afternoon"
}

# ==============================
# ASSISTANT
# ==============================

class Assistant(Agent):
    def __init__(self, stt_model, selected_lang="en"):
        self.whisper_stt = stt_model
        self.current_lang = selected_lang

        super().__init__(instructions=SYSTEM_PROMPT)

    async def on_enter(self):
        await self.session.say(
            "Welcome to the Ajman Happiness Centre. How can I help you today?"
        )

    async def on_user_turn_completed(self, turn_ctx, new_message):
        self.current_lang = self.whisper_stt.last_language or "en"
        print("[DEBUG] Current user language:", self.current_lang)

    async def llm_node(self, chat_ctx, tools, model_settings):

        # ── 1. Get the user's original message ──────────────────────────────
        user_text = ""
        if chat_ctx.items and chat_ctx.items[-1].role == "user":
            user_text = chat_ctx.items[-1].text_content or ""

        # ── 2. Use English translation for RAG retrieval ─────────────────────
        user_text_english = self.whisper_stt.last_text_english or user_text

        # ── 3. Decide whether to run RAG ─────────────────────────────────────
        # Skip retrieval for trivial/short messages to avoid bad chunk injection
        should_retrieve = (
            len(user_text_english.split()) >= 3
            and user_text_english.lower().strip() not in RETRIEVAL_SKIP_PHRASES
        )

        rag_context = ""
        if should_retrieve:
            try:
                rag_context = await asyncio.to_thread(
                    hala_reply,
                    user_text_english,
                )
                print("[DEBUG] RAG context retrieved:", rag_context[:200] if rag_context else "None")
            except Exception as e:
                print("[DEBUG] RAG error:", e)
                rag_context = ""

        # ── 4. Build the enriched user message ──────────────────────────────
        # FIX: We enrich the USER message instead of inserting a second system
        # message. LLaMA 3 Instruct expects exactly one system block at the
        # start; a second system block mid-conversation causes the model to
        # echo/leak prompt content and abandon its fine-tuned behaviour.
        if rag_context:
            enriched_content = RAG_INJECTION_TEMPLATE.format(
                rag_context=rag_context,
                user_text=user_text_english,
            )
        else:
            # No RAG — just pass the (possibly translated) user text as-is
            enriched_content = user_text_english

        # Replace the last user message content with the enriched version
        try:
            chat_ctx.items[-1].content = [enriched_content]
        except Exception as e:
            print("[DEBUG] Could not update user message content:", e)

        # ── 5. Stream response from the LLM ──────────────────────────────────
        async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
            yield chunk

# ==============================
# ENTRYPOINT
# ==============================

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    participant = await ctx.wait_for_participant()

    try:
        metadata = json.loads(participant.metadata or "{}")
    except Exception:
        metadata = {}

    selected_lang = metadata.get("lang", "en")
    region = metadata.get("region", "usa")

    print("[DEBUG] Selected frontend language:", selected_lang)
    print("[DEBUG] Selected avatar region:", region)

    processor = ctx.proc.userdata["seamless_processor"]
    model = ctx.proc.userdata["seamless_model"]
    device = ctx.proc.userdata["seamless_device"]
    stt_model = SeamlessSTT(processor, model, device, selected_lang=selected_lang)

    assistant = Assistant(stt_model, selected_lang=selected_lang)

    session = AgentSession(

        stt=stt_model,

        llm=openai.LLM(
            model=os.getenv("LLM_MODEL", "icp-assistant-qwen@q6_k"),
            base_url=os.getenv("LLM_BASE_URL", "http://llama-server:8000/v1"),
            api_key="local",
            temperature=0.1,
        ),

        tts=EdgeTTSPlugin(
            get_lang=lambda: assistant.current_lang,
            sample_rate=24000,
        ),

        vad=silero.VAD.load(
            min_speech_duration=0.2,
            min_silence_duration=0.8,
        ),

        turn_handling=TurnHandlingOptions(
            min_endpointing_delay=0.8,
        ),

        use_tts_aligned_transcript=True,
    )

    avatar = lemonslice.AvatarSession(
        api_key=os.getenv("LEMONSLICE_API_KEY"),
        agent_image_url=AVATAR_MAP.get(region, AVATAR_MAP["usa"]),
        agent_prompt="""You are Hala, a warm and professional ICP assistant. Be calm, friendly, welcoming, and naturally expressive. Use gentle facial expressions and natural movement.""",
        avatar_participant_identity="hala-avatar",
        avatar_participant_name="Hala Avatar",
    )

    await avatar.start(
        session,
        room=ctx.room)

    await session.start(
        agent=assistant,
        room=ctx.room,
    )

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            initialize_process_timeout=120
        )
    )