#!/usr/bin/env python3
"""Script để tạo sample audio dài ~20s cho tất cả các giọng đọc Google Cloud TTS tiếng Việt.
Sau đó convert sang WAV và lưu vào thư mục chỉ định."""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from google.cloud import texttospeech

# Text mẫu dài ~20 giây (khoảng 200-300 ký tự)
SAMPLE_TEXT = """Xin chào các bạn, đây là một đoạn văn bản mẫu để thử nghiệm giọng đọc của Google Cloud Text-to-Speech. 
Tôi đang kiểm tra chất lượng giọng nói, độ tự nhiên và cách phát âm tiếng Việt. 
Đây là một công cụ rất hữu ích để tạo ra các file audio từ văn bản một cách nhanh chóng và chính xác. 
Giọng nói này có thể được sử dụng trong nhiều ứng dụng khác nhau như đọc sách, podcast, hoặc các video hướng dẫn."""

# Đường dẫn credentials
CREDENTIALS_PATH = "credentials/geometric-rex-370803-ef593306e755.json"


def get_all_voices(credentials_path: str = None):
    """Lấy danh sách tất cả các voices tiếng Việt."""
    if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    elif CREDENTIALS_PATH:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices(language_code='vi-VN')
    return voices.voices


def synthesize_voice(voice_name: str, output_file: str, text: str = SAMPLE_TEXT, credentials_path: str = None):
    """Tạo audio sample cho một voice.
    
    Args:
        voice_name: Tên voice
        output_file: Đường dẫn file output (MP3)
        text: Text cần synthesize (mặc định: SAMPLE_TEXT)
        credentials_path: Đường dẫn credentials (mặc định: CREDENTIALS_PATH)
    
    Returns:
        file_size hoặc None nếu lỗi
    """
    if credentials_path:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    elif CREDENTIALS_PATH:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
    client = texttospeech.TextToSpeechClient()
    
    # Cấu hình voice
    voice_config = texttospeech.VoiceSelectionParams(
        language_code='vi-VN',
        name=voice_name
    )
    
    # Cấu hình audio
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    # Chia text thành chunks nếu quá dài (Google Cloud TTS giới hạn 5000 bytes)
    text_bytes = len(text.encode('utf-8'))
    if text_bytes > 4500:
        # Chia text thành nhiều chunks
        chunks = []
        current_chunk = ""
        sentences = text.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence += '.'
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            if len(test_chunk.encode('utf-8')) <= 4500:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
        if current_chunk:
            chunks.append(current_chunk)
    else:
        chunks = [text]
    
    # Synthesize từng chunk và nối lại
    audio_chunks = []
    for chunk in chunks:
        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_config,
            audio_config=audio_config
        )
        audio_chunks.append(response.audio_content)
    
    # Nối các chunks lại
    if len(audio_chunks) == 1:
        audio_content = audio_chunks[0]
    else:
        # Lưu các chunks tạm và nối bằng ffmpeg
        import tempfile
        temp_files = []
        try:
            for i, chunk_data in enumerate(audio_chunks):
                temp_file = f"{output_file}.chunk{i}.mp3"
                with open(temp_file, 'wb') as f:
                    f.write(chunk_data)
                temp_files.append(temp_file)
            
            # Nối bằng ffmpeg
            if _concat_mp3_files(temp_files, output_file):
                # Đã nối thành công
                file_size = os.path.getsize(output_file)
                return file_size
            else:
                # Nếu không có ffmpeg, lưu chunk đầu tiên
                audio_content = audio_chunks[0]
        finally:
            # Xóa file tạm
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
    
    # Lưu file
    with open(output_file, 'wb') as f:
        f.write(audio_content)
    
    file_size = os.path.getsize(output_file)
    return file_size


def _concat_mp3_files(input_files: list, output_file: str) -> bool:
    """Nối nhiều file MP3 thành một file bằng ffmpeg."""
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
            return result.returncode == 0
        finally:
            # Xóa file list tạm
            try:
                os.remove(concat_list)
            except Exception:
                pass
    except Exception:
        return False


