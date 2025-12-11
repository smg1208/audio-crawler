# Hướng dẫn sử dụng Piper TTS

## Tổng quan

Piper TTS là một TTS engine **offline, mã nguồn mở**, chạy rất nhanh trên chip Apple Silicon (M4). Engine này sử dụng ONNX model để synthesize speech.

## Ưu điểm

- ✅ **Offline**: Không cần kết nối Internet
- ✅ **Nhanh**: Tối ưu cho Apple Silicon (M4)
- ✅ **Miễn phí**: Mã nguồn mở
- ✅ **Chất lượng tốt**: Hỗ trợ nhiều ngôn ngữ, bao gồm tiếng Việt

## Cài đặt

### 1. Cài đặt thư viện

```bash
pip install piper-tts
```

### 2. Tải model tiếng Việt

Piper cung cấp nhiều model tiếng Việt. Bạn có thể tải từ:

**Cách 1: Sử dụng piper CLI (nếu có)**
```bash
piper --download-voice vi_VN
```

**Cách 2: Tải thủ công từ GitHub**
- Truy cập: https://github.com/rhasspy/piper/releases
- Tìm model tiếng Việt (ví dụ: `vi_VN-vivos-x_low.onnx`)
- Tải file `.onnx` và `.json` (nếu có)

**Các model tiếng Việt phổ biến:**
- `vi_VN-vivos-x_low.onnx` - Chất lượng thấp, nhanh
- `vi_VN-vivos-medium.onnx` - Chất lượng trung bình
- `vi_VN-vivos-high.onnx` - Chất lượng cao, chậm hơn

### 3. Cấu trúc thư mục

Đề xuất cấu trúc:
```
Audio download/
├── models/
│   ├── vi_VN-vivos-x_low.onnx
│   └── vi_VN-vivos-x_low.onnx.json  (tùy chọn)
├── config.json
└── ...
```

## Cấu hình

### Trong config.json

```json
{
  "tts_backend": "piper",
  "piper_model_path": "models/vi_VN-vivos-x_low.onnx",
  "piper_config_path": "models/vi_VN-vivos-x_low.onnx.json"
}
```

**Lưu ý:**
- `piper_model_path`: **Bắt buộc** - Đường dẫn đến file `.onnx`
- `piper_config_path`: **Tùy chọn** - Đường dẫn đến file `.json` (thường cùng tên với model)

### Từ command line

```bash
python3 run.py --config config.json \
  --tts-backend piper \
  --piper-model-path models/vi_VN-vivos-x_low.onnx \
  --piper-config-path models/vi_VN-vivos-x_low.onnx.json
```

## Sử dụng

### 1. Với run.py

```bash
# Sử dụng config.json
python3 run.py --config config.json

# Hoặc override từ command line
python3 run.py --config config.json \
  --tts-backend piper \
  --piper-model-path models/vi_VN-vivos-x_low.onnx
```

### 2. Trong code Python

```python
from crawler.tts_engines import PiperTTS
import asyncio

# Khởi tạo (model được load một lần duy nhất)
piper = PiperTTS(
    model_path='models/vi_VN-vivos-x_low.onnx',
    config_path='models/vi_VN-vivos-x_low.onnx.json'  # tùy chọn
)

# Synthesize
asyncio.run(piper.speak('Xin chào các bạn', 'output.mp3'))
```

### 3. Với TextToAudioConverter

```python
from crawler.converter import TextToAudioConverter

converter = TextToAudioConverter(
    backend='piper',
    piper_model_path='models/vi_VN-vivos-x_low.onnx',
    piper_config_path='models/vi_VN-vivos-x_low.onnx.json'
)

converter.convert('input.txt', 'output.mp3')
```

## Format Output

Piper TTS xuất file **WAV** mặc định. Hệ thống sẽ tự động:

1. Synthesize text thành file `.wav` tạm
2. Convert `.wav` sang `.mp3` bằng `ffmpeg` (nếu output là `.mp3`)
3. Xóa file `.wav` tạm sau khi convert

**Lưu ý:**
- Nếu không có `ffmpeg`, file sẽ được lưu dưới dạng `.wav`
- Cài đặt `ffmpeg`: `brew install ffmpeg`

## Tối ưu hiệu năng

### 1. Load model một lần

Model được load **một lần duy nhất** khi khởi tạo `PiperTTS` class. Điều này giúp:
- Tăng tốc độ synthesize
- Giảm memory overhead
- Tối ưu cho batch conversion

### 2. Async/Non-blocking

Piper TTS chạy trong `asyncio.run_in_executor()` để không block event loop, cho phép:
- Chạy song song với các tác vụ khác
- Batch conversion hiệu quả

### 3. Apple Silicon Optimization

Piper sử dụng `onnxruntime` và tự động tối ưu cho Apple Silicon (M4):
- Sử dụng Neural Engine nếu có
- Tối ưu CPU cores
- Memory efficient

## Troubleshooting

### Lỗi: "piper-tts library is not available"

**Giải pháp:**
```bash
pip install piper-tts
```

### Lỗi: "Piper model file not found"

**Giải pháp:**
- Kiểm tra đường dẫn model trong config
- Đảm bảo file `.onnx` tồn tại
- Sử dụng đường dẫn tuyệt đối hoặc tương đối đúng

### Lỗi: "Failed to load Piper model"

**Giải pháp:**
- Kiểm tra file model có bị hỏng không
- Thử tải lại model
- Kiểm tra version của `piper-tts` có tương thích không

### File output là WAV thay vì MP3

**Nguyên nhân:** Không có `ffmpeg`

**Giải pháp:**
```bash
brew install ffmpeg
```

### Chậm khi synthesize

**Tối ưu:**
- Sử dụng model `x_low` hoặc `low` cho tốc độ nhanh nhất
- Đảm bảo model chỉ load một lần (không tạo instance mới mỗi lần)
- Sử dụng batch conversion thay vì sequential

## So sánh với các engine khác

| Engine | Online/Offline | Tốc độ | Chất lượng | Cần Model |
|--------|---------------|--------|------------|-----------|
| **piper** | Offline | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| **macos** | Offline | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| **edge-tts** | Online | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ |
| **gtts** | Online | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |

## Ví dụ đầy đủ

### config.json

```json
{
  "story_id": "my-story",
  "tts_backend": "piper",
  "piper_model_path": "models/vi_VN-vivos-x_low.onnx",
  "piper_config_path": "models/vi_VN-vivos-x_low.onnx.json",
  "batch_size": 50
}
```

### Chạy

```bash
python3 run.py --config config.json
```

### Kết quả

- Text files được convert thành audio files (MP3)
- Model chỉ load một lần khi khởi tạo
- Tự động convert WAV -> MP3
- Xóa file WAV tạm sau khi convert

## Tải model tiếng Việt

### Từ GitHub Releases

1. Truy cập: https://github.com/rhasspy/piper/releases
2. Tìm file `vi_VN-vivos-x_low.onnx` (hoặc model khác)
3. Tải về và đặt vào thư mục `models/`

### Sử dụng wget/curl

```bash
mkdir -p models
cd models

# Tải model (ví dụ)
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/vi_VN-vivos-x_low.onnx
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/vi_VN-vivos-x_low.onnx.json
```

## Lưu ý quan trọng

1. **Model size**: Model có thể lớn (50-200MB), đảm bảo có đủ dung lượng
2. **First load**: Lần đầu load model có thể mất vài giây
3. **Memory**: Model được load vào RAM, cần đủ memory
4. **Format**: Output mặc định là WAV, tự động convert sang MP3 nếu có ffmpeg

