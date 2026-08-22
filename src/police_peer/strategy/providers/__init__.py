"""Provider package: optional language-model hint providers (T027, P2).

Re-exports the provider-neutral resolver so the injection seam can stay
provider-agnostic. ``template`` remains the shipped default and needs no
network or model dependency (STRAT-008, NG-003).
"""

from police_peer.strategy.providers.language_model import (
    OpenAIProvider,
    resolve_text_provider,
)

__all__ = [
    "OpenAIProvider",
    "resolve_text_provider",
]
