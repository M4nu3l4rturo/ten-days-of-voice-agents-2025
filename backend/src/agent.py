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
# Logging
# -------------------------
logger = logging.getLogger("voice_game_master")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# -------------------------
# The Veritas Chamber - Puzzle World Definition
# -------------------------
# A structured puzzle game focusing on observation and item use (The Room style).
WORLD = {
    "intro": {
        "title": "The Veritas Chamber",
        "desc": (
            "You find yourself locked inside a small, octagonal room. A single, ornate **mahogany desk** "
            "dominates the center, facing a small, bolted **wall safe**. On the wall above the safe, "
            "a cryptic **painting** depicts three intertwined geometric shapes. The single exit door is locked by an unusual, keyless mechanism."
        ),
        "choices": {
            "examine_desk": {
                "desc": "Approach and examine the mahogany desk.",
                "result_scene": "desk_clue",
            },
            "look_at_safe": {
                "desc": "Inspect the wall safe and its lock.",
                "result_scene": "safe_details",
            },
            "study_painting": {
                "desc": "Analyze the cryptic painting above the safe.",
                "result_scene": "painting_clue",
            },
        },
    },
    "desk_clue": {
        "title": "The Mahogany Desk",
        "desc": (
            "The desk is old, but meticulously kept. You find a **small brass key** tucked inside an "
            "unlocked drawer, and a **ledger** detailing cryptic financial transactions."
        ),
        "choices": {
            "take_key": {
                "desc": "Take the small brass key.",
                "result_scene": "desk_key_taken",
                "effects": {"add_inventory": "brass_key", "add_journal": "Found small brass key."},
            },
            "read_ledger": {
                "desc": "Review the ledger for clues.",
                "result_scene": "ledger_reveal",
                "effects": {"add_journal": "Ledger entry reads: 'The circle completes the path.'"},
            },
            "return_to_room": {
                "desc": "Step back and look at the main room again.",
                "result_scene": "intro",
            },
        },
    },
    "desk_key_taken": {
        "title": "Desk Searched",
        "desc": (
            "The brass key is now in your pocket. The remaining items on the desk seem ordinary. "
            "Your attention turns back to the safe and the painting."
        ),
        "choices": {
            "look_at_safe": {"desc": "Inspect the wall safe.", "result_scene": "safe_details"},
            "study_painting": {"desc": "Analyze the painting.", "result_scene": "painting_clue"},
        },
    },
    "painting_clue": {
        "title": "The Cryptic Canvas",
        "desc": (
            "The painting is modern and abstract, featuring three overlapping shapes: a **star**, a **pyramid**, and a **circle**. "
            "The star is illuminated by a small, hidden spotlight that casts a shadow pointing towards the safe dial."
        ),
        "choices": {
            "focus_on_star": {
                "desc": "Analyze the Star symbol.",
                "result_scene": "painting_detail",
                "effects": {"add_journal": "Star symbol is illuminated."},
            },
            "check_safe_again": {
                "desc": "Look back at the safe.",
                "result_scene": "safe_details",
            },
        },
    },
    "safe_details": {
        "title": "The Wall Safe",
        "desc": (
            "The safe is a heavy, dark steel box with a three-symbol dial lock. The mechanism requires you to input three unique symbols in a specific order."
        ),
        "choices": {
            "input_code": {
                "desc": "Attempt to input a code using the symbols: Star, Pyramid, Circle.",
                "result_scene": "safe_solved",
                "effects": {"add_journal": "Attempted safe combination: Star, Pyramid, Circle."},
            },
            "return_to_room": {
                "desc": "Go back to the main room.",
                "result_scene": "intro",
            },
        },
    },
    "safe_solved": {
        "title": "Success!",
        "desc": (
            "The safe clicks open silently. Inside, resting on red velvet, is a **heavy silver key** and a small note that simply reads: 'Exit'. "
            "You hear a faint *thunk* near the exit door."
        ),
        "choices": {
            "take_silver_key": {
                "desc": "Take the heavy silver key.",
                "result_scene": "exit_door",
                "effects": {"add_inventory": "silver_key", "add_journal": "Found silver key in safe. Door mechanism engaged."},
            },
            "re_read_note": {
                "desc": "Re-read the 'Exit' note.",
                "result_scene": "safe_solved", # Stay in the scene
            },
        },
    },
    "exit_door": {
        "title": "The Final Lock",
        "desc": (
            "You stand before the main exit door. A small, hidden silver keyhole has appeared next to the keyless mechanism. "
            "The heavy silver key fits perfectly."
        ),
        "choices": {
            "use_silver_key": {
                "desc": "Turn the silver key in the final lock.",
                "result_scene": "escape",
                "effects": {"add_journal": "Used silver key to open exit."},
            },
            "check_inventory": {
                "desc": "Check your journal and inventory.",
                "result_scene": "exit_door", # Rely on Agent calling show_journal
            },
        },
    },
    "escape": {
        "title": "Epilogue: Freedom",
        "desc": (
            "The lock clicks and the heavy exit door swings open, revealing a sunlit hallway. "
            "The clock on the wall reads 11:37 AM. You have solved The Veritas Chamber. Your adventure closes for now."
        ),
        "choices": {
            "restart_game": {
                "desc": "Begin a new session.",
                "result_scene": "intro",
                "effects": {"add_journal": "Completed the challenge."},
            },
        },
    },
    "ledger_reveal": {
        "title": "The Ledger",
        "desc": (
            "The ledger contains only numbers, except for one line: 'The circle completes the path.'. "
            "This seems to hint at the sequence of symbols needed for the safe."
        ),
        "choices": {
            "return_to_room": {
                "desc": "Go back to the main room.",
                "result_scene": "intro",
            },
        },
    },
    "painting_detail": {
        "title": "Star Symbol Detail",
        "desc": (
            "The star is carved from a piece of obsidian, and the shadow it casts shows a subtle **Pyramid** shape hidden in the background."
        ),
        "choices": {
            "return_to_room": {
                "desc": "Go back to the main room.",
                "result_scene": "intro",
            },
        },
    }
}

