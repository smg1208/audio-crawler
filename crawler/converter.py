
import subprocess
from typing import List, Optional

# Optional import for edge-tts — will be used only when selected
try:
    # edge-tts is asynchronous and exposes Communicate
    from edge_tts import Communicate  # type: ignore
except Exception:  # pragma: no cover - runtime environment may not have edge-tts
    Communicate = None  # type: ignore


class TextToAudioConverter:
    """Pluggable converter for text -> audio.

    Backends supported:
      - 'ttx' (subprocess command-line tool)
      - 'edge-tts' (Python wrapper around Microsoft Edge TTS)

    Behaviors:
      - dry_run: if True, conversion is not executed but printed.
    """

    def __init__(self, backend: str = 'ttx', ttx_cmd: str = 'ttx', dry_run: bool = False, extra_args: Optional[List[str]] = None):
        self.backend = backend
        self.ttx_cmd = ttx_cmd
        self.dry_run = dry_run
        self.extra_args = extra_args or []

    def convert(self, input_text_path: str, output_audio_path: str, voice: Optional[str] = None) -> None:
        if self.backend == 'ttx':
            return self._convert_ttx(input_text_path, output_audio_path)
        elif self.backend == 'edge-tts':
            return self._convert_edge_tts(input_text_path, output_audio_path, voice)
        else:
            raise ValueError(f'Unknown backend: {self.backend}')

    def _convert_ttx(self, input_text_path: str, output_audio_path: str) -> None:
        cmd = [self.ttx_cmd, '-i', input_text_path, '-o', output_audio_path] + self.extra_args

        if self.dry_run:
            print(f"[dry-run] would run: {' '.join(cmd)}")
            return

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ttx failed: {proc.returncode}\n{proc.stdout}\n{proc.stderr}")

    def _convert_edge_tts(self, input_text_path: str, output_audio_path: str, voice: Optional[str]) -> None:
        # If dry-run, we don't need the actual library installed — just report what would happen
        if self.dry_run:
            print(f"[dry-run] edge-tts would synthesize to {output_audio_path} with voice={voice}")
            return

        if Communicate is None:
            raise RuntimeError("edge-tts library is not available — install edge-tts to use this backend")

        with open(input_text_path, 'r', encoding='utf-8') as fh:
            text = fh.read()

        # Use the edge-tts Communicate API to synthesize to file
        # Communicate.save is asynchronous; we'll run it in an event loop
        try:
            import asyncio

            async def _run():
                comm = Communicate(text, voice=voice) if voice else Communicate(text)
                await comm.save(output_audio_path)

            asyncio.run(_run())
        except Exception as exc:
            raise RuntimeError(f"edge-tts synthesis failed: {exc}")

