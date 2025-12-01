"""
Day 10 – Voice Improv Battle Host

This file implements the required single-player voice agent called "Improv Battle".
The agent acts as a high-energy TV show host, guides the player through improv
scenarios, provides varied feedback, and manages the game state.

Behaviour summary (implemented as tools exposed to the LLM):
- start_show(name, max_rounds): Initialize session state and introduce the show.
- next_scenario(): Advance to the next improv scenario and set the phase to awaiting_improv.
- record_performance(performance): Save the player's improvisation, produce a host reaction, and advance the game state.
- summarize_show(): Produce a closing summary once rounds are complete.
- stop_show(confirm=False): Allow graceful early exit.
"""

import json
import logging
import os
import asyncio
import uuid
import random
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
logger = logging.getLogger("voice_improv_battle")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

load_dotenv(".env.local")

# -------------------------
# Improv Scenarios (Seeded List)
# -------------------------
SCENARIOS = [
    "You are a barista who has to tell a customer that their latte is actually a portal to another dimension.",
    "You are a time-travelling tour guide explaining modern smartphones to someone from the 1800s.",
    "You are a restaurant waiter who must calmly tell a customer that their order has escaped the kitchen.",
    "You are a customer trying to return an obviously cursed object to a very skeptical shop owner.",
    "You are an overenthusiastic TV infomercial host selling a product that clearly does not work as advertised.",
    "You are an astronaut who just discovered the ship's coffee machine has developed a personality.",
    "You are a nervous wedding officiant who keeps getting the couple's names mixed up in ridiculous ways.",
    "You are a ghost trying to give a performance review to a living employee.",
    "You are a medieval king reacting to a very modern delivery service showing up at court.",
    "You are a detective interrogating a suspect who only answers in awkward metaphors."
]

# -------------------------
# Per-session Improv State (as required)
# -------------------------
@dataclass
class Userdata:
    player_name: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    improv_state: Dict = field(default_factory=lambda: {
        "current_round": 0,
        "max_rounds": 3,
        "rounds": [],  # each: {"scenario": str, "performance": str, "reaction": str}
        "phase": "idle",  # "intro" | "awaiting_improv" | "reacting" | "done" | "idle"
        "used_indices": []
    })
    history: List[Dict] = field(default_factory=list)

# -------------------------
# Helpers for Game Logic
# -------------------------

def _pick_scenario(userdata: Userdata) -> str:
    """Picks a scenario that hasn't been used yet, or resets the list."""
    used = userdata.improv_state.get("used_indices", [])
    candidates = [i for i in range(len(SCENARIOS)) if i not in used]
    if not candidates:
        # Reset if we exhausted scenarios (ensures game can run long)
        userdata.improv_state["used_indices"] = []
        candidates = list(range(len(SCENARIOS)))
    
    idx = random.choice(candidates)
    userdata.improv_state["used_indices"].append(idx)
    return SCENARIOS[idx]


def _host_reaction_text(performance: str) -> str:
    """Generates a varied host reaction (supportive, neutral, or mildly critical)."""
    # Tones required: supportive, neutral, mildly critical (non-abusive)
    tones = ["supportive", "neutral", "mildly_critical"]
    tone = random.choice(tones)
    
    # Quick keyword detection to pick specific highlights
    highlights = []
    if any(w in performance.lower() for w in ("laugh", "funny", "haha", "joke")):
        highlights.append("great comedic timing")
    if any(w in performance.lower() for w in ("sad", "cry", "tears", "emotion")):
        highlights.append("good emotional depth")
    if any(w in performance.lower() for w in ("pause", "silence", "...", "wait")):
        highlights.append("interesting use of silence or pacing")
    if not highlights:
        highlights.append(random.choice(["nice character choices", "bold commitment", "unexpected twist"]))

    chosen = random.choice(highlights)
    
    # Generate varied feedback based on tone
    if tone == "supportive":
        return f"FANTASTIC! Love that — {chosen}! That was playful and clear. Nice work, {tone.upper()} feedback today! Ready for the next one?"
    elif tone == "neutral":
        return f"Hmm — {chosen}. That landed in parts; you had interesting ideas. Let's try the next scene and lean into one strong choice."
    else:  # mildly_critical
        return f"Okay — {chosen}, but that felt a bit rushed. Try to make stronger, clearer choices next time. Don't be afraid to exaggerate, Contesant!"

