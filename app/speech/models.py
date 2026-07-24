from pydantic import BaseModel
from typing import Optional
from enum import Enum


class VisemeType(str, Enum):
    AA = "AA"
    AE = "AE"
    AH = "AH"
    AO = "AO"
    AW = "AW"
    AY = "AY"
    B = "B"
    CH = "CH"
    D = "D"
    DH = "DH"
    EH = "EH"
    ER = "ER"
    EY = "EY"
    F = "F"
    G = "G"
    HH = "HH"
    IH = "IH"
    IY = "IY"
    JH = "JH"
    K = "K"
    L = "L"
    M = "M"
    N = "N"
    NG = "NG"
    OW = "OW"
    OY = "OY"
    P = "P"
    R = "R"
    S = "S"
    SH = "SH"
    SIL = "SIL"
    T = "T"
    TH = "TH"
    UH = "UH"
    UW = "UW"
    V = "V"
    W = "W"
    Y = "Y"
    Z = "Z"
    ZH = "ZH"
    DD = "DD"
    FF = "FF"
    KK = "KK"
    NN = "NN"
    PP = "PP"
    RR = "RR"
    SS = "SS"
    aa = "aa"
    ih = "ih"
    kk = "kk"
    nn = "nn"
    oh = "oh"
    ou = "ou"
    E = "E"
    sil = "sil"


class EmotionType(str, Enum):
    neutral = "neutral"
    happy = "happy"
    thoughtful = "thoughtful"
    concerned = "concerned"
    confident = "confident"
    surprised = "surprised"
    laughing = "laughing"
    considering = "considering"
    excited = "excited"


class GestureHint(str, Enum):
    none_ = "none"
    nod = "nod"
    open_palm = "open_palm"
    emphasis = "emphasis"
    thinking = "thinking"
    listening = "listening"


class VisemeEvent(BaseModel):
    time: float
    value: VisemeType
    intensity: float = 0.8
    duration: float = 0.1


class AudioChunk(BaseModel):
    sequence: int
    data: str
    is_final: bool = False
    sample_rate: int = 24000


class ExpressionEvent(BaseModel):
    time: float
    emotion: EmotionType
    intensity: float = 0.5


class GestureEvent(BaseModel):
    time: float
    gesture: GestureHint
    intensity: float = 0.5


class SpeechTimeline(BaseModel):
    phonemes: list[tuple[str, float, float]]
    visemes: list[VisemeEvent]
    expressions: list[ExpressionEvent] = []
    gestures: list[GestureEvent] = []


class WSMessage(BaseModel):
    session_id: str
    response_id: str
    type: str
    timestamp: float
    sequence: int = 0
    data: Optional[dict] = None
