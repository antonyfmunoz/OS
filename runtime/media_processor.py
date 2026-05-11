"""
MediaProcessor — unified multimodal file handler.

Routes files to the right backend:
  - voice/audio  → faster-whisper (local, always)
  - image        → Gemini 2.0 Flash (requires GEMINI_API_KEY)
  - video        → Gemini 2.0 Flash (requires GEMINI_API_KEY)
  - document     → Gemini 2.0 Flash (requires GEMINI_API_KEY)

Embeddings: Google Text Embedding 004 (768-dim) when key available.
"""

from pathlib import Path
from dotenv import load_dotenv as _load_dotenv
_ROOT = Path(__file__).parent.parent
_load_dotenv(_ROOT / 'services' / '.env')
_load_dotenv(_ROOT / 'runtime' / '.env', override=True)

try:
    import google.genai as genai
    from google.genai import types as genai_types
    _GENAI_NEW = True
except ImportError:
    import google.generativeai as genai  # type: ignore[no-redef]
    genai_types = None
    _GENAI_NEW = False

import os, tempfile, subprocess, base64

SUPPORTED = {
    'video':    ['.mp4', '.mov', '.avi', '.mkv',
                 '.webm', '.3gp', '.flv'],
    'audio':    ['.mp3', '.wav', '.ogg', '.m4a',
                 '.aac', '.flac', '.opus'],
    'document': ['.pdf', '.txt', '.md', '.docx',
                 '.csv', '.html', '.rtf'],
    'image':    ['.jpg', '.jpeg', '.png', '.gif',
                 '.webp', '.bmp', '.tiff'],
}

MIME_MAP = {
    '.pdf':  'application/pdf',
    '.txt':  'text/plain',
    '.md':   'text/plain',
    '.csv':  'text/csv',
    '.html': 'text/html',
    '.mp4':  'video/mp4',
    '.mov':  'video/quicktime',
    '.mp3':  'audio/mpeg',
    '.wav':  'audio/wav',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png':  'image/png',
    '.webp': 'image/webp',
}

DEFAULT_PROMPTS = {
    'video': (
        'Watch this video carefully. Identify: '
        '(1) what is happening, '
        '(2) any competitor content or tactics, '
        '(3) ICP signals or language patterns, '
        '(4) actionable insights for the business. '
        'Be specific.'
    ),
    'image': (
        'Analyze this image. Identify anything '
        'relevant to the businesses — competitor '
        'content, market signals, design patterns, '
        'performance data, or actionable insights.'
    ),
    'document': (
        'Read this document completely. Provide: '
        '1) concise summary, '
        '2) key facts and data points, '
        '3) actionable insights relevant to the '
        'businesses, '
        '4) any risks or opportunities.'
    ),
    'audio': 'Transcribe this audio accurately.',
    'voice': 'Transcribe this voice message.',
}


