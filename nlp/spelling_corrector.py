"""
Intelligent Phonetic & Fuzzy Spelling Auto-Correction Subsystem for P.H.A.S.S Sphere.
Automatically repairs typos, phonetic homophones, transpositions, and misspellings
before intent classification and directive execution.
"""

from __future__ import annotations
import re
import logging
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("phass.nlp.spelling_corrector")


class IntelligentSpellingCorrector:
    # Explicit phonetic homophones, transpositions, and domain-specific typos
    PHONETIC_AND_COMMON_TYPOS: Dict[str, str] = {
        # Actions & Verbs
        "wright": "write",
        "writte": "write",
        "writ": "write",
        "writting": "writing",
        "cretea": "create",
        "creat": "create",
        "crate": "create",
        "creete": "create",
        "generat": "generate",
        "reserch": "research",
        "reaserch": "research",
        "tryr": "try",
        "mak": "make",
        "maded": "made",
        "maked": "made",
        "ubgrade": "upgrade",
        "upgrde": "upgrade",
        "traine": "train",
        "trainning": "training",
        "lern": "learn",
        "leran": "learn",
        "lerning": "learning",
        "hotcod": "hotcode",
        "hot-code": "hotcode",
        "hot coding": "hotcode",
        "controol": "control",
        "controll": "control",
        "cheking": "checking",
        "diagnos": "diagnose",
        "diagnosise": "diagnose",
        
        # Greetings & Chat terms
        "hai": "hi",
        "heyy": "hey",
        "hiii": "hi",
        "hlo": "hello",
        "helo": "hello",
        "hellow": "hello",
        "frendly": "friendly",
        "chating": "chatting",
        "alkso": "also",
        "namae": "name",
        "intergfaace": "interface",
        "dashbeard": "dashboard",
        "windoiws": "windows",
        "allign": "align",
        "picter": "picture",

        # Wireless & Signal Terms
        "bluthooth": "bluetooth",
        "blutooth": "bluetooth",
        "bluetoth": "bluetooth",
        "sysmtem": "system",
        "systemm": "system",
        "softwaree": "software",
        "softwre": "software",
        "accese": "access",
        "acess": "access",
        "mens": "means",
        "anf": "and",
        "wlan": "wifi",
        "signall": "signal",
        "signels": "signals",
        "spektrum": "spectrum",
        
        # Domains & Tech Terms
        "posative": "positive",
        "postive": "positive",
        "intiger": "integer",
        "integar": "integer",
        "integre": "integer",
        "calculater": "calculator",
        "calculatr": "calculator",
        "remot": "remote",
        "remotee": "remote",
        "sphear": "sphere",
        "orvixx": "phass",
        "jarvic": "jarvis",
        "jarvice": "jarvis",
        "watsapp": "whatsapp",
        "whatsap": "whatsapp",
        "whatsappp": "whatsapp",
        "spotfy": "spotify",
        "spofity": "spotify",
        "youtub": "youtube",
        "youtubbe": "youtube",
        "googl": "google",
        "gogle": "google",
        "gdrive": "google drive",
        "aplication": "application",
        "applicaton": "application",
        "wether": "weather",
        "temprature": "temperature",
        "temperture": "temperature",
        "yeasterday": "yesterday",
        "yesterda": "yesterday",
        "parliment": "parliament",
        "parliamnet": "parliament",
        "sceen": "screen",
        "scrnshot": "screenshot",
        "screenshoot": "screenshot",
        "clipbord": "clipboard",
        "biometrc": "biometric",
        "holgram": "hologram",
        "wirefram": "wireframe",
    }

    # Standard Common English & Domain Vocabulary (words that should NEVER be mutated)
    VALID_WORDS: Set[str] = {
        # Common English stop words & basics
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
        "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between",
        "both", "but", "by", "can", "can't", "cannot", "could", "couldn't", "did", "didn't",
        "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
        "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having",
        "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
        "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in",
        "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most",
        "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
        "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
        "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
        "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
        "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
        "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what",
        "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
        "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
        "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves",

        # Domain terms & actions
        "mode", "mind", "theory", "diagnosis", "diagnostics", "check", "system", "file", "files",
        "notepad", "calculator", "terminal", "explorer", "code", "run", "start", "stop", "scan",
        "cyber", "security", "sweep", "lockdown", "morning", "night", "sentinel", "briefing",
        "clean", "slate", "optimize", "workspace", "developer", "dev", "status", "subsystem",
        "memory", "stream", "consciousness", "episodic", "battery", "temp", "lidar", "voxels",
        "octomap", "drone", "robot", "sphere", "phass", "jarvis", "weather", "forecast",
        "radar", "satellite", "temperature", "humidity", "webcam", "camera", "face",
        "biometric", "emotion", "focus", "presence", "email", "inbox", "calendar", "agenda",
        "messages", "schedule", "reminder", "light", "lights", "climate", "plug", "thermostat",
        "smart", "home", "hologram", "wireframe", "perspective", "positive", "integer",
        "quicksort", "fibonacci", "prime", "number", "numbers", "find", "finder", "search",
        "solve", "solver", "take", "screenshot", "read", "clipboard", "type", "press",
        "shortcut", "open", "close", "save", "load", "train", "learn", "hotcode", "omni",
        "architecture", "quantum", "simulation", "stock", "market", "trends", "lead",
        "signal", "signals", "bluetooth", "wifi", "boost", "volume", "speed", "utility",
        "utilities", "adapter", "adapters", "accelerate", "near", "device", "devices",
        "manager", "network", "firewall", "services", "connections",
        "miles", "km", "meters", "feet", "convert", "solve", "algebra",
        "software", "model", "models", "modelfile", "gguf", "safetensors", "onnx", "distill", "distillation", "export", "weights",
        "brain", "brains", "phi", "phi4", "secondary", "dual"
    }

    def _damerau_levenshtein_distance(self, s1: str, s2: str) -> int:
        """Computes edit distance including adjacent transpositions."""
        d: Dict[Tuple[int, int], int] = {}
        len1, len2 = len(s1), len(s2)
        for i in range(-1, len1 + 1):
            d[(i, -1)] = i + 1
        for j in range(-1, len2 + 1):
            d[(-1, j)] = j + 1

        for i in range(len1):
            for j in range(len2):
                cost = 0 if s1[i] == s2[j] else 1
                d[(i, j)] = min(
                    d[(i - 1, j)] + 1,        # deletion
                    d[(i, j - 1)] + 1,        # insertion
                    d[(i - 1, j - 1)] + cost  # substitution
                )
                if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                    d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost) # transposition

        return d[(len1 - 1, len2 - 1)]

    def correct_word(self, word: str) -> str:
        """Corrects a single word using phonetic dictionary and fuzzy edit distance."""
        w_clean = word.strip().lower()
        if not w_clean or len(w_clean) <= 1:
            return word

        # 1. Direct phonetic/homophone match
        if w_clean in self.PHONETIC_AND_COMMON_TYPOS:
            replacement = self.PHONETIC_AND_COMMON_TYPOS[w_clean]
            return replacement if word.islower() else (replacement.upper() if word.isupper() else replacement.capitalize())

        # 2. If already valid known English/domain word, never mutate
        if w_clean in self.VALID_WORDS:
            return word

        # 3. Fuzzy edit distance against domain vocabulary (only for words >= 5 chars, distance 1)
        if len(w_clean) < 5:
            return word

        best_candidate = word
        min_dist = 2

        for vocab_word in self.VALID_WORDS:
            if abs(len(w_clean) - len(vocab_word)) > 1:
                continue
            dist = self._damerau_levenshtein_distance(w_clean, vocab_word)
            if dist < min_dist:
                min_dist = dist
                best_candidate = vocab_word

        if min_dist == 1:
            return best_candidate if word.islower() else (best_candidate.upper() if word.isupper() else best_candidate.capitalize())

        return word

    def correct_sentence(self, sentence: str) -> Tuple[str, bool]:
        """
        Scans and auto-corrects full user sentences, preserving punctuation and casing.
        Returns (corrected_sentence, was_modified).
        """
        if not sentence or not sentence.strip():
            return sentence, False

        # Tokenize words while preserving spaces/punctuation
        tokens = re.split(r"(\s+|[^\w\s])", sentence)
        corrected_tokens = []
        was_modified = False

        for tok in tokens:
            if re.match(r"^\w+$", tok):
                c_tok = self.correct_word(tok)
                if c_tok != tok:
                    was_modified = True
                corrected_tokens.append(c_tok)
            else:
                corrected_tokens.append(tok)

        corrected_sentence = "".join(corrected_tokens)
        if was_modified:
            logger.info(f"Auto-corrected spelling: '{sentence}' -> '{corrected_sentence}'")

        return corrected_sentence, was_modified


spelling_corrector = IntelligentSpellingCorrector()
