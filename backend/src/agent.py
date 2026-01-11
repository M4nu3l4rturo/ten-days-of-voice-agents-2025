import json
import logging
import os
import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Annotated

from dotenv import load_dotenv
from pydantic import Field
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)

from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# -------------------------
# Configuración de Logs
# -------------------------
logger = logging.getLogger("wellness_companion")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# -------------------------
# Base de Datos de Bienestar (Persistencia)
# -------------------------
WELLNESS_DB = "wellness_history.json"

# Inicializar archivo si no existe
if not os.path.exists(WELLNESS_DB):
    with open(WELLNESS_DB, "w") as f:
        json.dump({"users": {}}, f)

def _load_data() -> Dict:
    """Carga los datos históricos del archivo JSON."""
    try:
        with open(WELLNESS_DB, "r") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

def _save_data(data: Dict):
    """Guarda los datos actualizados en el archivo JSON."""
    with open(WELLNESS_DB, "w") as f:
        json.dump(data, f, indent=4)

# -------------------------
# Estado de la Sesión
# -------------------------
@dataclass
class Userdata:
    user_id: str = "default_user"
    user_name: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    current_mood: Optional[str] = None
    history: List[Dict] = field(default_factory=list)

# -------------------------
# Herramientas del Agente (Tools)
# -------------------------

@function_tool
async def get_wellness_summary(ctx: RunContext[Userdata]) -> str:
    """
    Recupera el resumen de la sesión anterior para preguntar por avances.
    """
    data = _load_data()
    user_info = data["users"].get(ctx.userdata.user_id, {})
    
    last_log = user_info.get("last_log")
    last_goal = user_info.get("current_goal")
    
    if not last_log and not last_goal:
        return "This is our first session. I don't have previous data yet."
    
    summary = "Based on our last talk: "
    if last_log:
        summary += f"You were feeling '{last_log['mood']}' and noted: {last_log['notes']}. "
    if last_goal:
        summary += f"Your active goal was: {last_goal}."
    
    return summary

@function_tool
async def log_mood(
    ctx: RunContext[Userdata],
    mood: Annotated[str, Field(description="The user's current mood or emotional state")],
    notes: Annotated[Optional[str], Field(description="Brief context or reason for this mood", default="")] = ""
) -> str:
    """
    Registra el estado de ánimo actual del usuario en la base de datos persistente.
    """
    data = _load_data()
    uid = ctx.userdata.user_id
    
    if uid not in data["users"]:
        data["users"][uid] = {"logs": [], "current_goal": None}
    
    new_log = {
        "timestamp": datetime.now().isoformat(),
        "mood": mood,
        "notes": notes
    }
    
    data["users"][uid]["logs"].append(new_log)
    data["users"][uid]["last_log"] = new_log
    _save_data(data)
    
    return f"I've noted that you are feeling {mood}. Thank you for sharing that with me."

@function_tool
async def set_goal(
    ctx: RunContext[Userdata],
    goal: Annotated[str, Field(description="A wellness goal the user wants to achieve (e.g., drink more water, meditate)")]
) -> str:
    """
    Guarda una meta de bienestar para el usuario.
    """
    data = _load_data()
    uid = ctx.userdata.user_id
    
    if uid not in data["users"]:
        data["users"][uid] = {"logs": [], "current_goal": None}
        
    data["users"][uid]["current_goal"] = goal
    _save_data(data)
    
    return f"Got it! Your new goal is: {goal}. I'll remember to ask you about it next time."

# -------------------------
# El Agente Aura
# -------------------------
class AuraAgent(Agent):
    def __init__(self):
        # Instrucciones del sistema para definir la personalidad de Aura
        instructions = """
        Your name is Aura, a gentle and empathetic Wellness Companion.
        Your goal is to support the user's emotional and physical well-being.
        
        Style:
        - Warm, calm, and attentive.
        - Use short, soothing sentences.
        - Be proactive: Always ask how they are doing compared to their last session if data is available.
        
        Workflow:
        1. At the start of the call, use 'get_wellness_summary' to see if there is previous history.
        2. If history exists, ask specifically about their previous mood or their active goal.
        3. Listen actively. If they mention feeling a certain way, use 'log_mood'.
        4. If they want to change or set a habit, use 'set_goal'.
        5. Provide gentle wellness advice (breathing, hydration, breaks).
        """
        super().__init__(
            instructions=instructions,
            tools=[get_wellness_summary, log_mood, set_goal],
        )

# -------------------------
# Entrada y Configuración de Voz
# -------------------------
def prewarm(proc: JobProcess):
    """Carga el modelo VAD para detectar voz."""
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed.")

async def entrypoint(ctx: JobContext):
    """Punto de entrada para la sesión de Aura."""
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("🚀 AURA WELLNESS COMPANION STARTING")

    userdata = Userdata()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-marcus",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )

    await session.start(
        agent=AuraAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