# -------------------------
# Agent Tools (Functions)
# -------------------------
@function_tool
async def start_show(
    ctx: RunContext[Userdata],
    name: Annotated[Optional[str], Field(description="Player/contestant name (optional)", default=None)] = None,
    max_rounds: Annotated[int, Field(description="Number of rounds (3-5 recommended)", default=3)] = 3,
) -> str:
    """Initializes and introduces the Improv Battle show, and presents the first scenario."""
    userdata = ctx.userdata
    if name:
        userdata.player_name = name.strip()
    else:
        # Use existing name or fallback
        userdata.player_name = userdata.player_name or "Contestant"

    # Clamp rounds for safe play (1-8)
    max_rounds = max(1, min(8, max_rounds))

    # Reset state
    userdata.improv_state["max_rounds"] = int(max_rounds)
    userdata.improv_state["current_round"] = 0
    userdata.improv_state["rounds"] = []
    userdata.improv_state["phase"] = "intro"
    userdata.improv_state["used_indices"] = [] # Reset scenario use

    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "start_show", "name": userdata.player_name})

    intro = (
        f"WELCOME TO IMPROV BATTLE! I'm your high-energy host, and we're ready to play."
        f" {userdata.player_name}, we'll be running {userdata.improv_state['max_rounds']} rounds today! "
        "Rules are simple: I'll give you a scene, you act it out, and when you're done say 'End scene' or pause. I'll react, and we move on! Ready to go?!"
    )
    
    # After intro, immediately provide first scenario for flow
    scenario = _pick_scenario(userdata)
    userdata.improv_state["current_round"] = 1
    userdata.improv_state["phase"] = "awaiting_improv"
    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "present_scenario", "round": 1, "scenario": scenario})

    return intro + "\n\n**ROUND 1:** " + scenario + "\n\nStart improvising... NOW!"


@function_tool
async def next_scenario(ctx: RunContext[Userdata]) -> str:
    """Advances the game to the next scenario if not complete."""
    userdata = ctx.userdata
    if userdata.improv_state.get("phase") == "done":
        return "The show is already over! Say 'start show' to play again."

    cur = userdata.improv_state.get("current_round", 0)
    maxr = userdata.improv_state.get("max_rounds", 3)
    
    # Check for summary condition
    if cur >= maxr:
        userdata.improv_state["phase"] = "done"
        return await summarize_show(ctx)

    # Advance round
    next_round = cur + 1
    scenario = _pick_scenario(userdata)
    userdata.improv_state["current_round"] = next_round
    userdata.improv_state["phase"] = "awaiting_improv"
    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "present_scenario", "round": next_round, "scenario": scenario})
    
    return f"**ROUND {next_round}**: {scenario}\n\nHit me with your best shot!"


@function_tool
async def record_performance(
    ctx: RunContext[Userdata],
    performance: Annotated[str, Field(description="Player's improv performance (transcribed text)")],
) -> str:
    """Records the player's performance, generates a host reaction, and prepares for the next round or closure."""
    userdata = ctx.userdata
    
    # Check if we are in the correct phase, but proceed anyway to capture user input
    if userdata.improv_state.get("phase") not in ["awaiting_improv", "reacting"]:
        userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "record_performance_out_of_phase"})

    round_no = userdata.improv_state.get("current_round", 0)
    
    # Try to find the scenario from the history for logging
    scenario = "(Unknown Scenario)"
    for item in reversed(userdata.history):
        if item.get("action") == "present_scenario" and item.get("round") == round_no:
            scenario = item.get("scenario")
            break

    reaction = _host_reaction_text(performance) # Use our helper for varied tone

    # Store round data
    userdata.improv_state["rounds"].append({
        "round": round_no,
        "scenario": scenario,
        "performance": performance,
        "reaction": reaction, # Store the reaction text
    })
    userdata.improv_state["phase"] = "reacting"
    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "record_performance", "round": round_no})

    # Check for max rounds
    if round_no >= userdata.improv_state.get("max_rounds", 3):
        userdata.improv_state["phase"] = "done"
        closing = "\n" + reaction + "\n\nThat's the final round! "
        closing += (await summarize_show(ctx))
        return closing

    # Otherwise, prompt to move to the next round
    closing = reaction + "\n\nReady for the next challenge? Just say 'Next Scenario' or 'Next Round'!"
    return closing