class MediaProcessor:

    def __init__(self):
        key = os.getenv('GEMINI_API_KEY')
        if key:
            if _GENAI_NEW:
                self._client = genai.Client(api_key=key)
                self.model   = 'gemini-2.0-flash'
            else:
                genai.configure(api_key=key)
                self._client = None
                self.model   = genai.GenerativeModel('gemini-2.0-flash')
            self.available = True
        else:
            self.available = False
            self._client   = None
            self.model     = None

    def detect_modality(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        for modality, exts in SUPPORTED.items():
            if ext in exts:
                return modality
        return 'unknown'

    def process(
        self,
        file_path: str,
        modality: str | None = None,
        user_prompt: str = '',
        business_context: str = '',
    ) -> str:

        if not modality:
            modality = self.detect_modality(file_path)

        if modality == 'unknown':
            return f'Unsupported file type: {Path(file_path).suffix}'

        # voice/audio: always use local Whisper even if Gemini available
        if modality in ('voice', 'audio'):
            transcript = self._local_transcribe(file_path)
            if user_prompt and 'transcri' not in user_prompt.lower():
                # user wants analysis not just transcript
                full = f'Transcript: {transcript}\n\n{user_prompt}'
                from runtime.model_router import call_with_fallback
                _routing = call_with_fallback(prompt=full, task_type="fast_response")
                _analysis = _routing.output if _routing else ""
                return (
                    f'Transcript: "{transcript}"'
                    f'\n\nAnalysis: {_analysis}'
                )
            return transcript

        if not self.available:
            return (
                'GEMINI_API_KEY not set. '
                'Add to /opt/OS/runtime/.env to enable '
                'image, video, and document processing.'
            )

        prompt = user_prompt or DEFAULT_PROMPTS.get(
            modality, 'Analyze this content.'
        )
        if business_context:
            prompt = (
                f'Business context: {business_context[:300]}\n\n{prompt}'
            )

        if modality == 'image':
            return self._process_image(file_path, prompt)
        elif modality == 'video':
            return self._process_video(file_path, prompt)
        elif modality == 'document':
            return self._process_document(file_path, prompt)

        return 'Could not process file'

    def _process_image(self, path: str, prompt: str) -> str:
        import PIL.Image
        img = PIL.Image.open(path)
        if _GENAI_NEW:
            resp = self._client.models.generate_content(
                model=self.model, contents=[img, prompt]
            )
        else:
            resp = self.model.generate_content([img, prompt])
        return resp.text

    def _process_video(self, path: str, prompt: str) -> str:
        import time
        mime = MIME_MAP.get(Path(path).suffix.lower(), 'video/mp4')
        size = os.path.getsize(path)
        if size > 20 * 1024 * 1024:
            # large file: use Files API
            if _GENAI_NEW:
                video_file = self._client.files.upload(
                    path=path,
                    config={'mime_type': mime},
                )
                while video_file.state.name == 'PROCESSING':
                    time.sleep(3)
                    video_file = self._client.files.get(name=video_file.name)
                resp = self._client.models.generate_content(
                    model=self.model, contents=[video_file, prompt]
                )
            else:
                video_file = genai.upload_file(path=path, mime_type=mime)
                while video_file.state.name == 'PROCESSING':
                    time.sleep(3)
                    video_file = genai.get_file(video_file.name)
                resp = self.model.generate_content([video_file, prompt])
        else:
            # small file: inline bytes
            with open(path, 'rb') as f:
                data = f.read()
            inline = {
                'inline_data': {
                    'mime_type': mime,
                    'data': base64.b64encode(data).decode(),
                }
            }
            if _GENAI_NEW:
                resp = self._client.models.generate_content(
                    model=self.model, contents=[inline, prompt]
                )
            else:
                resp = self.model.generate_content([inline, prompt])
        return resp.text

    def _process_document(self, path: str, prompt: str) -> str:
        import time
        mime = MIME_MAP.get(Path(path).suffix.lower(), 'application/pdf')
        if _GENAI_NEW:
            doc_file = self._client.files.upload(
                path=path,
                config={'mime_type': mime},
            )
            while doc_file.state.name == 'PROCESSING':
                time.sleep(2)
                doc_file = self._client.files.get(name=doc_file.name)
            resp = self._client.models.generate_content(
                model=self.model, contents=[doc_file, prompt]
            )
        else:
            doc_file = genai.upload_file(path=path, mime_type=mime)
            while doc_file.state.name == 'PROCESSING':
                time.sleep(2)
                doc_file = genai.get_file(doc_file.name)
            resp = self.model.generate_content([doc_file, prompt])
        return resp.text

    def _local_transcribe(self, audio_path: str) -> str:
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel('small', device='cpu', compute_type='int8')
            segments, _ = model.transcribe(audio_path)
            return ' '.join(s.text for s in segments).strip()
        except ImportError:
            pass
        try:
            import whisper
            m = whisper.load_model('small')
            return m.transcribe(audio_path)['text'].strip()
        except ImportError:
            return (
                '[install faster-whisper: '
                'pip install faster-whisper --break-system-packages]'
            )

    def synthesize_speech(
        self,
        text: str,
        output_path: str | None = None,
    ) -> str | None:
        """
        Convert text to speech locally.
        Cleans markdown before synthesis.
        Returns path to audio file or None on failure.
        """
        import re

        # clean markdown
        clean = text
        clean = re.sub(r'\*+', '', clean)
        clean = re.sub(r'#+\s*', '', clean)
        clean = re.sub(r'`+[^`]*`+', '', clean)
        clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)
        clean = re.sub(r'[-•]\s+', '', clean)
        clean = re.sub(r'\n+', ' ', clean)
        clean = clean.strip()

        # truncate to reasonable voice length (~500 chars)
        if len(clean) > 500:
            cutoff = clean[:500].rfind('.')
            if cutoff > 200:
                clean = clean[:cutoff + 1]
            else:
                clean = clean[:500] + '...'

        if not output_path:
            with tempfile.NamedTemporaryFile(
                suffix='.wav', delete=False
            ) as f:
                output_path = f.name

        # try pyttsx3 (local, free)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            engine.setProperty('volume', 0.9)
            voices = engine.getProperty('voices')
            if voices:
                engine.setProperty('voice', voices[0].id)
            engine.save_to_file(clean, output_path)
            engine.runAndWait()
            if os.path.exists(output_path) and \
                    os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            print(f'[MediaProcessor] pyttsx3 failed: {e}')

        # fallback: espeak directly via subprocess
        try:
            result = subprocess.run(
                ['espeak', '-w', output_path, '-s', '150', clean],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and \
                    os.path.exists(output_path) and \
                    os.path.getsize(output_path) > 0:
                return output_path
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f'[MediaProcessor] espeak failed: {e}')

        return None

    def generate_embedding(self, text: str) -> list[float]:
        """
        Google Text Embedding 004 — 768 dimensions.
        Used for semantic memory storage.
        """
        if not self.available:
            return []
        if _GENAI_NEW:
            result = self._client.models.embed_content(
                model='models/text-embedding-004',
                contents=text,
                config=genai_types.EmbedContentConfig(
                    task_type='retrieval_document',
                ),
            )
            return list(result.embeddings[0].values)
        else:
            result = genai.embed_content(
                model='models/text-embedding-004',
                content=text,
                task_type='retrieval_document',
            )
            return result['embedding']
