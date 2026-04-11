---
type: codebase-class
file: eos_ai/media_processor.py
line: 85
generated: 2026-04-11
---

# MediaProcessor

**File:** [[eos_ai-media_processor-py]] | **Line:** 85

*No docstring.*

## Methods

- [[eos_ai-media_processor-py-MediaProcessor-__init__]]`()` — 
- [[eos_ai-media_processor-py-MediaProcessor-detect_modality]]`(file_path) → str` — 
- [[eos_ai-media_processor-py-MediaProcessor-process]]`(file_path, modality, user_prompt, business_context) → str` — 
- [[eos_ai-media_processor-py-MediaProcessor-_process_image]]`(path, prompt) → str` — 
- [[eos_ai-media_processor-py-MediaProcessor-_process_video]]`(path, prompt) → str` — 
- [[eos_ai-media_processor-py-MediaProcessor-_process_document]]`(path, prompt) → str` — 
- [[eos_ai-media_processor-py-MediaProcessor-_local_transcribe]]`(audio_path) → str` — 
- [[eos_ai-media_processor-py-MediaProcessor-synthesize_speech]]`(text, output_path) → str | None` — Convert text to speech locally.
- [[eos_ai-media_processor-py-MediaProcessor-generate_embedding]]`(text) → list[float]` — Google Text Embedding 004 — 768 dimensions.