def convert_mp3_to_wav(mp3_path: str, wav_path: str) -> bool:
    """Convert MP3 sang WAV bằng ffmpeg.
    
    Args:
        mp3_path: Đường dẫn file MP3
        wav_path: Đường dẫn file WAV đầu ra
    
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
            '-i', mp3_path,
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '22050',  # Sample rate 22050 Hz (hoặc 44100)
            '-ac', '1',  # Mono
            '-y',  # Overwrite output file
            wav_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        return result.returncode == 0
    except Exception as e:
        print(f"  ⚠️  Error converting to WAV: {e}")
        return False


def main():
    """Hàm chính."""
    parser = argparse.ArgumentParser(description="Tạo voice samples dài ~20s và convert sang WAV")
    parser.add_argument("--output-dir", default="voice_samples", help="Thư mục lưu samples (mặc định: voice_samples)")
    parser.add_argument("--wav-dir", help="Thư mục lưu file WAV (nếu không chỉ định, sẽ lưu cùng thư mục MP3)")
    parser.add_argument("--credentials", default=CREDENTIALS_PATH, help="Đường dẫn credentials JSON")
    parser.add_argument("--text", help="Text mẫu tùy chỉnh (mặc định: text dài ~20s)")
    parser.add_argument("--mp3-only", action='store_true', help="Chỉ tạo MP3, không convert sang WAV")
    args = parser.parse_args()
    
    # Sử dụng credentials và text từ args
    credentials_path = args.credentials
    sample_text = args.text if args.text else SAMPLE_TEXT
    
    # Tạo thư mục output
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Thư mục WAV
    wav_path = Path(args.wav_dir) if args.wav_dir else output_path
    wav_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Đang lấy danh sách voices...")
    # Tạm thời set credentials để lấy voices
    original_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    voices = get_all_voices()
    if original_creds:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = original_creds
    print(f"Tìm thấy {len(voices)} voices\n")
    
    print(f"Bắt đầu tạo samples (~20s mỗi voice)...")
    print(f"Text mẫu ({len(sample_text)} ký tự): '{sample_text[:100]}...'\n")
    
    success_count = 0
    error_count = 0
    wav_count = 0
    
    # Kiểm tra ffmpeg
    has_ffmpeg = subprocess.run(['which', 'ffmpeg'], capture_output=True).returncode == 0
    if not args.mp3_only and not has_ffmpeg:
        print("⚠️  Warning: ffmpeg not found. Cannot convert to WAV.")
        print("   Install with: brew install ffmpeg")
        print("   Will only create MP3 files.\n")
    
    for i, voice in enumerate(voices, 1):
        voice_name = voice.name
        # File MP3
        mp3_file = output_path / f"{voice_name}.mp3"
        # File WAV
        wav_file = wav_path / f"{voice_name}.wav"
        
        # Bỏ qua nếu cả MP3 và WAV đã tồn tại
        if mp3_file.exists() and (args.mp3_only or wav_file.exists()):
            print(f"[{i}/{len(voices)}] ⏭️  Đã tồn tại: {voice_name}")
            continue
        
        try:
            # Tạo MP3
            if not mp3_file.exists():
                print(f"[{i}/{len(voices)}] 🎤 Đang tạo MP3: {voice_name}...", end=' ', flush=True)
                file_size = synthesize_voice(voice_name, str(mp3_file), text=sample_text, credentials_path=credentials_path)
                if file_size:
                    print(f"✓ ({file_size:,} bytes)")
                    success_count += 1
                else:
                    print("✗ Failed")
                    error_count += 1
                    continue
            else:
                print(f"[{i}/{len(voices)}] 🎤 MP3 đã có, đang convert: {voice_name}...", end=' ', flush=True)
            
            # Convert sang WAV
            if not args.mp3_only and has_ffmpeg:
                if not wav_file.exists():
                    if convert_mp3_to_wav(str(mp3_file), str(wav_file)):
                        wav_size = os.path.getsize(wav_file)
                        print(f"✓ WAV ({wav_size:,} bytes)")
                        wav_count += 1
                    else:
                        print("⚠️  MP3 created but WAV conversion failed")
                else:
                    print("✓ WAV đã tồn tại")
            elif not args.mp3_only:
                print("⚠️  (skipped WAV - no ffmpeg)")
            
        except Exception as e:
            print(f"✗ Lỗi: {e}")
            error_count += 1
            # Xóa file nếu có lỗi
            if mp3_file.exists():
                try:
                    mp3_file.unlink()
                except Exception:
                    pass
            if wav_file.exists():
                try:
                    wav_file.unlink()
                except Exception:
                    pass
    
    print(f"\n{'='*60}")
    print(f"Hoàn thành!")
    print(f"  ✓ MP3 thành công: {success_count}/{len(voices)}")
    if not args.mp3_only:
        print(f"  ✓ WAV thành công: {wav_count}/{len(voices)}")
    print(f"  ✗ Lỗi: {error_count}/{len(voices)}")
    print(f"  📁 Thư mục MP3: {output_path.absolute()}")
    if not args.mp3_only:
        print(f"  📁 Thư mục WAV: {wav_path.absolute()}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()

