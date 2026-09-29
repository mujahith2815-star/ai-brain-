"""
Multi-Language Support Module for P.H.A.S.S Sphere & Llama Assistant.
Provides internationalization and multilingual processing:
Language identification and detection,
Bidirectional translation service across major global languages,
Localized voice and text command parser (Spanish, French, German, Chinese, Japanese, Hindi),
and UI interface string auto-localization.
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.language")


# ---------------------------------------------------------------------------
# 1. Language Detector
# ---------------------------------------------------------------------------
def language_detector(text: str) -> Dict[str, Any]:
    """
    Detects the primary language of the input text using script and vocabulary analysis.
    """
    if not text.strip():
        return {"status": "FAILED", "error": "Empty text provided."}

    # Script heuristics
    if re.search(r'[\u4e00-\u9fff]', text):
        return {"status": "SUCCESS", "detected_language": "zh", "language_name": "Chinese", "confidence": 0.98}
    if re.search(r'[\u3040-\u30ff]', text):
        return {"status": "SUCCESS", "detected_language": "ja", "language_name": "Japanese", "confidence": 0.98}
    if re.search(r'[\u0900-\u097f]', text):
        return {"status": "SUCCESS", "detected_language": "hi", "language_name": "Hindi", "confidence": 0.98}
    if re.search(r'[\u0400-\u04ff]', text):
        return {"status": "SUCCESS", "detected_language": "ru", "language_name": "Russian", "confidence": 0.95}
    if re.search(r'[\u0600-\u06ff]', text):
        return {"status": "SUCCESS", "detected_language": "ar", "language_name": "Arabic", "confidence": 0.95}

    # Latin character vocabulary matching
    words = [w.lower() for w in re.findall(r'\b[a-zA-Záéíóúüñßçàèìòùâêîôûëïö]+\b', text)]
    
    es_markers = {"el", "la", "los", "las", "un", "una", "de", "que", "y", "en", "por", "para", "hola", "archivo", "sistema"}
    fr_markers = {"le", "la", "les", "un", "une", "des", "et", "en", "pour", "bonjour", "fichier", "système"}
    de_markers = {"der", "die", "das", "ein", "eine", "und", "in", "für", "hallo", "datei", "system"}

    es_score = sum(1 for w in words if w in es_markers)
    fr_score = sum(1 for w in words if w in fr_markers)
    de_score = sum(1 for w in words if w in de_markers)

    if es_score > fr_score and es_score > de_score and es_score > 0:
        return {"status": "SUCCESS", "detected_language": "es", "language_name": "Spanish", "confidence": 0.90}
    elif fr_score > de_score and fr_score > 0:
        return {"status": "SUCCESS", "detected_language": "fr", "language_name": "French", "confidence": 0.90}
    elif de_score > 0:
        return {"status": "SUCCESS", "detected_language": "de", "language_name": "German", "confidence": 0.90}

    return {"status": "SUCCESS", "detected_language": "en", "language_name": "English", "confidence": 0.85}


# ---------------------------------------------------------------------------
# 2. Translation Service
# ---------------------------------------------------------------------------
def translation_service(
    text: str,
    target_lang: str = "es",
    source_lang: str = "auto",
) -> Dict[str, Any]:
    """
    Translates text to target language using comprehensive localized dictionary lookup.
    """
    from .ai_ml_tools import language_translator
    return language_translator(text=text, target_lang=target_lang, source_lang=source_lang)


# ---------------------------------------------------------------------------
# 3. Localized Commands Parser
# ---------------------------------------------------------------------------
def localized_commands(command_text: str) -> Dict[str, Any]:
    """
    Parses commands spoken or typed in non-English languages and maps them
    to standard internal assistant tool directives.
    """
    cmd_low = command_text.strip().lower()

    mappings = [
        # Spanish
        (["apagar sistema", "apagar equipo", "apaga la computadora"], "system_control shutdown"),
        (["reiniciar sistema", "reiniciar equipo", "reinicia la computadora"], "system_control restart"),
        (["bloquear pantalla", "bloquear equipo"], "system_control lock_screen"),
        (["tomar captura", "captura de pantalla", "foto de pantalla"], "screenshot_capture"),
        (["limpiar disco", "limpiar temporales", "borrar archivos temporales"], "disk_cleaner"),
        (["buscar archivos duplicados", "encontrar duplicados"], "find_duplicate_files"),
        (["organizar archivos", "organiza la carpeta"], "smart_file_organizer"),
        (["reproducir musica", "pon musica"], "music_player play"),
        (["cuenta un chiste", "dime un chiste"], "joke_generator"),

        # French
        (["arreter le systeme", "eteindre l'ordinateur"], "system_control shutdown"),
        (["redemarrer", "redemarrer le systeme"], "system_control restart"),
        (["verrouiller l'ecran", "bloquer l'ordinateur"], "system_control lock_screen"),
        (["capture d'ecran", "prendre une capture"], "screenshot_capture"),
        (["nettoyer le disque"], "disk_cleaner"),

        # German
        (["herunterfahren", "system ausschalten"], "system_control shutdown"),
        (["neustarten", "system neustarten"], "system_control restart"),
        (["bildschirm sperren"], "system_control lock_screen"),
        (["screenshot erstellen", "bildschirmfoto"], "screenshot_capture"),

        # Chinese
        (["关机", "关闭系统"], "system_control shutdown"),
        (["重启", "重启系统"], "system_control restart"),
        (["锁定屏幕", "锁屏"], "system_control lock_screen"),
        (["截屏", "截图"], "screenshot_capture"),

        # Hindi
        (["सिस्टम बंद करो", "कंप्यूटर बंद करो"], "system_control shutdown"),
        (["रीस्टार्ट करो", "सिस्टम रीस्टार्ट करो"], "system_control restart"),
        (["स्क्रीन लॉक करो"], "system_control lock_screen"),
        (["स्क्रीनशॉट लो"], "screenshot_capture"),
    ]

    for phrases, internal_cmd in mappings:
        for p in phrases:
            if p in cmd_low:
                return {
                    "status": "SUCCESS",
                    "original_command": command_text,
                    "matched_phrase": p,
                    "normalized_directive": internal_cmd,
                    "is_localized": True,
                }

    return {
        "status": "SUCCESS",
        "original_command": command_text,
        "normalized_directive": command_text,
        "is_localized": False,
    }


# ---------------------------------------------------------------------------
# 4. Interface Translation
# ---------------------------------------------------------------------------
def interface_translation(
    ui_strings: Optional[Dict[str, str]] = None,
    target_lang: str = "es",
) -> Dict[str, Any]:
    """
    Translates standard UI labels, buttons, and prompts into target language.
    """
    default_ui = {
        "welcome": "Welcome to P.H.A.S.S Sphere",
        "ready": "Ready for input",
        "exit": "Exit application",
        "settings": "System Settings",
        "tools": "Available Tools",
        "status": "Operational Status",
    }
    targets = ui_strings or default_ui
    t_low = target_lang.lower()

    es_ui = {
        "welcome": "Bienvenido a P.H.A.S.S Sphere",
        "ready": "Listo para recibir instrucciones",
        "exit": "Salir de la aplicación",
        "settings": "Configuración del Sistema",
        "tools": "Herramientas Disponibles",
        "status": "Estado Operativo",
    }
    fr_ui = {
        "welcome": "Bienvenue sur P.H.A.S.S Sphere",
        "ready": "Prêt pour les instructions",
        "exit": "Quitter l'application",
        "settings": "Paramètres du système",
        "tools": "Outils disponibles",
        "status": "Statut opérationnel",
    }
    de_ui = {
        "welcome": "Willkommen bei P.H.A.S.S Sphere",
        "ready": "Bereit für Eingaben",
        "exit": "Anwendung beenden",
        "settings": "Systemeinstellungen",
        "tools": "Verfügbare Werkzeuge",
        "status": "Betriebsstatus",
    }

    localized = es_ui if t_low == "es" else (fr_ui if t_low == "fr" else (de_ui if t_low == "de" else targets))

    return {
        "status": "SUCCESS",
        "target_language": target_lang,
        "localized_ui": localized,
    }
