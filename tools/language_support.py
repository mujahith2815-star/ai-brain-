"""
Multi-Language Support Module for P.H.A.S.S Sphere & Llama Assistant.
Provides language detection, dictionary & heuristic translation, localized system
responses, and cross-lingual command mapping.
"""

from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.language_support")

_LOCALIZED_MESSAGES = {
    "welcome": {
        "en": "Welcome to P.H.A.S.S Sphere. All systems are operational.",
        "es": "Bienvenido a P.H.A.S.S Sphere. Todos los sistemas están operativos.",
        "fr": "Bienvenue sur P.H.A.S.S Sphere. Tous les systèmes sont opérationnels.",
        "de": "Willkommen bei P.H.A.S.S Sphere. Alle Systeme sind betriebsbereit.",
        "hi": "P.H.A.S.S Sphere में आपका स्वागत है। सभी प्रणालियाँ क्रियाशील हैं।",
        "ja": "P.H.A.S.S Sphereへようこそ。すべてのシステムが稼働しています。",
    },
    "ready": {
        "en": "Standing by for your directive.",
        "es": "A la espera de su directiva.",
        "fr": "En attente de vos instructions.",
        "de": "Bereit für Ihre Anweisungen.",
        "hi": "आपके निर्देश की प्रतीक्षा में।",
        "ja": "指示をお待ちしています。",
    },
    "error": {
        "en": "An operation error occurred. Please verify your parameters.",
        "es": "Se produjo un error de operación. Por favor verifique sus parámetros.",
        "fr": "Une erreur de fonctionnement est survenue. Veuillez vérifier vos paramètres.",
        "de": "Ein Betriebsfehler ist aufgetreten. Bitte überprüfen Sie Ihre Parameter.",
        "hi": "एक संचालन त्रुटि हुई। कृपया अपने मापदंडों की जांच करें।",
        "ja": "操作エラーが発生しました。パラメータを確認してください。",
    },
}

_COMMON_COMMAND_MAP = {
    "limpiar disco": "clean disk",
    "analizar disco": "analyze disk space",
    "apagar sistema": "shutdown system",
    "bloquear pantalla": "lock screen",
    "nettoyer disque": "clean disk",
    "eteindre": "shutdown system",
    "bildschirm sperren": "lock screen",
    "platte bereinigen": "clean disk",
}


def detect_language(text: str) -> Dict[str, Any]:
    """Detects the primary natural language of input text."""
    t = text.lower()

    # Heuristics
    if re.search(r"[\u0900-\u097F]", text):
        return {"status": "SUCCESS", "language": "hi", "language_name": "Hindi", "confidence": 0.95}
    if re.search(r"[\u3040-\u30FF\u4E00-\u9FAF]", text):
        return {"status": "SUCCESS", "language": "ja", "language_name": "Japanese", "confidence": 0.95}
    if re.search(r"[\u0600-\u06FF]", text):
        return {"status": "SUCCESS", "language": "ar", "language_name": "Arabic", "confidence": 0.95}

    es_words = ["hola", "el", "la", "que", "gracias", "por", "favor", "disco", "limpiar", "sistema"]
    fr_words = ["bonjour", "le", "la", "les", "merci", "s'il", "vous", "plait", "disque"]
    de_words = ["hallo", "der", "die", "das", "bitte", "danke", "nicht", "system", "bereinigen"]

    words = set(re.findall(r"\b\w+\b", t))
    if len(words & set(es_words)) >= 2:
        return {"status": "SUCCESS", "language": "es", "language_name": "Spanish", "confidence": 0.90}
    if len(words & set(fr_words)) >= 2:
        return {"status": "SUCCESS", "language": "fr", "language_name": "French", "confidence": 0.90}
    if len(words & set(de_words)) >= 2:
        return {"status": "SUCCESS", "language": "de", "language_name": "German", "confidence": 0.90}

    return {"status": "SUCCESS", "language": "en", "language_name": "English", "confidence": 0.85}


def translate_text(
    text: str,
    target_lang: str,
    source_lang: Optional[str] = None,
) -> Dict[str, Any]:
    """Translates text to target language."""
    detected = detect_language(text)
    src = source_lang or detected["language"]
    tgt = target_lang.lower().strip()

    # Dictionary translations for basic common phrases
    dict_map = {
        ("hello", "es"): "Hola",
        ("hello", "fr"): "Bonjour",
        ("hello", "de"): "Hallo",
        ("clean disk", "es"): "Limpiar disco",
        ("clean disk", "fr"): "Nettoyer le disque",
        ("clean disk", "de"): "Festplatte bereinigen",
    }

    translated = dict_map.get((text.lower().strip(), tgt))
    if not translated:
        translated = f"[{tgt.upper()}] {text}"

    return {
        "status": "SUCCESS",
        "original_text": text,
        "translated_text": translated,
        "source_lang": src,
        "target_lang": tgt,
    }


def get_localized_response(
    message_key: str,
    lang: str = "en",
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Retrieves a standardized, localized message string for the target language."""
    key = message_key.lower().strip()
    lang_code = lang.lower().strip()
    msg_dict = _LOCALIZED_MESSAGES.get(key, {})
    template = msg_dict.get(lang_code, msg_dict.get("en", f"Directive resolved: {key}"))

    if params:
        for k, v in params.items():
            template = template.replace(f"{{{k}}}", str(v))

    return {
        "status": "SUCCESS",
        "message_key": key,
        "language": lang_code,
        "localized_text": template,
    }


def map_multilingual_command(
    query: str,
    target_language: str = "en",
) -> Dict[str, Any]:
    """Normalizes a non-English user command into standardized English tool directive."""
    q_clean = query.lower().strip()
    mapped = _COMMON_COMMAND_MAP.get(q_clean)
    if mapped:
        return {
            "status": "SUCCESS",
            "original_query": query,
            "mapped_command": mapped,
            "matched": True,
        }

    return {
        "status": "SUCCESS",
        "original_query": query,
        "mapped_command": query,
        "matched": False,
    }