@function_tool
async def summarize_show(ctx: RunContext[Userdata]) -> str:
    """Produces the required closing summary of the player's performance style."""
    userdata = ctx.userdata
    rounds = userdata.improv_state.get("rounds", [])
    if not rounds:
        return "No complete rounds were played. Thanks for stopping by Improv Battle!"

    # Aggregate simple metrics for the summary
    mentions_character = sum(1 for r in rounds if any(w in (r.get('performance') or '').lower() for w in ('i am', "i'm", 'role', 'character')))
    mentions_absurdity = sum(1 for r in rounds if any(w in (r.get('performance') or '').lower() for w in ('ridiculous', 'crazy', 'wtf', 'impossible')))
    mentions_emotion = sum(1 for r in rounds if any(w in (r.get('performance') or '').lower() for w in ('sad', 'angry', 'happy', 'love', 'cry')))

    summary_lines = [f"That's a wrap! What a show, {userdata.player_name or 'Contestant'}! Here's your final scorecard:"]
    
    # Determine player style
    profile = "Based on those scenes, you're a player who "
    if mentions_absurdity > len(rounds) / 2:
        profile += "**leans into the absurd** and loves a surprising twist!"
    elif mentions_character > len(rounds) / 2:
        profile += "**commits strongly to character** and clearly sets up the scene."
    elif mentions_emotion > 0:
        profile += "**brings real emotional depth** to the situation, which is key!"
    else:
        profile += "has a fantastic **sense of pacing**! Keep making clear choices."

    summary_lines.append(profile)
    summary_lines.append("\n**Final Standout Moments:**")
    
    # Highlight the reaction from the final round
    final_reaction = rounds[-1].get('reaction', 'Great performance overall!') if rounds else 'Fantastic performance!'
    summary_lines.append(f"- Your last scene got this reaction: '{final_reaction}'")
    
    summary_lines.append("\nThanks for battling it out on Improv Battle — hope to see you next time!")

    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "summarize_show"})
    return "\n".join(summary_lines)


@function_tool
async def stop_show(ctx: RunContext[Userdata], confirm: Annotated[bool, Field(description="Confirm stop", default=False)] = False) -> str:
    """Allows for a graceful early exit from the show."""
    userdata = ctx.userdata
    if not confirm:
        return "Are you sure you want to stop the show? Say 'stop show yes' to confirm."
    userdata.improv_state["phase"] = "done"
    userdata.history.append({"time": datetime.utcnow().isoformat() + "Z", "action": "stop_show"})
    return "Show stopped. Thanks for coming to Improv Battle, you're a star!"


# -------------------------
# The Agent (Improv Host)
# -------------------------
class GameMasterAgent(Agent):
    def __init__(self):
        # System Prompt aligned with requirements: Role, Style, Rules
        instructions = """
        You are the host of a high-energy TV improv show called 'Improv Battle'.
        Role: High-energy, witty, clear about rules, and acts as the game manager. Guide a single contestant through short improv scenes.

        Behavioural rules:
            - Introduce the show and explain the rules at the start.
            - Present clear scenario prompts (who you are, what's happening, what's the tension).
            - After the player's performance, use the output of `record_performance` to deliver a varied, realistic reaction (supportive, neutral, or mildly critical). The host must never be abusive, only constructive.
            - Prompt the player clearly for the next action.
            - Run the configured number of rounds, then summarize the player's style using the `summarize_show` tool.
            - Keep turns short and exciting.
            
        Use the provided tools: start_show, next_scenario, record_performance, summarize_show, stop_show.
        """
        super().__init__(
            instructions=instructions,
            tools=[start_show, next_scenario, record_performance, summarize_show, stop_show],
        )

# -------------------------
# Entrypoint & Prewarm (Standard LiveKit setup)
# -------------------------
def prewarm(proc: JobProcess):
    """Pre-loads the VAD model."""
    try:
        proc.userdata["vad"] = silero.VAD.load()
    except Exception:
        logger.warning("VAD prewarm failed; continuing without preloaded VAD.")


async def entrypoint(ctx: JobContext):
    """Main entrypoint for the agent job."""
    ctx.log_context_fields = {"room": ctx.room.name}
    logger.info("\n" + "🎭" * 6)
    logger.info("🚀 STARTING VOICE IMPROV HOST — Improv Battle")

    userdata = Userdata()

    # AgentSession setup: STT (Deepgram), LLM (Gemini), TTS (Murf), Turn Detection
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

    # Start the session with the GameMasterAgent
    await session.start(
        agent=GameMasterAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(noise_cancellation=noise_cancellation.BVC()),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
