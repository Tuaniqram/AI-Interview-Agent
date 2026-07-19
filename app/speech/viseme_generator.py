import re
from typing import Optional

PHONEME_TO_VISEME: dict[str, list[tuple[str, float]]] = {
    "AA": [("aa", 1.0), ("jawOpen", 0.8)],
    "AE": [("aa", 0.9), ("jawOpen", 0.7)],
    "AH": [("aa", 0.8), ("jawOpen", 0.6)],
    "AO": [("oh", 0.8), ("jawOpen", 0.5), ("mouthFunnel", 0.4)],
    "AW": [("aa", 0.7), ("oh", 0.5)],
    "AY": [("aa", 0.8), ("ih", 0.4)],
    "B": [("PP", 0.9), ("mouthClose", 0.7)],
    "CH": [("CH", 1.0)],
    "D": [("DD", 1.0), ("jawOpen", 0.3)],
    "DH": [("TH", 1.0)],
    "EH": [("E", 1.0), ("jawOpen", 0.4)],
    "ER": [("RR", 0.8), ("jawOpen", 0.3)],
    "EY": [("E", 0.9), ("ih", 0.3)],
    "F": [("FF", 1.0)],
    "G": [("kk", 0.8), ("jawOpen", 0.3)],
    "HH": [("aa", 0.3)],
    "IH": [("ih", 1.0), ("jawOpen", 0.2)],
    "IY": [("ih", 0.9), ("E", 0.3)],
    "JH": [("CH", 0.8), ("DD", 0.3)],
    "K": [("kk", 1.0), ("jawOpen", 0.3)],
    "L": [("nn", 0.6), ("jawOpen", 0.2)],
    "M": [("nn", 0.8), ("mouthClose", 0.3)],
    "N": [("nn", 1.0)],
    "NG": [("kk", 0.7), ("jawOpen", 0.2)],
    "OW": [("oh", 1.0), ("mouthFunnel", 0.6)],
    "OY": [("oh", 0.7), ("ih", 0.4)],
    "P": [("PP", 1.0), ("mouthClose", 0.8)],
    "R": [("RR", 1.0), ("mouthPucker", 0.2)],
    "S": [("SS", 1.0)],
    "SH": [("CH", 0.8), ("SH", 0.3)],
    "SIL": [("sil", 1.0)],
    "T": [("DD", 0.9), ("jawOpen", 0.2)],
    "TH": [("TH", 1.0)],
    "UH": [("oh", 0.6), ("mouthFunnel", 0.4)],
    "UW": [("oh", 0.8), ("mouthFunnel", 0.4)],
    "V": [("FF", 0.9)],
    "W": [("oh", 0.7), ("mouthFunnel", 0.4)],
    "Y": [("ih", 0.5), ("E", 0.3)],
    "Z": [("SS", 0.8)],
    "ZH": [("CH", 0.7), ("SH", 0.3)],
}

CHAR_TO_PHONEME: dict[str, str] = {
    "a": "AA", "b": "B", "c": "K", "d": "D",
    "e": "EH", "f": "F", "g": "G", "h": "HH",
    "i": "IH", "j": "JH", "k": "K", "l": "L",
    "m": "M", "n": "N", "o": "OW", "p": "P",
    "q": "K", "r": "R", "s": "S", "t": "T",
    "u": "UH", "v": "V", "w": "W", "x": "K",
    "y": "Y", "z": "Z",
}


def text_to_phonemes(text: str) -> list[tuple[str, float, float]]:
    words = re.findall(r"\S+|\s+", text.lower())
    phonemes: list[tuple[str, float, float]] = []
    char_index = 0

    for word in words:
        if word.isspace():
            char_index += len(word)
            continue

        word_phonemes: list[str] = []
        for ch in word:
            if ch.isalpha():
                p = CHAR_TO_PHONEME.get(ch, "SIL")
                word_phonemes.append(p)

        if not word_phonemes:
            char_index += len(word)
            continue

        word_duration = len(word) * 0.06
        phoneme_duration = word_duration / len(word_phonemes)
        current_time = char_index * 0.06

        for p in word_phonemes:
            phonemes.append((p, current_time, phoneme_duration))
            current_time += phoneme_duration

        char_index += len(word)

    return phonemes


def phonemes_to_visemes(
    phonemes: list[tuple[str, float, float]],
) -> list[dict]:
    visemes: list[dict] = []

    for phoneme, start_time, duration in phonemes:
        viseme_key = phoneme
        if phoneme not in PHONEME_TO_VISEME:
            viseme_key = "SIL"

        visemes.append({
            "time": round(start_time, 3),
            "value": viseme_key,
            "intensity": 0.8,
            "duration": round(duration, 3),
        })

    if not visemes:
        return []

    visemes.append({
        "time": round(visemes[-1]["time"] + visemes[-1]["duration"], 3),
        "value": "SIL",
        "intensity": 0,
        "duration": 0.1,
    })

    return visemes


def generate_viseme_timeline(
    text: str,
    timestamps: Optional[list[dict]] = None,
) -> list[dict]:
    if timestamps:
        return timestamps_to_visemes(timestamps)
    phonemes = text_to_phonemes(text)
    return phonemes_to_visemes(phonemes)


def timestamps_to_visemes(
    timestamps: list[dict],
) -> list[dict]:
    visemes: list[dict] = []
    for i, ts in enumerate(timestamps):
        char = ts.get("char", " ")
        start = ts.get("start", 0)
        end = ts.get("end", start + 0.1)
        duration = end - start

        phoneme = CHAR_TO_PHONEME.get(char.lower(), "SIL")
        visemes.append({
            "time": round(start, 3),
            "value": phoneme,
            "intensity": 0.8,
            "duration": round(duration, 3),
        })

    if visemes:
        last = visemes[-1]
        visemes.append({
            "time": round(last["time"] + last["duration"], 3),
            "value": "SIL",
            "intensity": 0,
            "duration": 0.1,
        })

    return visemes
