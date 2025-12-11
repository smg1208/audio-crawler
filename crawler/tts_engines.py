"""
Module chứa các TTS Engine theo Strategy Pattern.

Mỗi engine kế thừa từ BaseTTS và implement method speak().
"""

import asyncio
import subprocess
import os
import sys
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path

# Optional imports cho các engine khác nhau
try:
    from edge_tts import Communicate
except Exception:
    Communicate = None

try:
    from gtts import gTTS
except Exception:
    gTTS = None

try:
    import requests
except Exception:
    requests = None

try:
    from piper import PiperVoice
    PIPER_AVAILABLE = True
except Exception:
    PIPER_AVAILABLE = False
    PiperVoice = None

try:
    from google.cloud import texttospeech
    GOOGLE_CLOUD_TTS_AVAILABLE = True
except Exception:
    GOOGLE_CLOUD_TTS_AVAILABLE = False
    texttospeech = None

try:
    from TTS.api import TTS as CoquiTTSAPI
    import torch
    COQUI_TTS_AVAILABLE = True
except Exception:
    COQUI_TTS_AVAILABLE = False
    CoquiTTSAPI = None
    torch = None

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_TTS_AVAILABLE = True
except Exception:
    AZURE_TTS_AVAILABLE = False
    speechsdk = None