# -------------------------
# Per-session Userdata (Unchanged)
# -------------------------
@dataclass
class Userdata:
    player_name: Optional[str] = None
    current_scene: str = "intro"
    history: List[Dict] = field(default_factory=list)  # list of {'scene', 'action', 'time', 'result_scene'}
    journal: List[str] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    named_npcs: Dict[str, str] = field(default_factory=dict)
    choices_made: List[str] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

# -------------------------
# Helper functions (Unchanged)
# -------------------------
def scene_text(scene_key: str, userdata: Userdata) -> str:
    """
    Build the descriptive text for the current scene, and append choices as short hints.
    Always end with 'What do you do?' so the voice flow prompts player input.
    """
    scene = WORLD.get(scene_key)
    if not scene:
        return "You are in a featureless void. What do you do?"

    desc = f"{scene['desc']}\n\nChoices:\n"
    for cid, cmeta in scene.get("choices", {}).items():
        # Display short code for ease of voice control
        desc += f"- {cmeta['desc']} (say: {cid.replace('_', ' ').title()})\n" 
    # GM MUST end with the action prompt
    desc += "\nWhat do you do?"
    return desc

def apply_effects(effects: dict, userdata: Userdata):
    if not effects:
        return
    if "add_journal" in effects:
        userdata.journal.append(effects["add_journal"])
    if "add_inventory" in effects:
        userdata.inventory.append(effects["add_inventory"])
    # Extendable for more effect keys

def summarize_scene_transition(old_scene: str, action_key: str, result_scene: str, userdata: Userdata) -> str:
    """Record the transition into history and return a short narrative the GM can use."""
    entry = {
        "from": old_scene,
        "action": action_key,
        "to": result_scene,
        "time": datetime.utcnow().isoformat() + "Z",
    }
    userdata.history.append(entry)
    userdata.choices_made.append(action_key)
    # Changed echo message for new persona
    return f"The puzzle yields to your choice: '{action_key.replace('_', ' ').title()}'."

