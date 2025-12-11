# Hướng dẫn sử dụng hệ thống TTS đa phương thức (Multi-Engine TTS)

## Tổng quan

Hệ thống đã được refactor theo **Strategy Pattern** để hỗ trợ nhiều TTS engines:
- **edge-tts**: Microsoft Edge TTS (online, chất lượng cao)
- **macos**: macOS native TTS sử dụng lệnh `say` (offline, chỉ trên macOS)
- **gtts**: Google Text-to-Speech (online, miễn phí, đơn giản)
- **fpt-ai**: FPT.AI TTS (online, chất lượng cao, cần API key)

## Cấu trúc code

### 1. BaseTTS (Abstract Base Class)

File: `crawler/tts_engines.py`

Tất cả TTS engines kế thừa từ `BaseTTS` và implement method `speak(text, output_file)`:

```python
class BaseTTS(ABC):
    @abstractmethod
    async def speak(self, text: str, output_file: str) -> None:
        """Chuyển đổi text thành audio file."""
        pass
```

### 2. Các Engine Classes

- `EdgeTTS`: Microsoft Edge TTS
- `MacOSTTS`: macOS native TTS
- `GTTS`: Google Text-to-Speech
- `FPTAITTS`: FPT.AI TTS

### 3. TTSManager (Factory)

Quản lý và tạo engines:

```python
from crawler.tts_engines import TTSManager

# Tạo engine đơn lẻ
engine = TTSManager.create_engine('macos', voice='Linh')

# Tạo engine với fallback tự động
engine = TTSManager.create_with_fallback(
    primary_engine='edge-tts',
    fallback_engines=['macos', 'gtts'],
    voice='vi-VN-NamMinhNeural'
)
```

## Cách sử dụng

### 1. Sử dụng với run.py

#### Cấu hình trong config.json:

```json
{
  "tts_backend": "macos",
  "macos_voice": "Linh",
  "enable_tts_fallback": false,
  "fallback_engines": ["macos", "gtts"]
}
```

#### Chạy từ command line:

```bash
# Sử dụng macOS TTS
python3 run.py --config config.json --tts-backend macos

# Sử dụng edge-tts với fallback tự động
python3 run.py --config config.json --tts-backend edge-tts

# Với fallback enabled trong config
# Nếu edge-tts lỗi, sẽ tự động fallback sang macos hoặc gtts
```

### 2. Sử dụng với TextToAudioConverter

```python
from crawler.converter import TextToAudioConverter

# macOS TTS
converter = TextToAudioConverter(
    backend='macos',
    macos_voice='Linh',
    dry_run=False
)
converter.convert('input.txt', 'output.m4a')

# Edge TTS với fallback
converter = TextToAudioConverter(
    backend='edge-tts',
    edge_rate=1.0,
    enable_fallback=True,
    fallback_engines=['macos', 'gtts']
)
converter.convert('input.txt', 'output.mp3')
```

### 3. Sử dụng trực tiếp với TTS engines

```python
from crawler.tts_engines import MacOSTTS, EdgeTTS, TTSManager
import asyncio

# Cách 1: Tạo engine trực tiếp
macos = MacOSTTS(voice='Linh')
asyncio.run(macos.speak('Xin chào', 'output.m4a'))

# Cách 2: Sử dụng TTSManager
engine = TTSManager.create_engine('macos', voice='Linh')
asyncio.run(engine.speak('Xin chào', 'output.m4a'))

# Cách 3: Với fallback tự động
engine = TTSManager.create_with_fallback(
    primary_engine='edge-tts',
    fallback_engines=['macos', 'gtts']
)
asyncio.run(engine.speak('Xin chào', 'output.mp3'))
```

## macOS TTS - Chi tiết

### Giọng đọc có sẵn

Liệt kê các giọng đọc:

```python
from crawler.tts_engines import MacOSTTS

macos = MacOSTTS()
voices = macos.list_voices()
print(voices)
```

Giọng đọc tiếng Việt phổ biến:
- **Linh**: Nữ, miền Bắc (mặc định)
- **Nam**: Nam, miền Bắc

### Format output

macOS `say` command xuất file `.m4a` hoặc `.aiff` mặc định. Nếu bạn chỉ định `.mp3`, hệ thống sẽ:
1. Tạo file `.m4a` trước
2. Tự động convert sang `.mp3` bằng `ffmpeg` (nếu có)
3. Nếu không có `ffmpeg`, sẽ giữ file `.m4a`

**Khuyến nghị**: Sử dụng `.m4a` để tránh cần convert.

### Ví dụ