class BaseTTS(ABC):
    """Abstract Base Class cho tất cả TTS engines.
    
    Mỗi engine phải implement method speak() để chuyển text thành audio.
    """
    
    def __init__(self, voice: Optional[str] = None, dry_run: bool = False):
        """
        Args:
            voice: Tên giọng đọc (tùy chọn, mỗi engine có format riêng)
            dry_run: Nếu True, chỉ in ra thông tin mà không thực sự convert
        """
        self.voice = voice
        self.dry_run = dry_run
    
    @abstractmethod
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio file.
        
        Args:
            text: Văn bản cần chuyển đổi
            output_file: Đường dẫn file audio đầu ra
            
        Raises:
            RuntimeError: Nếu conversion thất bại
        """
        pass
    
    def is_available(self) -> bool:
        """Kiểm tra xem engine này có sẵn sàng sử dụng không.
        
        Returns:
            True nếu engine có thể sử dụng, False nếu không
        """
        return True


class EdgeTTS(BaseTTS):
    """Microsoft Edge TTS Engine - Online, chất lượng cao.
    
    Sử dụng edge-tts library để gọi Microsoft Edge TTS service.
    Hỗ trợ async/await và nhiều giọng đọc tiếng Việt.
    
    Tự động chia text thành các chunks nhỏ để tránh lỗi "No audio received"
    khi text quá dài, sau đó nối các file audio lại thành một file duy nhất.
    """
    
    def __init__(self, voice: str = "vi-VN-NamMinhNeural", rate: float = 1.0, dry_run: bool = False):
        """
        Args:
            voice: Tên giọng đọc (mặc định: vi-VN-NamMinhNeural)
            rate: Tốc độ đọc (0.5-2.0, mặc định: 1.0)
            dry_run: Nếu True, chỉ in ra thông tin
        """
        super().__init__(voice=voice, dry_run=dry_run)
        self.rate = rate
        self.max_chunk_size = 1500  # Tối đa 1500 ký tự mỗi chunk
    
    def is_available(self) -> bool:
        """Kiểm tra edge-tts có sẵn không."""
        return Communicate is not None
    
    def _split_text_into_chunks(self, text: str, max_size: int = 1500) -> list:
        """Chia text thành các chunks nhỏ hơn.
        
        Ưu tiên cắt tại dấu câu (., !, ?, \n) để giọng đọc không bị đứt quãng.
        
        Args:
            text: Text cần chia
            max_size: Kích thước tối đa mỗi chunk (ký tự, mặc định: 1500)
            
        Returns:
            Danh sách các chunks text
        """
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Tách text thành các phần theo dấu câu và xuống dòng
        import re
        # Tách theo: dấu chấm, chấm hỏi, chấm than, xuống dòng
        # Giữ lại dấu câu trong kết quả
        parts = re.split(r'([.!?\n])', text)
        
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue
            
            # Lấy dấu câu kèm theo (nếu có)
            punctuation = ""
            if i + 1 < len(parts) and parts[i + 1] in ['.', '!', '?', '\n']:
                punctuation = parts[i + 1]
                i += 2
            else:
                i += 1
            
            # Thêm dấu câu vào phần text
            if punctuation:
                part += punctuation
            
            # Kiểm tra xem có thể thêm vào chunk hiện tại không
            test_chunk = current_chunk + " " + part if current_chunk else part
            
            if len(test_chunk) <= max_size:
                current_chunk = test_chunk
            else:
                # Lưu chunk hiện tại (nếu có)
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Nếu phần mới vẫn quá dài, chia nhỏ hơn theo từ
                if len(part) > max_size:
                    words = part.split()
                    temp_chunk = ""
                    for word in words:
                        test_word = temp_chunk + " " + word if temp_chunk else word
                        if len(test_word) <= max_size:
                            temp_chunk = test_word
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            temp_chunk = word
                    current_chunk = temp_chunk
                else:
                    current_chunk = part
        
        # Thêm chunk cuối cùng
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text]
    
    def _concat_mp3_files(self, input_files: list, output_file: str) -> bool:
        """Nối nhiều file MP3 thành một file bằng ffmpeg.
        
        Args:
            input_files: Danh sách đường dẫn file MP3 đầu vào
            output_file: Đường dẫn file MP3 đầu ra
            
        Returns:
            True nếu thành công, False nếu không có ffmpeg hoặc lỗi
        """
        try:
            # Kiểm tra ffmpeg có sẵn không
            result = subprocess.run(
                ['which', 'ffmpeg'],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            # Tạo file list cho ffmpeg concat
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for input_file in input_files:
                    # Sử dụng absolute path để tránh lỗi
                    abs_path = os.path.abspath(input_file)
                    f.write(f"file '{abs_path}'\n")
                concat_list = f.name
            
            try:
                # Nối bằng ffmpeg
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_list,
                    '-c', 'copy',
                    '-y',  # Overwrite output file
                    output_file
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=120)
                
                return result.returncode == 0
            finally:
                # Xóa file list tạm
                try:
                    os.remove(concat_list)
                except Exception:
                    pass
        except Exception:
            return False
    
    async def speak(self, text: str, output_file: str, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        """Chuyển đổi text thành audio bằng Edge TTS với retry mechanism để xử lý rate limiting.
        
        Tự động chia text thành các chunks nhỏ nếu text quá dài,
        sau đó nối các file audio lại thành một file duy nhất.
        
        Args:
            text: Văn bản cần chuyển đổi
            output_file: Đường dẫn file audio đầu ra
            max_retries: Số lần retry tối đa khi bị rate limit (mặc định: 3)
            retry_delay: Delay giữa các lần retry (giây, mặc định: 2.0, tăng dần theo exponential backoff)
        """
        if self.dry_run:
            print(f"[dry-run] EdgeTTS would synthesize to {output_file} with voice={self.voice}, rate={self.rate}")
            return
        
        if not self.is_available():
            raise RuntimeError("edge-tts library is not available — install edge-tts to use this backend")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        # Convert rate to edge-tts format (+X% or -X%)
        if self.rate == 1.0:
            rate_str = "+0%"
        elif self.rate > 1.0:
            rate_str = f"+{int((self.rate - 1.0) * 100)}%"
        else:
            rate_str = f"{int((self.rate - 1.0) * 100)}%"
        
        # Chia text thành các chunks
        text_chunks = self._split_text_into_chunks(text, max_size=self.max_chunk_size)
        
        # Nếu chỉ có 1 chunk, xử lý với retry
        if len(text_chunks) == 1:
            last_error = None
            for attempt in range(max_retries):
            try:
                comm = Communicate(text=text, voice=self.voice, rate=rate_str)
                await comm.save(output_file)
                    # Verify file was created
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return
                    else:
                        raise RuntimeError("Audio file was not created or is empty")
            except Exception as exc:
                    last_error = exc
                    error_str = str(exc).lower()
                    # Check if it's a rate limiting / blocking issue
                    is_rate_limit = (
                        "no audio" in error_str or
                        "no audio received" in error_str or
                        "rate limit" in error_str or
                        "too many requests" in error_str or
                        "blocked" in error_str
                    )
                    
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s...
                        wait_time = retry_delay * (2 ** attempt)
                        if is_rate_limit:
                            print(f"⚠️  Edge TTS rate limited/blocked (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s before retry...")
                        else:
                            print(f"⚠️  Edge TTS error (attempt {attempt + 1}/{max_retries}): {exc}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise RuntimeError(f"EdgeTTS synthesis failed after {max_retries} attempts: {last_error}")
            return
        
        # Nhiều chunks: xử lý từng chunk và nối lại với retry và delay
        temp_files = []
        failed_chunks = []
        
        try:
            print(f"  Text quá dài ({len(text)} ký tự), chia thành {len(text_chunks)} chunks...")
            
            # Tạo audio cho từng chunk với retry và delay để tránh rate limiting
            for i, chunk in enumerate(text_chunks):
                temp_file = f"{output_file}.part_{i}.mp3"
                temp_files.append(temp_file)
                
                # Thêm delay giữa các chunks để tránh rate limiting (trừ chunk đầu tiên)
                if i > 0:
                    delay_between_chunks = 1.0  # 1 giây delay giữa các chunks
                    await asyncio.sleep(delay_between_chunks)
                
                # Retry cho từng chunk
                chunk_success = False
                last_chunk_error = None
                
                for chunk_attempt in range(max_retries):
                try:
                    print(f"  Đang tạo chunk {i+1}/{len(text_chunks)} ({len(chunk)} ký tự)...")
                    comm = Communicate(text=chunk, voice=self.voice, rate=rate_str)
                    await comm.save(temp_file)
                    
                    # Kiểm tra file đã được tạo và có nội dung
                        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                            chunk_success = True
                            break  # Thành công, thoát retry loop
                        else:
                        raise RuntimeError(f"Chunk {i+1} tạo file rỗng hoặc không tồn tại")
                    
                except Exception as chunk_exc:
                        last_chunk_error = chunk_exc
                        error_str = str(chunk_exc).lower()
                        is_rate_limit = (
                            "no audio" in error_str or
                            "no audio received" in error_str or
                            "rate limit" in error_str or
                            "too many requests" in error_str
                        )
                        
                        if chunk_attempt < max_retries - 1:
                            # Exponential backoff: 2s, 4s, 8s...
                            wait_time = retry_delay * (2 ** chunk_attempt)
                            if is_rate_limit:
                                print(f"  ⚠️  Chunk {i+1} bị rate limit (attempt {chunk_attempt + 1}/{max_retries}). Đợi {wait_time}s...")
                            else:
                                print(f"  ⚠️  Chunk {i+1} failed (attempt {chunk_attempt + 1}/{max_retries}): {chunk_exc}. Retry sau {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            # Đã hết retry
                            error_msg = f"Chunk {i+1}/{len(text_chunks)} failed after {max_retries} attempts: {last_chunk_error}"
                            print(f"  ❌ {error_msg}")
                    failed_chunks.append((i+1, error_msg))
                    # Xóa file lỗi nếu có
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception:
                        pass
            
            # Kiểm tra xem có chunk nào thành công không
            valid_files = [f for f in temp_files if os.path.exists(f) and os.path.getsize(f) > 0]
            
            if not valid_files:
                raise RuntimeError(f"Tất cả {len(text_chunks)} chunks đều thất bại. Lỗi: {failed_chunks}")
            
            if len(failed_chunks) > 0:
                print(f"  ⚠️  {len(failed_chunks)}/{len(text_chunks)} chunks thất bại, nhưng sẽ tiếp tục với {len(valid_files)} chunks thành công")
            
            # Nối các file audio lại
            if len(valid_files) == 1:
                # Chỉ có 1 file, đổi tên trực tiếp
                os.rename(valid_files[0], output_file)
            else:
                # Nhiều files, nối bằng ffmpeg
                print(f"  Đang nối {len(valid_files)} file audio...")
                if self._concat_mp3_files(valid_files, output_file):
                    print(f"  ✓ Đã nối thành công {len(valid_files)} chunks")
                else:
                    # Nếu không có ffmpeg, lưu chunk đầu tiên và cảnh báo
                    print(f"  ⚠️  Warning: ffmpeg not available. Only first chunk saved to {output_file}")
                    print(f"     Install ffmpeg to concatenate all chunks: brew install ffmpeg")
                    os.rename(valid_files[0], output_file)
        
        finally:
            # Xóa các file tạm
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass


class MacOSTTS(BaseTTS):
    """macOS Native TTS Engine - Offline, sử dụng lệnh 'say'.
    
    Sử dụng lệnh 'say' của macOS để chuyển text thành audio.
    Hoạt động offline, không cần kết nối Internet.
    """
    
    def __init__(self, voice: str = "Linh", dry_run: bool = False):
        """
        Args:
            voice: Tên giọng đọc macOS (mặc định: "Linh" - nữ, hoặc "Nam" - nam)
            dry_run: Nếu True, chỉ in ra thông tin
        """
        super().__init__(voice=voice, dry_run=dry_run)
        self._available_voices = None
    
    def is_available(self) -> bool:
        """Kiểm tra lệnh 'say' có sẵn không (chỉ trên macOS)."""
        if sys.platform != 'darwin':
            return False
        try:
            result = subprocess.run(['which', 'say'], capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False
    
    def list_voices(self) -> list:
        """Liệt kê các giọng đọc có sẵn trên macOS."""
        if not self.is_available():
            return []
        
        if self._available_voices is None:
            try:
                result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Parse output: "Linh            vi_VN    # Vietnamese"
                    voices = []
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            voice_name = line.split()[0]
                            voices.append(voice_name)
                    self._available_voices = voices
                else:
                    self._available_voices = []
            except Exception:
                self._available_voices = []
        
        return self._available_voices
    
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio bằng lệnh 'say' của macOS.
        
        Lưu ý: macOS 'say' xuất file .aiff hoặc .m4a mặc định.
        Nếu output_file có đuôi .mp3, sẽ cần convert sau đó (hoặc chấp nhận .m4a).
        """
        if self.dry_run:
            print(f"[dry-run] MacOSTTS would synthesize to {output_file} with voice={self.voice}")
            return
        
        if not self.is_available():
            raise RuntimeError("macOS 'say' command is not available (only works on macOS)")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        # Kiểm tra voice có tồn tại không
        available_voices = self.list_voices()
        if available_voices and self.voice not in available_voices:
            print(f"⚠️  Warning: Voice '{self.voice}' not found. Available voices: {available_voices[:5]}...")
            print(f"   Using default voice instead.")
            voice_arg = []  # Sử dụng voice mặc định
        else:
            voice_arg = ['-v', self.voice]
        
        # Xác định format output dựa trên extension
        output_path = Path(output_file)
        if output_path.suffix.lower() in ['.mp3', '.m4a', '.aac']:
            # macOS say không hỗ trợ trực tiếp mp3, sẽ xuất m4a/aiff
            # Nếu user muốn mp3, sẽ cần convert sau đó
            actual_output = str(output_path.with_suffix('.m4a'))
            format_args = ['--data-format=alac']  # Apple Lossless Audio Codec
        else:
            actual_output = output_file
            format_args = ['--data-format=LEF32@32000']  # Linear PCM
        
        try:
            # Chạy lệnh 'say' trong executor để không block event loop
            def _run_say():
                cmd = ['say'] + voice_arg + ['-o', actual_output] + format_args + [text]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise RuntimeError(f"macOS 'say' command failed: {result.stderr}")
                return actual_output
            
            # Chạy trong thread pool để không block
            loop = asyncio.get_event_loop()
            final_output = await loop.run_in_executor(None, _run_say)
            
            # Nếu user muốn mp3 nhưng macOS xuất m4a, có thể convert (nếu có ffmpeg)
            if output_path.suffix.lower() == '.mp3' and actual_output != output_file:
                # Thử convert sang mp3 bằng ffmpeg (nếu có)
                if self._convert_to_mp3(actual_output, output_file):
                    # Xóa file m4a tạm
                    try:
                        os.remove(actual_output)
                    except Exception:
                        pass
                else:
                    # Nếu không có ffmpeg, đổi tên file m4a thành mp3 (hoặc giữ nguyên)
                    print(f"⚠️  Warning: macOS 'say' outputs .m4a format. File saved as: {actual_output}")
                    print(f"   Install ffmpeg to convert to MP3: brew install ffmpeg")
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("macOS 'say' command timed out after 300 seconds")
        except Exception as exc:
            raise RuntimeError(f"MacOSTTS synthesis failed: {exc}")
    
    def _convert_to_mp3(self, input_file: str, output_file: str) -> bool:
        """Convert audio file sang MP3 bằng ffmpeg (nếu có).
        
        Returns:
            True nếu convert thành công, False nếu không có ffmpeg hoặc lỗi
        """
        try:
            result = subprocess.run(
                ['which', 'ffmpeg'],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            # Convert bằng ffmpeg
            cmd = [
                'ffmpeg', '-i', input_file,
                '-codec:a', 'libmp3lame',
                '-q:a', '2',  # Quality: 0-9, 2 là tốt
                '-y',  # Overwrite output file
                output_file
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False


class GTTS(BaseTTS):
    """Google Text-to-Speech Engine - Online, miễn phí, đơn giản.
    
    Sử dụng gTTS library để gọi Google TTS service.
    Không cần API key, hoạt động ổn định.
    """
    
    def __init__(self, lang: str = 'vi', slow: bool = False, dry_run: bool = False):
        """
        Args:
            lang: Mã ngôn ngữ (mặc định: 'vi' cho tiếng Việt)
            slow: Nếu True, đọc chậm hơn
            dry_run: Nếu True, chỉ in ra thông tin
        """
        super().__init__(voice=None, dry_run=dry_run)
        self.lang = lang
        self.slow = slow
    
    def is_available(self) -> bool:
        """Kiểm tra gTTS có sẵn không."""
        return gTTS is not None
    
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio bằng Google TTS."""
        if self.dry_run:
            print(f"[dry-run] GTTS would synthesize to {output_file} with lang={self.lang}")
            return
        
        if not self.is_available():
            raise RuntimeError("gTTS library is not available — install gtts to use this backend: pip install gtts")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        try:
            # Chạy gTTS trong executor vì nó là blocking
            def _run_gtts():
                tts = gTTS(text=text, lang=self.lang, slow=self.slow)
                tts.save(output_file)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _run_gtts)
            
        except Exception as exc:
            raise RuntimeError(f"GTTS synthesis failed: {exc}")


class PiperTTS(BaseTTS):
    """Piper TTS Engine - Offline, mã nguồn mở, tối ưu cho Apple Silicon.
    
    Piper TTS là engine offline chạy trên CPU, rất nhanh trên chip Apple Silicon (M4).
    Sử dụng ONNX model để synthesize speech.
    """
    
    def __init__(self, model_path: str, config_path: Optional[str] = None, dry_run: bool = False):
        """
        Args:
            model_path: Đường dẫn đến file model .onnx (ví dụ: 'models/vi_VN-vivos-x_low.onnx')
            config_path: Đường dẫn đến file config .json (tùy chọn, thường cùng tên với model)
            dry_run: Nếu True, chỉ in ra thông tin mà không thực sự convert
        
        Note:
            Model được load một lần duy nhất khi khởi tạo để tối ưu hiệu năng.
        """
        super().__init__(voice=None, dry_run=dry_run)
        self.model_path = Path(model_path)
        self.config_path = Path(config_path) if config_path else None
        
        # Kiểm tra file model có tồn tại không
        if not self.model_path.exists():
            raise FileNotFoundError(f"Piper model file not found: {self.model_path}")
        
        # Nếu không có config_path, thử tìm file .json cùng tên
        if self.config_path is None:
            config_candidate = self.model_path.with_suffix('.json')
            if config_candidate.exists():
                self.config_path = config_candidate
            else:
                # Piper có thể hoạt động không cần config file
                self.config_path = None
        
        # Load model một lần duy nhất khi khởi tạo
        self.voice: Optional[PiperVoice] = None
        if not self.dry_run:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load Piper model một lần duy nhất."""
        if not PIPER_AVAILABLE:
            raise RuntimeError(
                "piper-tts library is not available. Install with: pip install piper-tts"
            )
        
        try:
            # Load model với config nếu có
            if self.config_path and self.config_path.exists():
                self.voice = PiperVoice.load(str(self.model_path), config_path=str(self.config_path))
            else:
                # Load model không có config (Piper sẽ tự tìm config hoặc dùng default)
                self.voice = PiperVoice.load(str(self.model_path))
        except Exception as e:
            raise RuntimeError(f"Failed to load Piper model from {self.model_path}: {e}")
    
    def is_available(self) -> bool:
        """Kiểm tra Piper TTS có sẵn không."""
        if not PIPER_AVAILABLE:
            return False
        if not self.model_path.exists():
            return False
        return self.voice is not None or self.dry_run
    
    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> bool:
        """Convert file WAV sang MP3 bằng ffmpeg.
        
        Args:
            wav_path: Đường dẫn file WAV đầu vào
            mp3_path: Đường dẫn file MP3 đầu ra
            
        Returns:
            True nếu convert thành công, False nếu không có ffmpeg hoặc lỗi
        """
        try:
            # Kiểm tra ffmpeg có sẵn không
            result = subprocess.run(
                ['which', 'ffmpeg'],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            # Convert bằng ffmpeg
            cmd = [
                'ffmpeg',
                '-i', wav_path,
                '-codec:a', 'libmp3lame',
                '-q:a', '2',  # Quality: 0-9, 2 là tốt
                '-y',  # Overwrite output file
                mp3_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False
    
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio bằng Piper TTS.
        
        Quy trình:
        1. Synthesize text thành WAV bằng Piper
        2. Convert WAV sang MP3 bằng ffmpeg (nếu cần)
        3. Xóa file WAV tạm
        
        Args:
            text: Văn bản cần chuyển đổi
            output_file: Đường dẫn file audio đầu ra (có thể là .wav hoặc .mp3)
        """
        if self.dry_run:
            print(f"[dry-run] PiperTTS would synthesize to {output_file} using model {self.model_path}")
            return
        
        if not self.is_available():
            raise RuntimeError("Piper TTS is not available. Check model path and library installation.")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        output_path = Path(output_file)
        is_mp3_output = output_path.suffix.lower() == '.mp3'
        
        # Tạo file WAV tạm
        if is_mp3_output:
            wav_path = output_path.with_suffix('.wav')
        else:
            wav_path = output_path
        
        try:
            # Synthesize trong executor để không block event loop
            def _synthesize():
                if self.voice is None:
                    raise RuntimeError("Piper voice model not loaded")
                
                # Synthesize text thành audio
                audio_data = self.voice.synthesize(text)
                
                # Lưu vào file WAV
                with open(wav_path, 'wb') as f:
                    f.write(audio_data)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _synthesize)
            
            # Nếu output là MP3, convert từ WAV
            if is_mp3_output:
                if not self._convert_wav_to_mp3(str(wav_path), str(output_path)):
                    # Nếu không có ffmpeg, giữ file WAV và cảnh báo
                    print(f"⚠️  Warning: ffmpeg not available. Output saved as WAV: {wav_path}")
                    print(f"   Install ffmpeg to convert to MP3: brew install ffmpeg")
                    # Đổi tên file WAV thành output path (không phải MP3)
                    wav_path.rename(output_path.with_suffix('.wav'))
                else:
                    # Xóa file WAV tạm sau khi convert thành công
                    try:
                        wav_path.unlink()
                    except Exception:
                        pass
            
        except Exception as exc:
            # Xóa file WAV tạm nếu có lỗi
            if wav_path.exists():
                try:
                    wav_path.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"PiperTTS synthesis failed: {exc}")


class GoogleCloudTTS(BaseTTS):
    """Google Cloud Text-to-Speech Engine - Online, chất lượng cao, cần credentials.
    
    Sử dụng Google Cloud TTS API để chuyển text thành audio.
    Yêu cầu Google Cloud credentials và billing enabled.
    """
    
    def __init__(self, credentials_path: Optional[str] = None, 
                 language_code: str = 'vi-VN',
                 voice_name: Optional[str] = None,
                 ssml_gender: Optional[str] = None,
                 dry_run: bool = False):
        """
        Args:
            credentials_path: Đường dẫn đến file credentials JSON (tùy chọn, có thể dùng env var)
            language_code: Mã ngôn ngữ (mặc định: 'vi-VN' cho tiếng Việt)
            voice_name: Tên giọng đọc cụ thể (tùy chọn, ví dụ: 'vi-VN-Standard-A')
            ssml_gender: Giới tính giọng đọc ('NEUTRAL', 'FEMALE', 'MALE')
            dry_run: Nếu True, chỉ in ra thông tin mà không thực sự convert
        
        Note:
            Credentials có thể được set qua:
            - credentials_path: Đường dẫn đến file JSON
            - Environment variable: GOOGLE_APPLICATION_CREDENTIALS
        """
        super().__init__(voice=voice_name, dry_run=dry_run)
        self.credentials_path = credentials_path
        self.language_code = language_code
        self.voice_name = voice_name
        self.ssml_gender = ssml_gender
        
        # Khởi tạo client
        self.client: Optional[texttospeech.TextToSpeechClient] = None
        if not self.dry_run:
            self._init_client()
    
    def _init_client(self) -> None:
        """Khởi tạo Google Cloud TTS client."""
        if not GOOGLE_CLOUD_TTS_AVAILABLE:
            raise RuntimeError(
                "google-cloud-texttospeech library is not available. "
                "Install with: pip install google-cloud-texttospeech"
            )
        
        try:
            # Nếu có credentials_path, set environment variable
            if self.credentials_path:
                import os
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path
            
            # Khởi tạo client
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Cloud TTS client: {e}")
    
    def is_available(self) -> bool:
        """Kiểm tra Google Cloud TTS có sẵn không."""
        if not GOOGLE_CLOUD_TTS_AVAILABLE:
            return False
        return self.client is not None or self.dry_run
    
    def _split_text_into_chunks(self, text: str, max_bytes: int = 4500, max_sentence_length: int = 150) -> list:
        """Chia text thành các chunks nhỏ hơn để tránh vượt quá giới hạn của Google Cloud TTS.
        
        Google Cloud TTS có 2 giới hạn:
        1. Tổng bytes: 5000 bytes mỗi request
        2. Độ dài câu: Mỗi câu không được quá dài (khuyến nghị < 150 ký tự để an toàn, đặc biệt với câu không có dấu câu)
        
        Args:
            text: Văn bản cần chia
            max_bytes: Số bytes tối đa mỗi chunk (mặc định: 4500 để an toàn)
            max_sentence_length: Độ dài tối đa mỗi câu (ký tự, mặc định: 150)
            
        Returns:
            Danh sách các chunks text
        """
        text_bytes = len(text.encode('utf-8'))
        
        # Kiểm tra xem text có dấu câu không
        import re
        has_punctuation = bool(re.search(r'[.!?。！？;:;,，]', text))
        
        # Nếu text không có dấu câu và quá dài (>= 150 ký tự), chia trực tiếp theo từ
        # Google Cloud TTS rất nhạy cảm với câu dài không có dấu câu
        if not has_punctuation and len(text) >= 150:
            return self._split_text_without_punctuation(text, max_bytes, max_sentence_length)
        
        if text_bytes <= max_bytes:
            # Kiểm tra xem có câu quá dài không
            sentences = self._split_into_sentences(text)
            if all(len(s.strip()) <= max_sentence_length for s in sentences if s.strip()):
                return [text]
        
        chunks = []
        current_chunk = ""
        
        # Chia text thành các phần nhỏ hơn theo nhiều dấu câu
        # Ưu tiên: dấu chấm > dấu chấm hỏi/chấm than > dấu phẩy > dấu chấm phẩy
        
        # Tách theo các dấu câu chính (., !, ?, ;, :, ,)
        # Giữ lại dấu câu trong kết quả
        parts = re.split(r'([.!?。！？;:;,，])', text)
        
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if not part:
                i += 1
                continue
            
            # Lấy dấu câu kèm theo (nếu có)
            punctuation = ""
            if i + 1 < len(parts) and parts[i + 1] in ['.', '!', '?', '。', '！', '？', ';', ':', ',', '，']:
                punctuation = parts[i + 1]
                i += 2
            else:
                i += 1
            
            # Thêm dấu câu vào phần text
            if punctuation:
                part += punctuation
            
            # Kiểm tra độ dài câu
            if len(part) > max_sentence_length:
                # Câu quá dài, chia nhỏ hơn theo dấu phẩy hoặc từ
                sub_parts = self._split_long_sentence(part, max_sentence_length)
                for sub_part in sub_parts:
                    test_chunk = current_chunk + " " + sub_part if current_chunk else sub_part
                    test_bytes = len(test_chunk.encode('utf-8'))
                    
                    if test_bytes <= max_bytes:
                        current_chunk = test_chunk
                    else:
                        # Lưu chunk hiện tại
                        if current_chunk:
                            chunks.append(current_chunk)
                        # Bắt đầu chunk mới
                        current_chunk = sub_part
            else:
                # Câu có độ dài hợp lý
                test_chunk = current_chunk + " " + part if current_chunk else part
                test_bytes = len(test_chunk.encode('utf-8'))
                
                if test_bytes <= max_bytes:
                    current_chunk = test_chunk
                else:
                    # Lưu chunk hiện tại
                    if current_chunk:
                        chunks.append(current_chunk)
                    # Bắt đầu chunk mới
                    current_chunk = part
        
        # Thêm chunk cuối cùng
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks if chunks else [text]
    
    def _split_into_sentences(self, text: str) -> list:
        """Tách text thành các câu."""
        import re
        # Tách theo dấu chấm, chấm hỏi, chấm than
        sentences = re.split(r'[.!?。！？]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _split_text_without_punctuation(self, text: str, max_bytes: int, max_sentence_length: int) -> list:
        """Chia text không có dấu câu thành các chunks nhỏ hơn.
        
        Args:
            text: Text không có dấu câu
            max_bytes: Số bytes tối đa mỗi chunk
            max_sentence_length: Độ dài tối đa mỗi câu (ký tự)
            
        Returns:
            Danh sách các chunks text
        """
        chunks = []
        words = text.split()
        current_chunk = ""
        
        for word in words:
            test_chunk = current_chunk + " " + word if current_chunk else word
            
            # Kiểm tra cả độ dài câu và bytes
            test_length = len(test_chunk)
            test_bytes = len(test_chunk.encode('utf-8'))
            
            if test_length <= max_sentence_length and test_bytes <= max_bytes:
                current_chunk = test_chunk
            else:
                # Lưu chunk hiện tại (thêm dấu chấm để tạo câu hợp lệ)
                if current_chunk:
                    chunks.append(current_chunk + ".")
                # Bắt đầu chunk mới
                current_chunk = word
        
        # Thêm chunk cuối cùng
        if current_chunk:
            chunks.append(current_chunk + ".")
        
        return chunks if chunks else [text]
    
    def _split_long_sentence(self, sentence: str, max_length: int) -> list:
        """Chia một câu quá dài thành nhiều phần nhỏ hơn.
        
        Ưu tiên chia theo dấu phẩy, sau đó theo từ.
        """
        parts = []
        
        # Thử chia theo dấu phẩy trước
        comma_parts = sentence.split(',')
        if len(comma_parts) > 1:
            current_part = ""
            for part in comma_parts:
                part = part.strip()
                if not part:
                    continue
                
                test_part = current_part + ", " + part if current_part else part
                if len(test_part) <= max_length:
                    current_part = test_part
                else:
                    if current_part:
                        parts.append(current_part)
                    current_part = part
            
            if current_part:
                parts.append(current_part)
            
            # Nếu vẫn còn phần quá dài, chia theo từ
            final_parts = []
            for part in parts:
                if len(part) <= max_length:
                    final_parts.append(part)
                else:
                    # Chia theo từ
                    words = part.split()
                    temp_part = ""
                    for word in words:
                        test_word = temp_part + " " + word if temp_part else word
                        if len(test_word) <= max_length:
                            temp_part = test_word
                        else:
                            if temp_part:
                                final_parts.append(temp_part + ".")
                            temp_part = word
                    if temp_part:
                        final_parts.append(temp_part + ".")
            return final_parts if final_parts else [sentence]
        else:
            # Không có dấu phẩy, chia theo từ
            words = sentence.split()
            current_part = ""
            for word in words:
                test_part = current_part + " " + word if current_part else word
                if len(test_part) <= max_length:
                    current_part = test_part
                else:
                    if current_part:
                        parts.append(current_part + ".")
                    current_part = word
            if current_part:
                parts.append(current_part + ".")
            return parts if parts else [sentence]
    
    def _concat_mp3_files(self, input_files: list, output_file: str) -> bool:
        """Nối nhiều file MP3 thành một file bằng ffmpeg.
        
        Args:
            input_files: Danh sách đường dẫn file MP3 đầu vào
            output_file: Đường dẫn file MP3 đầu ra
            
        Returns:
            True nếu thành công, False nếu không có ffmpeg hoặc lỗi
        """
        try:
            # Kiểm tra ffmpeg có sẵn không
            result = subprocess.run(
                ['which', 'ffmpeg'],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            # Tạo file list cho ffmpeg concat
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for input_file in input_files:
                    f.write(f"file '{os.path.abspath(input_file)}'\n")
                concat_list = f.name
            
            try:
                # Nối bằng ffmpeg
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_list,
                    '-c', 'copy',
                    '-y',
                    output_file
                ]
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                
                # Xóa file list tạm
                try:
                    os.remove(concat_list)
                except Exception:
                    pass
                
                return result.returncode == 0
            except Exception:
                # Xóa file list tạm
                try:
                    os.remove(concat_list)
                except Exception:
                    pass
                return False
        except Exception:
            return False
    
    async def speak(self, text: str, output_file: str, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Chuyển đổi text thành audio bằng Google Cloud TTS với retry mechanism.
        
        Quy trình:
        1. Chia text thành các chunks nhỏ hơn 5000 bytes (nếu cần)
        2. Synthesize từng chunk với retry
        3. Nối các audio chunks lại với nhau (nếu có ffmpeg)
        4. Xóa file tạm sau khi hoàn thành
        
        Args:
            text: Văn bản cần chuyển đổi
            output_file: Đường dẫn file audio đầu ra
            max_retries: Số lần retry tối đa (mặc định: 3)
            retry_delay: Thời gian chờ giữa các lần retry (giây, mặc định: 1.0)
        """
        if self.dry_run:
            print(f"[dry-run] GoogleCloudTTS would synthesize to {output_file} with language={self.language_code}, voice={self.voice_name}")
            return
        
        if not self.is_available():
            raise RuntimeError("Google Cloud TTS is not available. Check credentials and library installation.")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        if self.client is None:
            raise RuntimeError("Google Cloud TTS client not initialized")
        
        temp_files = []  # Danh sách file tạm cần xóa
        last_error = None
        
        try:
            # Retry logic với exponential backoff
            for attempt in range(max_retries):
                try:
                    # Xác định giọng đọc
                    voice_config = texttospeech.VoiceSelectionParams(
                        language_code=self.language_code,
                    )
                    
                    if self.voice_name:
                        voice_config.name = self.voice_name
                    
                    if self.ssml_gender:
                        if self.ssml_gender.upper() == 'FEMALE':
                            voice_config.ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
                        elif self.ssml_gender.upper() == 'MALE':
                            voice_config.ssml_gender = texttospeech.SsmlVoiceGender.MALE
                        else:
                            voice_config.ssml_gender = texttospeech.SsmlVoiceGender.NEUTRAL
                    
                    # Cấu hình audio
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3
                    )
                    
                    # Chia text thành chunks nếu quá dài (Google Cloud TTS giới hạn 5000 bytes và độ dài câu)
                    # max_sentence_length=150 để tránh lỗi "sentence too long" (an toàn hơn, đặc biệt với câu không có dấu câu)
                    text_chunks = self._split_text_into_chunks(text, max_bytes=4500, max_sentence_length=150)
                    
                    if len(text_chunks) > 1:
                        print(f"  Text quá dài ({len(text.encode('utf-8'))} bytes), chia thành {len(text_chunks)} chunks...")
                    
                    # Synthesize trong executor để không block event loop
                    # Sử dụng thread pool để tối ưu cho Google Cloud TTS
                    def _synthesize_all():
                        audio_chunks = []
                        
                        for i, chunk in enumerate(text_chunks, 1):
                            if len(text_chunks) > 1:
                                print(f"  Synthesizing chunk {i}/{len(text_chunks)}...")
                            
                            # Retry cho từng chunk
                            chunk_retries = max_retries
                            chunk_error = None
                            for chunk_attempt in range(chunk_retries):
                                try:
                                    synthesis_input = texttospeech.SynthesisInput(text=chunk)
                                    response = self.client.synthesize_speech(
                                        input=synthesis_input,
                                        voice=voice_config,
                                        audio_config=audio_config
                                    )
                                    audio_chunks.append(response.audio_content)
                                    chunk_error = None
                                    break  # Thành công, thoát retry loop
                                except Exception as chunk_exc:
                                    chunk_error = chunk_exc
                                    if chunk_attempt < chunk_retries - 1:
                                        # Exponential backoff: 1s, 2s, 4s...
                                        wait_time = retry_delay * (2 ** chunk_attempt)
                                        import time
                                        time.sleep(wait_time)
                                        print(f"  ⚠️  Chunk {i} failed (attempt {chunk_attempt + 1}/{chunk_retries}), retrying in {wait_time}s...")
                            
                            if chunk_error:
                                raise RuntimeError(f"Failed to synthesize chunk {i} after {chunk_retries} attempts: {chunk_error}")
                        
                        # Nối tất cả audio chunks lại
                        if len(audio_chunks) == 1:
                            # Chỉ có 1 chunk, lưu trực tiếp
                            with open(output_file, 'wb') as f:
                                f.write(audio_chunks[0])
                        else:
                            # Nhiều chunks, cần nối bằng ffmpeg
                            # Lưu các chunks tạm
                            for i, audio_data in enumerate(audio_chunks):
                                temp_file = f"{output_file}.chunk{i}.mp3"
                                with open(temp_file, 'wb') as f:
                                    f.write(audio_data)
                                temp_files.append(temp_file)
                            
                            # Nối bằng ffmpeg
                            if self._concat_mp3_files(temp_files, output_file):
                                print(f"  ✓ Đã nối {len(temp_files)} chunks thành công")
                            else:
                                # Nếu không có ffmpeg, lưu chunk đầu tiên và cảnh báo
                                print(f"⚠️  Warning: ffmpeg not available. Only first chunk saved to {output_file}")
                                print(f"   Install ffmpeg to concatenate all chunks: brew install ffmpeg")
                                with open(output_file, 'wb') as f:
                                    f.write(audio_chunks[0])
                    
                    # Sử dụng thread pool executor để tối ưu cho Google Cloud TTS
                    # Google Cloud client là thread-safe, có thể dùng chung
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, _synthesize_all)
                    
                    # Thành công, thoát retry loop
                    return
                    
                except Exception as exc:
                    last_error = exc
                    if attempt < max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s...
                        wait_time = retry_delay * (2 ** attempt)
                        print(f"⚠️  GoogleCloudTTS synthesis failed (attempt {attempt + 1}/{max_retries}): {exc}")
                        print(f"   Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Đã hết retry
                        raise RuntimeError(f"GoogleCloudTTS synthesis failed after {max_retries} attempts: {last_error}")
        finally:
            # Luôn xóa file tạm, kể cả khi có lỗi
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        print(f"  ✓ Đã xóa file tạm: {os.path.basename(temp_file)}")
                except Exception as e:
                    print(f"⚠️  Warning: Không thể xóa file tạm {temp_file}: {e}")


class FPTAITTS(BaseTTS):
    """FPT.AI TTS Engine - Online, chất lượng cao, cần API key.
    
    Sử dụng FPT.AI TTS API để chuyển text thành audio.
    Hỗ trợ nhiều giọng đọc tiếng Việt chất lượng cao.
    """
    
    def __init__(self, api_key: str, voice: str = 'banmai', dry_run: bool = False):
        """
        Args:
            api_key: FPT.AI API key (bắt buộc)
            voice: Tên giọng đọc (banmai, lannhi, leminh, giahuy)
            dry_run: Nếu True, chỉ in ra thông tin
        """
        super().__init__(voice=voice, dry_run=dry_run)
        self.api_key = api_key
    
    def is_available(self) -> bool:
        """Kiểm tra FPT.AI có sẵn không (cần requests và API key)."""
        return requests is not None and bool(self.api_key)
    
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio bằng FPT.AI TTS."""
        if self.dry_run:
            print(f"[dry-run] FPTAITTS would synthesize to {output_file} with voice={self.voice}")
            return
        
        if not self.is_available():
            raise RuntimeError("FPT.AI TTS requires requests library and API key")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        try:
            # Chạy request trong executor vì requests là blocking
            def _run_fpt_ai():
                url = "https://api.fpt.ai/hmi/tts/v5"
                headers = {
                    "api-key": self.api_key,
                    "voice": self.voice,
                    "speed": "0",  # -5 to 5, 0 is normal
                    "prosody": "1"  # 0-2, 1 is normal
                }
                data = text.encode('utf-8')
                
                response = requests.post(url, headers=headers, data=data, timeout=30)
                response.raise_for_status()
                
                with open(output_file, 'wb') as fh:
                    fh.write(response.content)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _run_fpt_ai)
            
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"FPT.AI TTS API request failed: {exc}")
        except Exception as exc:
            raise RuntimeError(f"FPTAITTS synthesis failed: {exc}")


class CoquiTTS(BaseTTS):
    """Coqui TTS Engine - Offline, mã nguồn mở, chất lượng cao.
    
    Sử dụng Coqui TTS (TTS library) để chuyển text thành audio.
    Hỗ trợ nhiều model, có thể chạy trên CPU hoặc GPU.
    """
    
    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
                 device: Optional[str] = None,
                 speaker_wav: Optional[str] = None,
                 language: str = "en",
                 dry_run: bool = False):
        """
        Args:
            model_name: Tên model Coqui TTS (mặc định: "tts_models/multilingual/multi-dataset/xtts_v2")
            device: Thiết bị chạy ('cpu', 'cuda', hoặc None để tự động)
            speaker_wav: Đường dẫn file audio mẫu cho voice cloning (bắt buộc với XTTS v2)
            language: Mã ngôn ngữ (mặc định: "en" vì XTTS v2 không hỗ trợ "vi")
            dry_run: Nếu True, chỉ in ra thông tin mà không thực sự convert
        
        Note:
            ⚠️  QUAN TRỌNG: XTTS v2 KHÔNG hỗ trợ tiếng Việt (language="vi")!
            Supported languages: ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']
            
            Model mặc định: "tts_models/multilingual/multi-dataset/xtts_v2" - Multilingual XTTS v2
            Model này KHÔNG hỗ trợ tiếng Việt, cần speaker_wav để clone giọng.
            
            💡 Khuyến nghị: Dùng backend khác cho tiếng Việt:
            - google-cloud: Hỗ trợ tiếng Việt tốt, ổn định
            - azure: Hỗ trợ tiếng Việt tốt, ổn định
            - macos: Offline, native Vietnamese voice
            
            Các model khác có thể dùng:
            - "tts_models/multilingual/multi-dataset/xtts_v2" (multilingual, KHÔNG hỗ trợ vi, cần speaker_wav)
            - "tts_models/en/ljspeech/tacotron2-DDC" (tiếng Anh)
        """
        super().__init__(voice=None, dry_run=dry_run)
        self.model_name = model_name
        self.device = device
        self.speaker_wav = speaker_wav
        self.language = language
        self.tts_instance: Optional[CoquiTTSAPI] = None
        
        if not self.dry_run:
            self._init_tts()
    
    def _init_tts(self) -> None:
        """Khởi tạo Coqui TTS instance."""
        if not COQUI_TTS_AVAILABLE:
            raise RuntimeError(
                "Coqui TTS library is not available. "
                "Install with: pip install TTS"
            )
        
        try:
            # Tự động chấp nhận license agreement để tránh prompt
            # Coqui TTS kiểm tra environment variable COQUI_TOS_AGREED
            if os.environ.get("COQUI_TOS_AGREED") != "1":
                os.environ["COQUI_TOS_AGREED"] = "1"
                print("  Auto-accepting Coqui TTS license agreement (COQUI_TOS_AGREED=1)")
            
            # Fix PyTorch 2.6 weights_only issue
            # PyTorch 2.6 changed default weights_only from False to True for security
            # Coqui TTS models need weights_only=False to load
            import torch
            original_load = torch.load
            def patched_load(*args, **kwargs):
                # Set weights_only=False if not explicitly provided
                if 'weights_only' not in kwargs:
                    kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            torch.load = patched_load
            
            # Xác định device
            if self.device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Khởi tạo TTS instance
            # Model sẽ được download tự động lần đầu tiên
            print(f"  Initializing Coqui TTS with model: {self.model_name}")
            print(f"  Device: {self.device}")
            # Khởi tạo TTS instance
            # Lưu ý: Không dùng .to() trong constructor, sẽ dùng sau
            self.tts_instance = CoquiTTSAPI(model_name=self.model_name, progress_bar=False)
            
            # Restore original torch.load after initialization
            torch.load = original_load
            # Move to device sau khi khởi tạo
            if self.device == 'cuda' and torch.cuda.is_available():
                self.tts_instance = self.tts_instance.to(self.device)
            else:
                self.device = 'cpu'  # Đảm bảo dùng CPU nếu không có CUDA
                self.tts_instance = self.tts_instance.to(self.device)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Coqui TTS: {e}")
    
    def is_available(self) -> bool:
        """Kiểm tra Coqui TTS có sẵn không."""
        if not COQUI_TTS_AVAILABLE:
            return False
        return self.tts_instance is not None or self.dry_run
    
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio bằng Coqui TTS.
        
        Args:
            text: Văn bản cần chuyển đổi
            output_file: Đường dẫn file audio đầu ra (thường là .wav)
        """
        if self.dry_run:
            print(f"[dry-run] CoquiTTS would synthesize to {output_file} with model={self.model_name}, device={self.device}")
            return
        
        if not self.is_available():
            raise RuntimeError("Coqui TTS is not available. Check library installation.")
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        if self.tts_instance is None:
            raise RuntimeError("Coqui TTS instance not initialized")
        
        try:
            # Coqui TTS thường xuất file .wav
            # Nếu output_file là .mp3, cần convert sau
            output_wav = output_file
            need_convert = False
            
            if output_file.endswith('.mp3'):
                # Tạo file .wav tạm
                output_wav = output_file.replace('.mp3', '.wav')
                need_convert = True
            
            # Synthesize trong executor để không block event loop
            def _synthesize():
                # XTTS v2 cần speaker_wav và language
                if 'xtts' in self.model_name.lower():
                    if not self.speaker_wav:
                        raise RuntimeError(
                            f"Model {self.model_name} requires speaker_wav parameter for voice cloning. "
                            "Please provide a reference audio file."
                        )
                    
                    # Kiểm tra language có được hỗ trợ không
                    # XTTS v2 không hỗ trợ "vi" (tiếng Việt)
                    supported_languages = ['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']
                    if self.language not in supported_languages:
                        raise RuntimeError(
                            f"Language '{self.language}' is not supported by XTTS v2. "
                            f"Supported languages: {supported_languages}. "
                            f"⚠️  XTTS v2 does NOT support Vietnamese (vi). "
                            f"Please use another backend (google-cloud, azure, macos) for Vietnamese text."
                        )
                    
                    self.tts_instance.tts_to_file(
                        text=text,
                        file_path=output_wav,
                        speaker_wav=self.speaker_wav,
                        language=self.language
                    )
                else:
                    # Model khác không cần speaker_wav
                    self.tts_instance.tts_to_file(text=text, file_path=output_wav)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _synthesize)
            
            # Convert WAV sang MP3 nếu cần
            if need_convert:
                if self._convert_wav_to_mp3(output_wav, output_file):
                    # Xóa file WAV tạm
                    try:
                        os.remove(output_wav)
                    except Exception:
                        pass
                else:
                    # Nếu không convert được, giữ file WAV và cảnh báo
                    print(f"⚠️  Warning: Could not convert WAV to MP3. Output saved as: {output_wav}")
                    print(f"   Install ffmpeg to convert: brew install ffmpeg")
            
        except Exception as exc:
            raise RuntimeError(f"CoquiTTS synthesis failed: {exc}")
    
    def _convert_wav_to_mp3(self, wav_path: str, mp3_path: str) -> bool:
        """Convert WAV sang MP3 bằng ffmpeg.
        
        Args:
            wav_path: Đường dẫn file WAV
            mp3_path: Đường dẫn file MP3 đầu ra
            
        Returns:
            True nếu thành công, False nếu không có ffmpeg hoặc lỗi
        """
        try:
            # Kiểm tra ffmpeg có sẵn không
            result = subprocess.run(
                ['which', 'ffmpeg'],
                capture_output=True,
                timeout=2
            )
            if result.returncode != 0:
                return False
            
            # Convert bằng ffmpeg
            cmd = [
                'ffmpeg',
                '-i', wav_path,
                '-codec:a', 'libmp3lame',
                '-q:a', '2',  # Quality: 0-9, 2 là tốt
                '-y',  # Overwrite output file
                mp3_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False


class AzureTTS(BaseTTS):
    """Azure Text-to-Speech Engine - Online, chất lượng cao, ổn định, cần credentials.
    
    Sử dụng Azure Cognitive Services Speech SDK để chuyển text thành audio.
    Yêu cầu Azure subscription key và region.
    
    Azure TTS và Edge TTS sử dụng cùng giọng nói Microsoft, nhưng Azure TTS:
    - Ổn định hơn (có SLA 99.9%)
    - Có free tier (0-500K ký tự/tháng)
    - Có support từ Microsoft
    - Rate limiting rõ ràng
    """
    
    def __init__(self, subscription_key: Optional[str] = None,
                 region: str = 'eastus',
                 voice_name: str = 'vi-VN-HoaiMyNeural',
                 dry_run: bool = False):
        """
        Args:
            subscription_key: Azure subscription key (bắt buộc)
            region: Azure region (mặc định: 'eastus')
            voice_name: Tên giọng đọc (mặc định: 'vi-VN-HoaiMyNeural')
            dry_run: Nếu True, chỉ in ra thông tin mà không thực sự convert
        
        Note:
            Subscription key có thể được set qua:
            - subscription_key parameter
            - Environment variable: AZURE_SPEECH_KEY
            Region có thể được set qua:
            - region parameter
            - Environment variable: AZURE_SPEECH_REGION
        
        Giọng nói tiếng Việt phổ biến:
            - vi-VN-HoaiMyNeural (Nữ)
            - vi-VN-NamMinhNeural (Nam)
        """
        super().__init__(voice=voice_name, dry_run=dry_run)
        
        # Lấy subscription key từ parameter hoặc env var
        if subscription_key:
            self.subscription_key = subscription_key
        else:
            import os
            self.subscription_key = os.getenv('AZURE_SPEECH_KEY')
        
        # Lấy region từ parameter hoặc env var
        if region:
            self.region = region
        else:
            import os
            self.region = os.getenv('AZURE_SPEECH_REGION', 'eastus')
        
        self.voice_name = voice_name
        
        if not self.subscription_key and not self.dry_run:
            raise ValueError(
                "Azure TTS requires subscription_key. "
                "Provide it via parameter or set AZURE_SPEECH_KEY environment variable."
            )
    
    def is_available(self) -> bool:
        """Kiểm tra Azure TTS có sẵn không."""
        if not AZURE_TTS_AVAILABLE:
            return False
        return self.subscription_key is not None or self.dry_run
    
    async def speak(self, text: str, output_file: str, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        """Chuyển đổi text thành audio bằng Azure TTS với retry mechanism.
        
        Args:
            text: Văn bản cần chuyển đổi
            output_file: Đường dẫn file audio đầu ra
            max_retries: Số lần retry tối đa (mặc định: 3)
            retry_delay: Thời gian chờ giữa các lần retry (giây, mặc định: 1.0)
        """
        if self.dry_run:
            print(f"[dry-run] AzureTTS would synthesize to {output_file} with voice={self.voice_name}, region={self.region}")
            return
        
        if not self.is_available():
            raise RuntimeError(
                "Azure TTS is not available. "
                "Install with: pip install azure-cognitiveservices-speech"
            )
        
        if not text.strip():
            raise RuntimeError("Input text is empty")
        
        if not self.subscription_key:
            raise RuntimeError("Azure TTS subscription key not provided")
        
        # Azure TTS limit: ~10,000 characters per request (SSML) or ~5,000 for plain text
        # We'll use 4,000 characters per chunk to be safe
        max_chunk_size = 4000
        
        last_error = None
        
        # Đảm bảo output directory tồn tại và sử dụng absolute path
        output_path = Path(output_file)
        output_dir = output_path.parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        absolute_output_file = str(output_path.absolute())
        
        # Chia text thành chunks nếu quá dài
        text_chunks = []
        if len(text) > max_chunk_size:
            # Chia text theo câu (ưu tiên dấu chấm, chấm hỏi, chấm than)
            import re
            sentences = re.split(r'([.!?。！？])', text)
            current_chunk = ""
            for i in range(0, len(sentences), 2):
                sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                if len(current_chunk) + len(sentence) <= max_chunk_size:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        text_chunks.append(current_chunk)
                    current_chunk = sentence
            if current_chunk:
                text_chunks.append(current_chunk)
        else:
            text_chunks = [text]
        
        # Retry logic với exponential backoff
        for attempt in range(max_retries):
            try:
                # Chạy synthesize trong executor để không block event loop
                def _synthesize():
                    # Validate inputs
                    if not self.subscription_key or len(self.subscription_key.strip()) == 0:
                        raise ValueError("Azure subscription key is empty or invalid")
                    if not self.voice_name or len(self.voice_name.strip()) == 0:
                        raise ValueError("Azure voice name is empty or invalid")
                    
                    # Cấu hình speech config
                    try:
                    speech_config = speechsdk.SpeechConfig(
                        subscription=self.subscription_key,
                        region=self.region
                    )
                    except Exception as config_exc:
                        raise RuntimeError(
                            f"Failed to create SpeechConfig: {config_exc}\n"
                            "Please verify:\n"
                            "  1. Your Azure subscription key is valid and not expired\n"
                            "  2. The Speech service is enabled in your Azure account\n"
                            "  3. The region matches your Speech service resource region"
                        )
                    
                    speech_config.speech_synthesis_voice_name = self.voice_name
                    
                    # Set audio format to MP3 - try different methods
                    try:
                        # Method 1: Try using set_speech_synthesis_output_format
                        if hasattr(speech_config, 'set_speech_synthesis_output_format'):
                            # Check if the enum exists
                            if hasattr(speechsdk, 'SpeechSynthesisOutputFormat'):
                                format_enum = getattr(speechsdk.SpeechSynthesisOutputFormat, 'Audio16Khz128KBitRateMonoMp3', None)
                                if format_enum is not None:
                                    speech_config.set_speech_synthesis_output_format(format_enum)
                    except Exception as format_exc:
                        # If format setting fails, Azure should auto-detect from .mp3 extension
                        pass
                    
                    # Cấu hình audio output với absolute path
                    audio_config = speechsdk.audio.AudioOutputConfig(filename=absolute_output_file)
                    
                    # Tạo synthesizer
                    synthesizer = speechsdk.SpeechSynthesizer(
                        speech_config=speech_config,
                        audio_config=audio_config
                    )
                    
                    # Synthesize (handle multiple chunks if needed)
                    if len(text_chunks) == 1:
                        # Single chunk - simple case
                        result = synthesizer.speak_text_async(text_chunks[0]).get()
                        # Check result immediately for single chunk
                        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                            error_msg = f"Azure TTS failed: {result.reason}"
                            if result.reason == speechsdk.ResultReason.Canceled:
                                try:
                                    cancellation = speechsdk.CancellationDetails(result)
                                    error_msg += f" (Canceled: {cancellation.reason})"
                                    if cancellation.reason == speechsdk.CancellationReason.Error:
                                        if hasattr(cancellation, 'error_details') and cancellation.error_details:
                                            error_msg += f" - {cancellation.error_details}"
                                        if hasattr(cancellation, 'error_code'):
                                            error_msg += f" (Error code: {cancellation.error_code})"
                                except Exception as cancel_exc:
                                    error_msg += f" (Could not get cancellation details: {cancel_exc})"
                            raise RuntimeError(error_msg)
                    else:
                        # Multiple chunks - synthesize each and concatenate
                        temp_files = []
                        try:
                            for i, chunk in enumerate(text_chunks):
                                temp_file = f"{absolute_output_file}.part_{i}.mp3"
                                temp_audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_file)
                                temp_synthesizer = speechsdk.SpeechSynthesizer(
                                    speech_config=speech_config,
                                    audio_config=temp_audio_config
                                )
                                chunk_result = temp_synthesizer.speak_text_async(chunk).get()
                                if chunk_result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
                                    # Get cancellation details with comprehensive error information
                                    error_msg = f"Chunk {i+1} failed: {chunk_result.reason}"
                                    if chunk_result.reason == speechsdk.ResultReason.Canceled:
                                        # Try to get cancellation details, but handle the case where it fails
                                        cancellation_info = ""
                                        try:
                                            cancellation = speechsdk.CancellationDetails(chunk_result)
                                            cancellation_info = f" | Cancellation reason: {cancellation.reason}"
                                            if cancellation.reason == speechsdk.CancellationReason.Error:
                                                error_details = getattr(cancellation, 'error_details', None)
                                                error_code = getattr(cancellation, 'error_code', None)
                                                if error_code:
                                                    cancellation_info += f" | Error code: {error_code}"
                                                    # Common error codes and their meanings
                                                    if error_code == 0x5:  # SPXERR_INVALID_ARG
                                                        cancellation_info += " (SPXERR_INVALID_ARG - Invalid argument. Check subscription key, region, voice name, or audio format)"
                                                if error_details:
                                                    cancellation_info += f" | Error details: {error_details}"
                                                if not error_details and not error_code:
                                                    cancellation_info += " | No additional error details available"
                                            elif cancellation.reason == speechsdk.CancellationReason.EndOfStream:
                                                cancellation_info += " | End of stream reached"
                                        except Exception as cancel_exc:
                                            # If we can't get cancellation details, provide troubleshooting info
                                            cancellation_info = f" | Could not get cancellation details (this often indicates invalid subscription key or region)"
                                            cancellation_info += f"\n   Troubleshooting:\n"
                                            cancellation_info += f"   1. Verify your Azure subscription key is valid and not expired\n"
                                            cancellation_info += f"   2. Ensure the Speech service is enabled in your Azure account\n"
                                            cancellation_info += f"   3. Check that the region '{self.region}' matches your Speech service resource\n"
                                            cancellation_info += f"   4. Verify the voice name '{self.voice_name}' is available in your region"
                                        error_msg += cancellation_info
                                    raise RuntimeError(error_msg)
                                temp_files.append(temp_file)
                            
                            # Concatenate audio files using ffmpeg if available
                            if len(temp_files) > 1:
                                # Try to concatenate
                                from crawler.converter import TextToAudioConverter
                                # Use a simple approach: check if ffmpeg is available
                                import subprocess
                                ffmpeg_available = subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0
                                if ffmpeg_available:
                                    # Create concat file list
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                                        for temp_file in temp_files:
                                            f.write(f"file '{os.path.abspath(temp_file)}'\n")
                                        concat_list = f.name
                                    
                                    try:
                                        cmd = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_list, '-c', 'copy', '-y', absolute_output_file]
                                        subprocess.run(cmd, capture_output=True, check=True)
                                    finally:
                                        try:
                                            os.remove(concat_list)
                                        except:
                                            pass
                                else:
                                    # No ffmpeg - just use first chunk
                                    import shutil
                                    shutil.copy(temp_files[0], absolute_output_file)
                            
                            # Clean up temp files
                            for temp_file in temp_files:
                                try:
                                    if os.path.exists(temp_file):
                                        os.remove(temp_file)
                                except:
                                    pass
                            
                            result = type('obj', (object,), {'reason': speechsdk.ResultReason.SynthesizingAudioCompleted})()
                        except Exception as chunk_exc:
                            # Clean up temp files on error
                            for temp_file in temp_files:
                                try:
                                    if os.path.exists(temp_file):
                                        os.remove(temp_file)
                                except:
                                    pass
                            raise chunk_exc
                    
                    # Kiểm tra kết quả
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        return True
                    elif result.reason == speechsdk.ResultReason.Canceled:
                        try:
                        cancellation = speechsdk.CancellationDetails(result)
                        error_msg = f"Azure TTS canceled: {cancellation.reason}"
                        if cancellation.reason == speechsdk.CancellationReason.Error:
                                if hasattr(cancellation, 'error_details') and cancellation.error_details:
                            error_msg += f" - {cancellation.error_details}"
                                if hasattr(cancellation, 'error_code'):
                                    error_msg += f" (Error code: {cancellation.error_code})"
                        except Exception as cancel_exc:
                            # If we can't get cancellation details, use a generic error
                            error_msg = f"Azure TTS canceled (could not get details: {cancel_exc})"
                        raise RuntimeError(error_msg)
                    else:
                        raise RuntimeError(f"Azure TTS synthesis failed: {result.reason}")
                
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, _synthesize)
                
                if success:
                    # Kiểm tra file đã được tạo (sử dụng absolute path)
                    if os.path.exists(absolute_output_file) and os.path.getsize(absolute_output_file) > 0:
                        return  # Thành công
                    else:
                        raise RuntimeError("Audio file was not created or is empty")
                
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s...
                    wait_time = retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                else:
                    # Lần thử cuối cùng thất bại
                    raise RuntimeError(f"AzureTTS synthesis failed after {max_retries} attempts: {last_error}")
        
        # Không nên đến đây, nhưng để an toàn
        raise RuntimeError(f"AzureTTS synthesis failed: {last_error}")


class TTSManager:
    """Factory/Manager class để quản lý và tạo TTS engines.
    
    Hỗ trợ:
    - Tạo engine dựa trên tên
    - Fallback tự động khi engine chính lỗi
    - Quản lý cấu hình engines
    """
    
    # Mapping tên engine -> class
    ENGINE_CLASSES = {
        'edge-tts': EdgeTTS,
        'macos': MacOSTTS,
        'gtts': GTTS,
        'fpt-ai': FPTAITTS,
        'piper': PiperTTS,
        'google-cloud': GoogleCloudTTS,
        'coqui': CoquiTTS,
        'azure': AzureTTS,
    }
    
    @classmethod
    def create_engine(cls, engine_name: str, **kwargs) -> BaseTTS:
        """Tạo TTS engine dựa trên tên.
        
        Args:
            engine_name: Tên engine ('edge-tts', 'macos', 'gtts', 'fpt-ai')
            **kwargs: Các tham số cho engine (voice, rate, api_key, etc.)
            
        Returns:
            Instance của BaseTTS
            
        Raises:
            ValueError: Nếu engine_name không hợp lệ
        """
        if engine_name not in cls.ENGINE_CLASSES:
            available = ', '.join(cls.ENGINE_CLASSES.keys())
            raise ValueError(f"Unknown engine: {engine_name}. Available: {available}")
        
        engine_class = cls.ENGINE_CLASSES[engine_name]
        return engine_class(**kwargs)
    
    @classmethod
    def create_with_fallback(cls, primary_engine: str, fallback_engines: list = None, **kwargs) -> BaseTTS:
        """Tạo engine với khả năng fallback tự động.
        
        Args:
            primary_engine: Engine chính
            fallback_engines: Danh sách engine dự phòng (mặc định: ['macos', 'gtts'])
            **kwargs: Các tham số cho engine
            
        Returns:
            Wrapper engine có khả năng fallback
        """
        if fallback_engines is None:
            fallback_engines = ['macos', 'gtts']
        
        return FallbackTTS(primary_engine, fallback_engines, **kwargs)
    
    @classmethod
    def list_available_engines(cls) -> list:
        """Liệt kê các engine có sẵn (đã cài đặt và có thể sử dụng).
        
        Returns:
            Danh sách tên engine có sẵn
        """
        available = []
        for name, engine_class in cls.ENGINE_CLASSES.items():
            # Tạo instance tạm để kiểm tra
            try:
                if name == 'fpt-ai':
                    # FPT.AI cần API key
                    engine = engine_class(api_key='test', **{})
                elif name == 'piper':
                    # Piper cần model path, bỏ qua nếu không có
                    continue
                elif name == 'google-cloud':
                    # Google Cloud cần credentials, bỏ qua nếu không có
                    continue
                else:
                    engine = engine_class(**{})
                if engine.is_available():
                    available.append(name)
            except Exception:
                pass
        return available


class FallbackTTS(BaseTTS):
    """Wrapper TTS engine có khả năng fallback tự động.
    
    Nếu engine chính lỗi, sẽ tự động thử engine dự phòng.
    """
    
    def __init__(self, primary_engine: str, fallback_engines: list, **kwargs):
        """
        Args:
            primary_engine: Tên engine chính
            fallback_engines: Danh sách engine dự phòng
            **kwargs: Các tham số cho engines
        """
        super().__init__(voice=None, dry_run=kwargs.get('dry_run', False))
        self.primary_engine = primary_engine
        self.fallback_engines = fallback_engines
        self.kwargs = kwargs
        
        # Tạo engine chính
        self.primary = TTSManager.create_engine(primary_engine, **kwargs)
        self.primary.dry_run = self.dry_run
        
        # Tạo engines dự phòng
        self.fallbacks = []
        for fallback_name in fallback_engines:
            try:
                fallback = TTSManager.create_engine(fallback_name, **kwargs)
                fallback.dry_run = self.dry_run
                if fallback.is_available():
                    self.fallbacks.append(fallback)
            except Exception:
                pass
    
    def is_available(self) -> bool:
        """Kiểm tra có ít nhất một engine khả dụng không."""
        if self.primary.is_available():
            return True
        return any(fb.is_available() for fb in self.fallbacks)
    
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio với fallback tự động."""
        last_error = None
        
        # Thử engine chính trước
        if self.primary.is_available():
            try:
                await self.primary.speak(text, output_file)
                return
            except Exception as e:
                last_error = e
                print(f"⚠️  Primary engine '{self.primary_engine}' failed: {e}")
                print(f"   Trying fallback engines...")
        
        # Thử các engine dự phòng
        for fallback in self.fallbacks:
            if fallback.is_available():
                try:
                    print(f"   Trying fallback: {type(fallback).__name__}...")
                    await fallback.speak(text, output_file)
                    print(f"✓ Fallback engine succeeded!")
                    return
                except Exception as e:
                    last_error = e
                    print(f"   Fallback failed: {e}")
        
        # Tất cả đều thất bại
        raise RuntimeError(f"All TTS engines failed. Last error: {last_error}")