# -------------------------
# Agent Tools (Unchanged Function Signatures)
# -------------------------

@function_tool
async def start_adventure(
    ctx: RunContext[Userdata],
    player_name: Annotated[Optional[str], Field(description="Player name", default=None)] = None,
) -> str:
    """Initialize a new adventure session for the player and return the opening description."""
    userdata = ctx.userdata
    if player_name:
        userdata.player_name = player_name
    userdata.current_scene = "intro"
    userdata.history = []
    userdata.journal = []
    userdata.inventory = []
    userdata.named_npcs = {}
    userdata.choices_made = []
    userdata.session_id = str(uuid.uuid4())[:8]
    userdata.started_at = datetime.utcnow().isoformat() + "Z"

    opening = (
        f"Greetings {userdata.player_name or 'traveler'}. You have been deemed worthy to attempt '{WORLD['intro']['title']}'.\n\n"
        + scene_text("intro", userdata)
    )
    # Ensure GM prompt present
    if not opening.endswith("What do you do?"):
        opening += "\nWhat do you do?"
    return opening

@function_tool
async def get_scene(
    ctx: RunContext[Userdata],
) -> str:
    """Return the current scene description (useful for 'remind me where I am')."""
    userdata = ctx.userdata
    scene_k = userdata.current_scene or "intro"
    txt = scene_text(scene_k, userdata)
    return txt

@function_tool
async def player_action(
    ctx: RunContext[Userdata],
    action: Annotated[str, Field(description="Player spoken action or the short action code (e.g., 'examine_desk' or 'take the key')")],
) -> str:
    """
    Accept player's action (natural language or action key), try to resolve it to a defined choice,
    update userdata, advance to the next scene and return the GM's next description (ending with 'What do you do?').
    """
    userdata = ctx.userdata
    current = userdata.current_scene or "intro"
    scene = WORLD.get(current)
    action_text = (action or "").strip()

    # Attempt 1: match exact action key (e.g., 'inspect_box')
    chosen_key = None
    if action_text.lower() in (scene.get("choices") or {}):
        chosen_key = action_text.lower()

    # Attempt 2: fuzzy match by checking if action_text contains the choice key or descriptive words
    if not chosen_key:
        # try to find a choice whose description words appear in action_text
        for cid, cmeta in (scene.get("choices") or {}).items():
            desc = cmeta.get("desc", "").lower()
            if cid.replace('_', ' ') in action_text.lower() or any(w in action_text.lower() for w in desc.lower().split()[:4]):
                chosen_key = cid
                break
            
    # Attempt 3: fallback by simple keyword matching against choice descriptions
    if not chosen_key:
        for cid, cmeta in (scene.get("choices") or {}).items():
            for keyword in cmeta.get("desc", "").lower().split():
                if keyword and keyword in action_text.lower():
                    chosen_key = cid
                    break
            if chosen_key:
                break


    if not chosen_key:
        # If we still can't resolve, ask a clarifying GM response but keep it short and end with prompt.
        resp = (
            "I didn't quite catch that action for this situation. Try one of the listed choices or use a simple phrase like 'examine desk' or 'study painting'.\n\n"
            + scene_text(current, userdata)
        )
        return resp

    # Apply the chosen choice
    choice_meta = scene["choices"].get(chosen_key)
    result_scene = choice_meta.get("result_scene", current)
    effects = choice_meta.get("effects", None)

    # Apply effects (inventory/journal, etc.)
    apply_effects(effects or {}, userdata)

    # Record transition
    _note = summarize_scene_transition(current, chosen_key, result_scene, userdata)

    # Update current scene
    userdata.current_scene = result_scene

    # Build narrative reply: echo a short confirmation, then describe next scene
    next_desc = scene_text(result_scene, userdata)

    # A small flourish so the GM sounds more persona-driven
    persona_pre = (
        "The Archivist (a calm, highly intelligent narrator) replies:\n\n"
    )
    reply = f"{persona_pre}{_note}\n\n{next_desc}"
    # ensure final prompt present
    if not reply.endswith("What do you do?"):
        reply += "\nWhat do you do?"
    return reply

