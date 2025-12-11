
import subprocess
import asyncio
from typing import List, Optional, Iterable, Tuple

# Import TTS engines theo Strategy Pattern
try:
    from crawler.tts_engines import (
        BaseTTS, EdgeTTS, MacOSTTS, GTTS, FPTAITTS, GoogleCloudTTS, CoquiTTS, AzureTTS,
        TTSManager, FallbackTTS
    )
    TTS_ENGINES_AVAILABLE = True
except ImportError:
    TTS_ENGINES_AVAILABLE = False

# Import edge_tts và các thư viện khác cho fallback (luôn cần thiết)
try:
    from edge_tts import Communicate  # type: ignore
except Exception:
    Communicate = None  # type: ignore

try:
    from gtts import gTTS  # type: ignore
except Exception:
    gTTS = None  # type: ignore

try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore


class TextToAudioConverter:
    """Pluggable converter for text -> audio.

    Backends supported:
      - 'ttx' (subprocess command-line tool)
      - 'edge-tts' (Microsoft Edge TTS - online, high quality)
      - 'macos' (macOS native TTS using 'say' command - offline)
      - 'gtts' (Google Text-to-Speech - free, simple, no API key needed)
      - 'fpt-ai' (FPT.AI TTS - high quality Vietnamese TTS, requires API key)

    Behaviors:
      - dry_run: if True, conversion is not executed but printed.
      - enable_fallback: if True, automatically fallback to other engines on error
      - fpt_api_key: API key for FPT.AI TTS (required if backend='fpt-ai')
      - fpt_voice: Voice name for FPT.AI TTS (default: 'banmai')
      - macos_voice: Voice name for macOS TTS (default: 'Linh')
      - edge_rate: Speech rate for Edge TTS (0.5-2.0, default: 1.0)
    """

    def __init__(self, backend: str = 'ttx', ttx_cmd: str = 'ttx', dry_run: bool = False, 
                 extra_args: Optional[List[str]] = None, fpt_api_key: Optional[str] = None,
                 fpt_voice: str = 'banmai', macos_voice: str = 'Linh', edge_rate: float = 1.0,
                 enable_fallback: bool = False, fallback_engines: Optional[List[str]] = None,
                 piper_model_path: Optional[str] = None, piper_config_path: Optional[str] = None,
                 google_cloud_credentials_path: Optional[str] = None, google_cloud_language_code: str = 'vi-VN',
                 google_cloud_voice_name: Optional[str] = None, google_cloud_ssml_gender: Optional[str] = None,
                 coqui_model_name: Optional[str] = None, coqui_device: Optional[str] = None,
                 coqui_speaker_wav: Optional[str] = None, coqui_language: str = "vi",
                 azure_subscription_key: Optional[str] = None, azure_region: str = 'eastus',
                 azure_voice_name: str = 'vi-VN-HoaiMyNeural'):
        self.backend = backend
        self.ttx_cmd = ttx_cmd
        self.dry_run = dry_run
        self.extra_args = extra_args or []
        self.fpt_api_key = fpt_api_key
        self.fpt_voice = fpt_voice
        self.macos_voice = macos_voice
        self.edge_rate = edge_rate
        self.enable_fallback = enable_fallback
        self.fallback_engines = fallback_engines or ['macos', 'gtts']
        self.piper_model_path = piper_model_path
        self.piper_config_path = piper_config_path
        self.google_cloud_credentials_path = google_cloud_credentials_path
        self.google_cloud_language_code = google_cloud_language_code
        self.google_cloud_voice_name = google_cloud_voice_name
        self.google_cloud_ssml_gender = google_cloud_ssml_gender
        self.coqui_model_name = coqui_model_name
        self.coqui_device = coqui_device
        self.coqui_speaker_wav = coqui_speaker_wav
        self.coqui_language = coqui_language
        self.azure_subscription_key = azure_subscription_key
        self.azure_region = azure_region
        self.azure_voice_name = azure_voice_name
        
        # Tạo TTS engine nếu sử dụng engine mới
        self.tts_engine: Optional[BaseTTS] = None
        if TTS_ENGINES_AVAILABLE and backend in ['edge-tts', 'macos', 'gtts', 'fpt-ai', 'piper', 'google-cloud', 'coqui', 'azure']:
            self._init_tts_engine()

    def _init_tts_engine(self) -> None:
        """Khởi tạo TTS engine dựa trên backend."""
        if not TTS_ENGINES_AVAILABLE:
            return
        
        try:
            if self.enable_fallback:
                # Sử dụng FallbackTTS
                self.tts_engine = TTSManager.create_with_fallback(
                    primary_engine=self.backend,
                    fallback_engines=self.fallback_engines,
                    voice=self._get_voice_for_engine(),
                    rate=self.edge_rate if self.backend == 'edge-tts' else None,
                    api_key=self.fpt_api_key if self.backend == 'fpt-ai' else None,
                    dry_run=self.dry_run
                )
            else:
                # Sử dụng engine đơn lẻ
                kwargs = {
                    'dry_run': self.dry_run
                }
                
                if self.backend == 'edge-tts':
                    kwargs['voice'] = self._get_voice_for_engine() or 'vi-VN-NamMinhNeural'
                    kwargs['rate'] = self.edge_rate
                elif self.backend == 'macos':
                    kwargs['voice'] = self.macos_voice
                elif self.backend == 'fpt-ai':
                    kwargs['api_key'] = self.fpt_api_key
                    kwargs['voice'] = self._get_voice_for_engine() or self.fpt_voice
                elif self.backend == 'piper':
                    if not self.piper_model_path:
                        raise ValueError("piper_model_path is required when using piper backend")
                    kwargs['model_path'] = self.piper_model_path
                    kwargs['config_path'] = self.piper_config_path
                elif self.backend == 'google-cloud':
                    kwargs['credentials_path'] = self.google_cloud_credentials_path
                    kwargs['language_code'] = self.google_cloud_language_code
                    kwargs['voice_name'] = self.google_cloud_voice_name
                    kwargs['ssml_gender'] = self.google_cloud_ssml_gender
                elif self.backend == 'coqui':
                    kwargs['model_name'] = self.coqui_model_name or 'tts_models/multilingual/multi-dataset/xtts_v2'
                    kwargs['device'] = self.coqui_device
                    kwargs['speaker_wav'] = self.coqui_speaker_wav
                    kwargs['language'] = self.coqui_language
                elif self.backend == 'azure':
                    kwargs['subscription_key'] = self.azure_subscription_key
                    kwargs['region'] = self.azure_region
                    kwargs['voice_name'] = self.azure_voice_name
                
                self.tts_engine = TTSManager.create_engine(self.backend, **kwargs)
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize TTS engine: {e}")
            self.tts_engine = None
    
    def _get_voice_for_engine(self) -> Optional[str]:
        """Lấy voice phù hợp với engine hiện tại."""
        # Có thể override trong tương lai
        return None
    
    def convert(self, input_text_path: str, output_audio_path: str, voice: Optional[str] = None) -> None:
        """Chuyển đổi text file thành audio file.
        
        Args:
            input_text_path: Đường dẫn file text đầu vào
            output_audio_path: Đường dẫn file audio đầu ra
            voice: Tên giọng đọc (tùy chọn, override voice mặc định)
        """
        # Nếu có TTS engine mới, sử dụng nó
        if self.tts_engine is not None:
            return self._convert_with_engine(input_text_path, output_audio_path, voice)
        
        # Fallback về code cũ cho backward compatibility
        if self.backend == 'ttx':
            return self._convert_ttx(input_text_path, output_audio_path)
        elif self.backend == 'edge-tts':
            return self._convert_edge_tts(input_text_path, output_audio_path, voice)
        elif self.backend == 'gtts':
            return self._convert_gtts(input_text_path, output_audio_path)
        elif self.backend == 'fpt-ai':
            return self._convert_fpt_ai(input_text_path, output_audio_path, voice)
        else:
            raise ValueError(f'Unknown backend: {self.backend}')
    
    def _convert_with_engine(self, input_text_path: str, output_audio_path: str, voice: Optional[str] = None) -> None:
        """Chuyển đổi sử dụng TTS engine mới (Strategy Pattern)."""
        if self.tts_engine is None:
            raise RuntimeError("TTS engine not initialized")
        
        # Đọc text từ file
        with open(input_text_path, 'r', encoding='utf-8') as fh:
            text = fh.read()
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        # Override voice nếu được cung cấp
        if voice and hasattr(self.tts_engine, 'voice'):
            self.tts_engine.voice = voice
        
        # Chạy conversion (async)
        try:
            asyncio.run(self.tts_engine.speak(text, output_audio_path))
        except Exception as exc:
            raise RuntimeError(f"TTS conversion failed: {exc}")

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
            print(f"[dry-run] edge-tts would synthesize to {output_audio_path} with voice={voice}, rate={self.edge_rate}")
            return

        if Communicate is None:
            raise RuntimeError("edge-tts library is not available — install edge-tts to use this backend")

        with open(input_text_path, 'r', encoding='utf-8') as fh:
            text = fh.read()

        # Convert rate to edge-tts format (+X% or -X%)
        if self.edge_rate == 1.0:
            rate_str = "+0%"
        elif self.edge_rate > 1.0:
            rate_str = f"+{int((self.edge_rate - 1.0) * 100)}%"
        else:
            rate_str = f"{int((self.edge_rate - 1.0) * 100)}%"

        # Use the edge-tts Communicate API to synthesize to file
        # Communicate.save is asynchronous; we'll run it in an event loop
        try:
            async def _run_single(text: str, out_path: str, voice_arg: Optional[str], rate: str):
                if voice_arg:
                    comm = Communicate(text, voice=voice_arg, rate=rate)
                else:
                    comm = Communicate(text, rate=rate)
                await comm.save(out_path)

            asyncio.run(_run_single(text, output_audio_path, voice, rate_str))
        except Exception as exc:
            raise RuntimeError(f"edge-tts synthesis failed: {exc}")

    def convert_batch(self, tasks: Iterable[Tuple[str, str, Optional[str]]], concurrency: int = 4, max_retries: int = 3, retry_failed: bool = True) -> list:
        """Convert multiple text files to audio concurrently with retry mechanism.

        Args:
            tasks: iterable of tuples (input_text_path, output_audio_path, voice)
            concurrency: max number of concurrent TTS syntheses
            max_retries: Số lần retry tối đa cho mỗi task (mặc định: 3)
            retry_failed: Nếu True, tự động retry các task bị fail (mặc định: True)

        Returns:
            List of failed tasks: [(input_path, output_path, voice, error), ...]

        Notes:
            - Hỗ trợ tất cả TTS engines (edge-tts, macos, gtts, fpt-ai, piper, google-cloud)
            - Sử dụng asyncio để chạy song song
            - Keep `concurrency` modest (e.g. 2-8) to avoid remote throttling hoặc overload system
            - Google Cloud TTS: concurrency có thể cao hơn (10-20) vì client là thread-safe
        """
        if self.tts_engine is None:
            # Nếu TTS engine không được khởi tạo, không thể convert
            if self.backend == 'coqui':
                raise RuntimeError(
                    'Coqui TTS engine failed to initialize. '
                    'This is often due to PyTorch version compatibility issues. '
                    'Please try:\n'
                    '  - pip install transformers==4.35.0\n'
                    '  - Or use another backend: google-cloud, azure, or macos'
                )
            # Fallback về code cũ cho edge-tts (chỉ khi backend là edge-tts)
            if self.backend != 'edge-tts':
                raise RuntimeError(f'convert_batch is only supported for TTS backends, not {self.backend}')
            if Communicate is None:
                raise RuntimeError('edge-tts library is not available — install edge-tts to use this backend')
            
            # Code cũ cho edge-tts
            # Convert rate to edge-tts format (+X% or -X%)
            if self.edge_rate == 1.0:
                rate_str = "+0%"
            elif self.edge_rate > 1.0:
                rate_str = f"+{int((self.edge_rate - 1.0) * 100)}%"
            else:
                rate_str = f"{int((self.edge_rate - 1.0) * 100)}%"
            
            async def _worker(sem: asyncio.Semaphore, in_path: str, out_path: str, voice_arg: Optional[str]):
                async with sem:
                    # Thêm delay ngẫu nhiên nhỏ (0-1s) để tránh rate limiting khi nhiều workers chạy song song
                    import random
                    await asyncio.sleep(random.uniform(0, 1.0))
                    
                    loop = asyncio.get_event_loop()
                    def _read_file(p: str) -> str:
                        with open(p, 'r', encoding='utf-8') as fh:
                            return fh.read()
                    text = await loop.run_in_executor(None, _read_file, in_path)
                    
                    # Retry logic với exponential backoff
                    last_error = None
                    for attempt in range(max_retries):
                        try:
                    if voice_arg:
                        comm = Communicate(text, voice=voice_arg, rate=rate_str)
                    else:
                        comm = Communicate(text, rate=rate_str)
                    await comm.save(out_path)
                            
                            # Verify file was created
                            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                                return  # Success
                            else:
                                raise RuntimeError("Audio file was not created or is empty")
                        except Exception as exc:
                            last_error = exc
                            error_str = str(exc).lower()
                            is_rate_limit = (
                                "no audio" in error_str or
                                "no audio received" in error_str or
                                "rate limit" in error_str or
                                "too many requests" in error_str
                            )
                            
                            if attempt < max_retries - 1:
                                # Exponential backoff: 3s, 6s, 12s...
                                wait_time = 3.0 * (2 ** attempt)
                                if is_rate_limit:
                                    print(f"⚠️  Edge TTS rate limited for {os.path.basename(in_path)}. Waiting {wait_time}s...")
                                await asyncio.sleep(wait_time)
                            else:
                                # Final attempt failed
                                raise RuntimeError(f"EdgeTTS failed after {max_retries} attempts: {last_error}")

            async def _run_all():
                sem = asyncio.Semaphore(concurrency)
                task_list = list(tasks)  # Convert to list to preserve order
                tasks_async = [asyncio.create_task(_worker(sem, inp, out, v)) for (inp, out, v) in task_list]
                results = await asyncio.gather(*tasks_async, return_exceptions=True)
                
                # Log errors but don't raise - continue processing other tasks
                failed_count = 0
                for i, r in enumerate(results):
                    if isinstance(r, Exception):
                        inp, out, v = task_list[i]
                        print(f"⚠️  Error converting {inp} -> {out}: {r}")
                        failed_count += 1
                
                if failed_count > 0:
                    print(f"⚠️  {failed_count}/{len(task_list)} tasks failed during batch conversion")
                    # Don't raise - let run.py handle individual task status

            if self.dry_run:
                for inp, out, v in tasks:
                    print(f"[dry-run] edge-tts would synthesize {inp} -> {out} with voice={v}")
                return

            try:
                asyncio.run(_run_all())
            except Exception as exc:
                print(f"⚠️  Fatal error during batch conversion: {exc}")
                raise RuntimeError(f"edge-tts batch synthesis failed: {exc}")
            return
        
        # Sử dụng TTS engine mới
        async def _worker(sem: asyncio.Semaphore, in_path: str, out_path: str, voice_arg: Optional[str], retry_count: int = 0):
            async with sem:
                # Đọc text trong worker
                loop = asyncio.get_event_loop()
                def _read_file(p: str) -> str:
                    with open(p, 'r', encoding='utf-8') as fh:
                        return fh.read()
                text = await loop.run_in_executor(None, _read_file, in_path)
                
                # Sử dụng engine hiện tại (voice được set trong engine)
                engine = self.tts_engine
                if voice_arg and hasattr(engine, 'voice') and not isinstance(engine, FallbackTTS):
                    # Override voice nếu được cung cấp
                    engine.voice = voice_arg
                
                # Retry logic cho các engine hỗ trợ
                if isinstance(engine, GoogleCloudTTS):
                    await engine.speak(text, out_path, max_retries=max_retries, retry_delay=1.0)
                elif isinstance(engine, EdgeTTS):
                    # EdgeTTS với retry để xử lý rate limiting
                    await engine.speak(text, out_path, max_retries=max_retries, retry_delay=2.0)
                else:
                    await engine.speak(text, out_path)

        async def _run_all():
            sem = asyncio.Semaphore(concurrency)
            task_list = list(tasks)  # Convert to list to preserve order
            tasks_async = [asyncio.create_task(_worker(sem, inp, out, v)) for (inp, out, v) in task_list]
            results = await asyncio.gather(*tasks_async, return_exceptions=True)
            
            # Collect failed tasks
            failed_tasks = []
            failed_count = 0
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    inp, out, v = task_list[i]
                    print(f"⚠️  Error converting {inp} -> {out}: {r}")
                    failed_tasks.append((inp, out, v, r))
                    failed_count += 1
            
            if failed_count > 0:
                print(f"⚠️  {failed_count}/{len(task_list)} tasks failed during batch conversion")
            
            return failed_tasks

        if self.dry_run:
            for inp, out, v in tasks:
                print(f"[dry-run] {self.backend} would synthesize {inp} -> {out} with voice={v}")
            return

        async def _run_with_retry():
            failed_tasks = await _run_all()
            
            # Retry failed tasks nếu được yêu cầu
            if retry_failed and failed_tasks:
                print(f"\n🔄 Retrying {len(failed_tasks)} failed tasks...")
                retry_sem = asyncio.Semaphore(concurrency)
                retry_tasks_async = [
                    asyncio.create_task(_worker(retry_sem, inp, out, v))
                    for (inp, out, v, _) in failed_tasks
                ]
                retry_results = await asyncio.gather(*retry_tasks_async, return_exceptions=True)
                
                # Check retry results
                still_failed = []
                for i, r in enumerate(retry_results):
                    if isinstance(r, Exception):
                        inp, out, v, orig_error = failed_tasks[i]
                        print(f"⚠️  Retry failed for {inp} -> {out}: {r}")
                        still_failed.append((inp, out, v, r))
                    else:
                        inp, out, v, orig_error = failed_tasks[i]
                        print(f"✓ Retry successful for {inp} -> {out}")
                
                if still_failed:
                    print(f"⚠️  {len(still_failed)} tasks still failed after retry")
                else:
                    print(f"✓ All failed tasks succeeded after retry")
                
                return still_failed
            else:
                return failed_tasks
        
        try:
            return asyncio.run(_run_with_retry())
        except Exception as exc:
            print(f"⚠️  Fatal error during batch conversion: {exc}")
            raise RuntimeError(f"{self.backend} batch synthesis failed: {exc}")

    def _convert_gtts(self, input_text_path: str, output_audio_path: str) -> None:
        """Convert text to audio using Google Text-to-Speech (gTTS).
        
        gTTS is free, simple, and doesn't require API keys.
        Language code: 'vi' for Vietnamese.
        """
        if self.dry_run:
            print(f"[dry-run] gTTS would synthesize to {output_audio_path}")
            return

        if gTTS is None:
            raise RuntimeError("gTTS library is not available — install gtts to use this backend: pip install gtts")

        with open(input_text_path, 'r', encoding='utf-8') as fh:
            text = fh.read()

        if not text.strip():
            raise RuntimeError("Input text is empty")

        try:
            # gTTS supports Vietnamese with lang='vi'
            # slow=False means normal speed, True means slower
            tts = gTTS(text=text, lang='vi', slow=False)
            tts.save(output_audio_path)
        except Exception as exc:
            raise RuntimeError(f"gTTS synthesis failed: {exc}")

    def _convert_fpt_ai(self, input_text_path: str, output_audio_path: str, voice: Optional[str] = None) -> None:
        """Convert text to audio using FPT.AI TTS.
        
        FPT.AI provides high-quality Vietnamese TTS with multiple voices.
        Requires API key (free tier available).
        Voice options: 'banmai' (female, Northern), 'lannhi' (female, Southern), 
                      'leminh' (male, Northern), 'giahuy' (male, Southern)
        """
        if self.dry_run:
            print(f"[dry-run] FPT.AI TTS would synthesize to {output_audio_path} with voice={voice or self.fpt_voice}")
            return

        if requests is None:
            raise RuntimeError("requests library is not available — install requests to use this backend")

        if not self.fpt_api_key:
            raise RuntimeError("FPT.AI API key is required — set fpt_api_key in converter initialization")

        with open(input_text_path, 'r', encoding='utf-8') as fh:
            text = fh.read()

        if not text.strip():
            raise RuntimeError("Input text is empty")

        # Use provided voice or default
        voice_name = voice or self.fpt_voice

        try:
            # FPT.AI TTS API endpoint
            url = "https://api.fpt.ai/hmi/tts/v5"
            headers = {
                "api-key": self.fpt_api_key,
                "voice": voice_name,
                "speed": "0",  # -5 to 5, 0 is normal
                "prosody": "1"  # 0-2, 1 is normal
            }
            data = text.encode('utf-8')

            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()

            # FPT.AI returns audio as binary data
            with open(output_audio_path, 'wb') as fh:
                fh.write(response.content)

        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"FPT.AI TTS API request failed: {exc}")
        except Exception as exc:
            raise RuntimeError(f"FPT.AI TTS synthesis failed: {exc}")

