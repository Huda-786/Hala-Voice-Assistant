# Imports
from dotenv import load_dotenv
from livekit.agents import (Agent, AgentSession, JobContext, WorkerOptions, cli, TurnHandlingOptions)
from livekit.plugins import openai, silero, lemonslice
from livekit.agents.llm import ChatMessage
from livekit.agents.stt import StreamAdapter
from edge_TTS import EdgeTTSPlugin
from transformers import AutoProcessor, SeamlessM4TModel
from seamless_stt import SeamlessSTT
from hala import hala_reply
from prompts_scripts import get_rag_template, get_script, get_system_prompt
import asyncio
from langchain_openai import ChatOpenAI
from session_state import SessionState
from intent_extractor import update_session_from_turn
import json
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
    "usa": "https://raw.githubusercontent.com/Huda-786/Avatars/7d901ae1544a00b6ff0a299ab3d6813e79671b97/USA2.jpeg",
    "east_asia": "https://raw.githubusercontent.com/Huda-786/Avatars/3da684f0d2fc88df77ae84afaac4efa170fa3d5a/EA.png"
}


def prewarm(proc):
    print("Prewarming SeamlessM4T...")
    model_id = "facebook/hf-seamless-m4t-medium"

    processor = AutoProcessor.from_pretrained(model_id)
    model = SeamlessM4TModel.from_pretrained(model_id)

    device = "cpu"
    model.to(device)
    model.eval()

    proc.userdata["seamless_processor"] = processor
    proc.userdata["seamless_model"] = model
    proc.userdata["seamless_device"] = device
    print(f"SeamlessM4T ready on {device}.")

# ==============================
# ASSISTANT
# ==============================

class Assistant(Agent):
    def __init__(self, stt_model, selected_lang="en", mode = "reception"):

        self.seam_stt = stt_model  
        self.current_lang = selected_lang
        self.mode = mode
        self.rag_session = SessionState()
        self.intent_llm = ChatOpenAI(
            model="icp_assistant_model_llama_5_q4.gguf",
            base_url="http://llama-server:8000/v1",      #"http://127.0.0.1:1234/v1"
            api_key="lm-studio",
            temperature=0,
        )

        super().__init__(instructions=get_system_prompt())

    async def on_enter(self):  #Initial Greetings!

        if self.mode == "counter":
            welcome_script = get_script()
        else:
            welcome_script = "Welcome to the Ajman Happiness center. How can I help you today?"

        await self.session.say(
             welcome_script,
             allow_interruptions = False,
        )

    async def on_user_turn_completed(self, turn_ctx, new_message):
        self.current_lang = self.seam_stt.last_language or "en"
        print("[DEBUG] Current user language:", self.current_lang)

    async def llm_node(self, chat_ctx, tools, model_settings):

        user_text = ""

        if chat_ctx.items and chat_ctx.items[-1].role == "user":
            user_text = chat_ctx.items[-1].text_content or ""

        user_text_english = self.seam_stt.last_text_english or user_text

        if user_text.strip():
            try:
                chat_ctx.items[-1].content = [user_text_english]
            except Exception:
                pass

        self.rag_session = await asyncio.to_thread(
            update_session_from_turn,
            self.intent_llm,
            self.rag_session,
            user_text_english, 
        )
        
        print("[DEBUG] RAG SESSION:", self.rag_session.summary())

        user_lower = user_text_english.lower()


        try:
            rag_context = await asyncio.to_thread(
                hala_reply,
                user_text_english,
                self.rag_session,
            )
            print(rag_context)

        except Exception as e:
            print("RAG error:", e)
            rag_context = "No relevant context found."
        

        state_prompt = f"""
        CURRENT VERIFIED USER STATE:
        service_type={self.rag_session.service_type}
        nationality={self.rag_session.nationality}
        category={self.rag_session.category}
        topic={self.rag_session.topic}
        age={self.rag_session.age}
        urgency={self.rag_session.urgency}

        MANDATORY DECISION:
        - If nationality is None and the user asks about documents, fees, steps, validity, or eligibility, ask only for nationality.
        - If the topic is fingerprints, and age is None, please get the age from the user. 
        - Do not answer the service question yet.
        - Do not assume resident, UAE national, or GCC national.
        """
        injected_prompt = get_rag_template().format(
            rag_context=rag_context)

        insert_index = len(chat_ctx.items) - 1
        chat_ctx.items.insert(
            insert_index,
            ChatMessage(role="system", content=[state_prompt]),
            
        )

        chat_ctx.items.insert(
            insert_index + 1,
            ChatMessage(
                role="system",
                content=[injected_prompt],
            ),
        )

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
    mode = metadata.get("mode", "reception")

    print("[DEBUG] Selected Mode:", mode)
    print("[DEBUG] Selected frontend language:", selected_lang)
    print("[DEBUG] Selected avatar region:", region)

    processor = ctx.proc.userdata["seamless_processor"]
    model = ctx.proc.userdata["seamless_model"]
    device = ctx.proc.userdata["seamless_device"]
    base_stt_model = SeamlessSTT(processor, model, device, selected_lang=selected_lang)

    vad_model = silero.VAD.load(
        min_speech_duration=0.2,
        min_silence_duration=0.8,
    )

    stt_model = StreamAdapter(
        stt=base_stt_model,
        vad=vad_model,
    )

    assistant = Assistant(base_stt_model, selected_lang = selected_lang, mode = mode)

    session = AgentSession(

        stt=stt_model,

        llm = openai.LLM(
            model="icp_assistant_model_llama_5_q4.gguf",
            base_url="http://llama-server:8000/v1",      #"http://127.0.0.1:1234/v1"
            api_key="lm-studio",
            temperature=0.1,
        ),

        tts=EdgeTTSPlugin(
            get_lang=lambda: assistant.current_lang,
            sample_rate=24000,
        ),

        vad=vad_model,

        turn_handling=TurnHandlingOptions(
            min_endpointing_delay=0.8,
        ),

        use_tts_aligned_transcript=False,
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
            initialize_process_timeout=180,
            num_idle_processes=1,
            multiprocessing_context="spawn",
            job_memory_warn_mb=1600,
        )
    )