```python
from crawler.converter import TextToAudioConverter

converter = TextToAudioConverter(
    backend='macos',
    macos_voice='Linh'
)

# Xuất file .m4a (khuyến nghị)
converter.convert('chapter.txt', 'chapter.m4a')

# Xuất file .mp3 (sẽ tự động convert nếu có ffmpeg)
converter.convert('chapter.txt', 'chapter.mp3')
```

## Fallback tự động

Khi `enable_fallback=True`, nếu engine chính lỗi, hệ thống sẽ tự động thử các engine dự phòng:

```python
converter = TextToAudioConverter(
    backend='edge-tts',
    enable_fallback=True,
    fallback_engines=['macos', 'gtts']
)

# Nếu edge-tts lỗi, sẽ tự động thử macos, sau đó gtts
converter.convert('input.txt', 'output.mp3')
```

## Batch conversion

Tất cả TTS engines đều hỗ trợ batch conversion:

```python
tasks = [
    ('chapter1.txt', 'chapter1.mp3', None),
    ('chapter2.txt', 'chapter2.mp3', None),
    ('chapter3.txt', 'chapter3.mp3', None),
]

converter.convert_batch(tasks, concurrency=4)
```

## Cấu hình trong config.json

```json
{
  "tts_backend": "macos",
  "macos_voice": "Linh",
  "edge_rate": 1.0,
  "enable_tts_fallback": false,
  "fallback_engines": ["macos", "gtts"],
  "fpt_api_key": "YOUR_API_KEY",
  "fpt_voice": "banmai"
}
```

## So sánh các engines

| Engine | Online/Offline | Chất lượng | Tốc độ | Cần API Key | Hỗ trợ tiếng Việt |
|--------|----------------|------------|--------|-------------|-------------------|
| **macos** | Offline | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | ✅ Tốt |
| **edge-tts** | Online | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ✅ Tốt |
| **gtts** | Online | ⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ✅ Tốt |
| **fpt-ai** | Online | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ | ✅ Rất tốt |

## Troubleshooting

### macOS TTS không hoạt động

1. Kiểm tra bạn đang chạy trên macOS:
   ```python
   import sys
   print(sys.platform)  # Phải là 'darwin'
   ```

2. Kiểm tra lệnh `say` có sẵn:
   ```bash
   which say
   say -v "Linh" "Test"
   ```

3. Kiểm tra giọng đọc có tồn tại:
   ```python
   from crawler.tts_engines import MacOSTTS
   macos = MacOSTTS()
   print(macos.list_voices())
   ```

### Fallback không hoạt động

- Đảm bảo `enable_fallback=True` trong config hoặc khi tạo converter
- Kiểm tra các engine dự phòng có sẵn:
  ```python
  from crawler.tts_engines import TTSManager
  print(TTSManager.list_available_engines())
  ```

### File output không đúng format

- macOS TTS xuất `.m4a` mặc định
- Nếu cần `.mp3`, cài đặt `ffmpeg`:
  ```bash
  brew install ffmpeg
  ```

## Ví dụ đầy đủ

```python
#!/usr/bin/env python3
"""Ví dụ sử dụng TTS engines."""

from crawler.tts_engines import TTSManager, MacOSTTS
from crawler.converter import TextToAudioConverter
import asyncio

# Ví dụ 1: Sử dụng MacOSTTS trực tiếp
async def example1():
    macos = MacOSTTS(voice='Linh')
    await macos.speak('Xin chào các bạn', 'hello.m4a')
    print('✓ Created hello.m4a')

# Ví dụ 2: Sử dụng với converter
def example2():
    converter = TextToAudioConverter(
        backend='macos',
        macos_voice='Linh'
    )
    converter.convert('input.txt', 'output.m4a')
    print('✓ Created output.m4a')

# Ví dụ 3: Với fallback tự động
def example3():
    converter = TextToAudioConverter(
        backend='edge-tts',
        enable_fallback=True,
        fallback_engines=['macos', 'gtts']
    )
    # Nếu edge-tts lỗi, sẽ tự động fallback
    converter.convert('input.txt', 'output.mp3')

# Chạy ví dụ
if __name__ == '__main__':
    asyncio.run(example1())
    example2()
    example3()
```

## Migration từ code cũ

Code cũ vẫn hoạt động bình thường (backward compatible). Bạn có thể từ từ migrate:

1. **Bước 1**: Thử engine mới với `--tts-backend macos`
2. **Bước 2**: Bật fallback trong config nếu muốn
3. **Bước 3**: Tùy chỉnh voice và các tham số khác

Không cần thay đổi code hiện tại, chỉ cần cập nhật config!

