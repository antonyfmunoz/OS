"""Symbolic capability classes for model routing.

Types are owned by substrate.contracts.routing_contracts — re-exported here
for backwards compatibility within the adapters layer.
"""

from substrate.contracts.routing_contracts import (  # noqa: F401
    CapabilityClass,
    CapabilityEntry,
    PrivacyLevel,
)


CAPABILITY_REGISTRY: dict[CapabilityClass, CapabilityEntry] = {
    CapabilityClass.BEST_CLOUD_REASONING: CapabilityEntry(
        capability_class=CapabilityClass.BEST_CLOUD_REASONING,
        preferred_provider_symbol="cc_sdk_opus",
        fallback_provider_symbols=["anthropic_opus", "gemini_flash"],
        privacy_level=PrivacyLevel.INTERNAL,
        max_cost_hint="$0.15/1k tokens",
        local_first=False,
        notes="CEO/strategic decisions. Maps to agent_type='ceo', force_opus=True in model_router.",
    ),
    CapabilityClass.FAST_CLOUD_REASONING: CapabilityEntry(
        capability_class=CapabilityClass.FAST_CLOUD_REASONING,
        preferred_provider_symbol="gemini_flash",
        fallback_provider_symbols=["groq_llama", "anthropic_haiku"],
        privacy_level=PrivacyLevel.INTERNAL,
        max_cost_hint="$0.01/1k tokens",
        local_first=False,
        notes="Bulk worker tasks. Maps to agent_type='worker' in model_router.",
    ),
    CapabilityClass.CHEAP_CLOUD_REASONING: CapabilityEntry(
        capability_class=CapabilityClass.CHEAP_CLOUD_REASONING,
        preferred_provider_symbol="groq_llama",
        fallback_provider_symbols=["gemini_flash", "ollama_local"],
        privacy_level=PrivacyLevel.INTERNAL,
        max_cost_hint="$0.001/1k tokens",
        local_first=False,
        notes="Classification, tagging, simple extraction. Cheapest viable option.",
    ),
    CapabilityClass.LOCAL_FAST_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_FAST_MODEL,
        preferred_provider_symbol="ollama_gemma3_4b",
        fallback_provider_symbols=["groq_llama"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Private data that must not leave the VPS. Ollama gemma3:4b.",
    ),
    CapabilityClass.LOCAL_CODE_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_CODE_MODEL,
        preferred_provider_symbol="ollama_qwen_coder",
        fallback_provider_symbols=["ollama_gemma3_4b", "gemini_flash"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Code generation/review on private repos. Qwen2.5-Coder when available.",
    ),
    CapabilityClass.LOCAL_EMBEDDING_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_EMBEDDING_MODEL,
        preferred_provider_symbol="ollama_nomic_embed",
        fallback_provider_symbols=["openai_embed_small"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Vector embeddings for memory/search. nomic-embed-text via Ollama.",
    ),
    CapabilityClass.LOCAL_VISION_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_VISION_MODEL,
        preferred_provider_symbol="ollama_llava",
        fallback_provider_symbols=["cloud_vision"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Image understanding on private content. LLaVA via Ollama.",
    ),
    CapabilityClass.LOCAL_TRANSCRIPTION_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_TRANSCRIPTION_MODEL,
        preferred_provider_symbol="whisper_local",
        fallback_provider_symbols=["groq_whisper"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Speech-to-text. Whisper via local binary or Ollama.",
    ),
    CapabilityClass.CLOUD_VISION_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.CLOUD_VISION_MODEL,
        preferred_provider_symbol="gemini_flash_vision",
        fallback_provider_symbols=["anthropic_sonnet"],
        privacy_level=PrivacyLevel.INTERNAL,
        max_cost_hint="$0.02/image",
        local_first=False,
        notes="Non-private image analysis. Gemini Flash has good vision at low cost.",
    ),
    CapabilityClass.LOCAL_TTS_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_TTS_MODEL,
        preferred_provider_symbol="piper_tts",
        fallback_provider_symbols=["cloud_tts"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Text-to-speech. Piper TTS for local, fast synthesis.",
    ),
    CapabilityClass.CLOUD_TTS_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.CLOUD_TTS_MODEL,
        preferred_provider_symbol="elevenlabs",
        fallback_provider_symbols=["google_tts", "piper_tts"],
        privacy_level=PrivacyLevel.INTERNAL,
        max_cost_hint="$0.30/1k chars",
        local_first=False,
        notes="High-quality voice synthesis for content. ElevenLabs primary.",
    ),
    CapabilityClass.LOCAL_STT_MODEL: CapabilityEntry(
        capability_class=CapabilityClass.LOCAL_STT_MODEL,
        preferred_provider_symbol="whisper_local",
        fallback_provider_symbols=["groq_whisper", "google_stt"],
        privacy_level=PrivacyLevel.RESTRICTED,
        max_cost_hint="$0 (local)",
        local_first=True,
        notes="Live speech-to-text for voice interface. Same as transcription but real-time.",
    ),
}
