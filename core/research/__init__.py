"""
J.A.R.V.I.S. Institutional Market Research Hub.
Provides macro surveillance, meme alpha radar streaming, and spot crypto fundamental dossiers.
"""

from .macro_surveillance import (
    CurrencyStrengthMeter,
    CentralBankRateMatrix,
    EconomicNewsBlackoutManager,
    MacroSurveillanceEngine,
    get_macro_surveillance_engine,
)
from .meme_alpha_stream import (
    MemeAlphaStreamer,
    get_meme_alpha_streamer,
)
from .spot_crypto_dossier import (
    SpotCryptoDossierEngine,
    get_spot_crypto_dossier_engine,
)

__all__ = [
    "CurrencyStrengthMeter",
    "CentralBankRateMatrix",
    "EconomicNewsBlackoutManager",
    "MacroSurveillanceEngine",
    "get_macro_surveillance_engine",
    "MemeAlphaStreamer",
    "get_meme_alpha_streamer",
    "SpotCryptoDossierEngine",
    "get_spot_crypto_dossier_engine",
]
