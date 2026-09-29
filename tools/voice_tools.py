"""
Voice Tools for Llama Assistant
These tools allow Llama to listen and speak.
"""

import threading
from core.voice_interface import get_voice_interface


def listen_for_command() -> str:
    """
    Listen for a voice command and transcribe it to text.
    Returns the transcribed text.
    """
    voice = get_voice_interface()
    text = voice.listen_command()
    if text:
        return f"Command: {text}"
    return "No command heard."


def speak_response(text: str) -> str:
    """
    Convert text to speech and speak it aloud.
    Args:
        text: The text to speak.
    """
    if not text or not text.strip():
        return "Nothing to speak."
    voice = get_voice_interface()
    result = voice.speak(text)
    return result


def speak_async(text: str) -> str:
    """
    Speak text aloud without blocking (non-blocking).
    """
    if not text or not text.strip():
        return "Nothing to speak."
    voice = get_voice_interface()
    voice.speak_async(text)
    return f"Speaking: {text[:50]}..."


def set_voice_rate(rate: int) -> str:
    """
    Set the speaking speed.
    Args:
        rate: Words per minute (typically 100-300).
    """
    voice = get_voice_interface()
    return voice.set_rate(rate)


def set_voice_volume(volume: int) -> str:
    """
    Set the speaking volume.
    Args:
        volume: 0 to 100.
    """
    voice = get_voice_interface()
    return voice.set_volume(volume / 100.0)


def set_voice_gender(gender: str) -> str:
    """
    Set the voice gender.
    Args:
        gender: 'male' or 'female'.
    """
    voice = get_voice_interface()
    voices = voice.list_voices()
    for v in voices:
        if gender.lower() in v['name'].lower() or gender.lower() in str(v.get('gender', '')).lower():
            return voice.set_voice(v['id'])
    avail = [v['name'] for v in voices] if voices else "None"
    return f"No {gender} voice found. Available: {avail}"


def list_available_voices() -> str:
    """
    List all available TTS voices.
    """
    voice = get_voice_interface()
    voices = voice.list_voices()
    if not voices:
        return "No voices available."
    return "\n".join([f"- {v['name']} ({v.get('gender', 'unknown')})" for v in voices])


def wait_for_wake_word() -> str:
    """
    Wait for the wake word ('Hey Llama'), then record a command.
    Returns the transcribed command.
    """
    voice = get_voice_interface()
    text = voice.listen_with_wake_word()
    if text:
        return f"Command: {text}"
    return "No command heard or wake word not detected."


def start_continuous_mode(callback=None) -> str:
    """
    Start continuous listening mode in background.
    When wake word is detected, it will process the command.
    """
    voice = get_voice_interface()
    
    def default_callback(text):
        print(f"🎤 Voice Command: {text}")
        
    cb = callback or default_callback
    voice.start_continuous_listening(cb)
    return "Continuous listening started. Say 'Hey Llama' to activate."


def stop_continuous_mode() -> str:
    """
    Stop continuous listening mode.
    """
    voice = get_voice_interface()
    return voice.stop_listening()


def get_voice_status() -> dict:
    """
    Get the current voice interface status.
    """
    voice = get_voice_interface()
    return voice.get_status()


# Tool registry registration info
VOICE_TOOLS = {
    "listen_for_command": {
        "function": listen_for_command,
        "description": "Listen for a voice command and convert to text.",
        "parameters": {},
        "returns": "Transcribed text of the command."
    },
    "speak_response": {
        "function": speak_response,
        "description": "Speak text aloud using text-to-speech.",
        "parameters": {"text": "The text to speak."},
        "returns": "Confirmation message."
    },
    "speak_async": {
        "function": speak_async,
        "description": "Speak text aloud without blocking (non-blocking).",
        "parameters": {"text": "The text to speak."},
        "returns": "Confirmation message."
    },
    "set_voice_rate": {
        "function": set_voice_rate,
        "description": "Set speaking speed (words per minute).",
        "parameters": {"rate": "Speed in wpm (100-300)."},
        "returns": "Confirmation message."
    },
    "set_voice_volume": {
        "function": set_voice_volume,
        "description": "Set speaking volume (0-100).",
        "parameters": {"volume": "Volume level 0-100."},
        "returns": "Confirmation message."
    },
    "set_voice_gender": {
        "function": set_voice_gender,
        "description": "Set voice gender (male or female).",
        "parameters": {"gender": "'male' or 'female'."},
        "returns": "Confirmation message."
    },
    "list_available_voices": {
        "function": list_available_voices,
        "description": "List all available TTS voices.",
        "parameters": {},
        "returns": "List of voice names."
    },
    "wait_for_wake_word": {
        "function": wait_for_wake_word,
        "description": "Wait for wake word 'Hey Llama', then record command.",
        "parameters": {},
        "returns": "Transcribed command text."
    },
    "start_continuous_mode": {
        "function": start_continuous_mode,
        "description": "Start background listening for wake word.",
        "parameters": {},
        "returns": "Confirmation message."
    },
    "stop_continuous_mode": {
        "function": stop_continuous_mode,
        "description": "Stop background listening mode.",
        "parameters": {},
        "returns": "Confirmation message."
    },
    "get_voice_status": {
        "function": get_voice_status,
        "description": "Get the current voice interface status.",
        "parameters": {},
        "returns": "Status dictionary."
    }
}