@function_tool
async def show_journal(
    ctx: RunContext[Userdata],
) -> str:
    userdata = ctx.userdata
    lines = []
    lines.append(f"Session: {userdata.session_id} | Started at: {userdata.started_at}")
    if userdata.player_name:
        lines.append(f"Player: {userdata.player_name}")
    if userdata.journal:
        lines.append("\nJournal entries (Observations and Clues):")
        for j in userdata.journal:
            lines.append(f"- {j}")
    else:
        lines.append("\nJournal is empty. Have you observed anything yet?")
    if userdata.inventory:
        lines.append("\nInventory (Tools and Keys):")
        for it in userdata.inventory:
            lines.append(f"- {it}")
    else:
        lines.append("\nNo items in inventory.")
    lines.append("\nRecent actions:")
    for h in userdata.history[-6:]:
        lines.append(f"- {h['time']} | from {h['from']} -> {h['to']} via {h['action']}")
    lines.append("\nWhat do you do?")
    return "\n".join(lines)

@function_tool
async def restart_adventure(
    ctx: RunContext[Userdata],
) -> str:
    """Reset the userdata and start again."""
    userdata = ctx.userdata
    userdata.current_scene = "intro"
    userdata.history = []
    userdata.journal = []
    userdata.inventory = []
    userdata.named_npcs = {}
    userdata.choices_made = []
    userdata.session_id = str(uuid.uuid4())[:8]
    userdata.started_at = datetime.utcnow().isoformat() + "Z"
    greeting = (
        "The chamber resets. The mechanisms lock. You stand once more at the beginning.\n\n"
        + scene_text("intro", userdata)
    )
    if not greeting.endswith("What do you do?"):
        greeting += "\nWhat do you do?"
    return greeting

# -------------------------
# The Agent (GameMasterAgent)
# -------------------------
class GameMasterAgent(Agent):
    def __init__(self):
        # System instructions define Universe, Tone, Role
        instructions = """
        You are 'The Archivist', the enigmatic Game Master (GM) for a voice-only, puzzle-box text adventure (similar to 'The Room' games).
        Universe: Modern-day mystery, high-tech puzzles, hidden mechanisms, secret societies. The current game is 'The Veritas Chamber'.
        Tone: Calm, highly intelligent, precise, and slightly detached (focus on observation and deduction).
        Role: You are the GM. You describe chambers and objects vividly, focusing on details relevant to puzzles. You remember the player's tools, inventory, and observations.
              and you always end your descriptive messages with the prompt: 'What do you do?'
        Rules:
            - Use the provided tools to start the adventure, get the current scene, accept the player's spoken action,
              show the player's journal, or restart the adventure.
            - Keep continuity using the per-session userdata. Reference journal items and inventory when relevant.
            - Drive short sessions (aim for several meaningful turns). Each GM message MUST end with 'What do you do?'.
            - Respect that this agent is voice-first: responses should be concise enough for spoken delivery but evocative.
        """
        super().__init__(
            instructions=instructions,
            tools=[start_adventure, get_scene, player_action, show_journal, restart_adventure],
        )

# -------------------------
# Entrypoint & Prewarm (Unchanged)
# -------------------------
def prewarm(proc: JobProcess):
    # load VAD model and stash on process userdata, try/catch like original file
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed; continuing without preloaded VAD.")

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("\n" + "🔑" * 8)
    logger.info("🚀 STARTING VOICE GAME MASTER (The Veritas Chamber)")

    userdata = Userdata()

    # ALL speech plugins are set to English ('en-US-marcus' voice, 'nova-3' model)
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=google.LLM(model="gemini-2.5-flash"),
        tts=murf.TTS(
            voice="en-US-marcus",
            style="Conversational",
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(), # Turn detector remains flexible
        vad=ctx.proc.userdata.get("vad"),
        userdata=userdata,
    )

    # Start the agent session with the GameMasterAgent
    await session.start(
        agent=GameMasterAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()

if __name__ == "__main__":
    # Ensure this block is run via the LiveKit CLI: lk agent run --log-level INFO agent.py
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
