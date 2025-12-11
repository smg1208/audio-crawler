# Hướng dẫn sử dụng Coqui TTS

## ⚠️  QUAN TRỌNG: XTTS v2 KHÔNG hỗ trợ tiếng Việt!

**XTTS v2 không hỗ trợ language code "vi" (tiếng Việt).**

Supported languages: `['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']`

**💡 Khuyến nghị:** Dùng backend khác cho tiếng Việt:
- **google-cloud**: Hỗ trợ tiếng Việt tốt, ổn định
- **azure**: Hỗ trợ tiếng Việt tốt, ổn định  
- **macos**: Offline, native Vietnamese voice

---

## Tổng quan

**Coqui TTS** là một thư viện TTS mã nguồn mở, chất lượng cao, hoạt động offline. Nó sử dụng các mô hình neural network để tạo giọng nói tự nhiên.

### Ưu điểm
- ✅ **Offline**: Không cần internet
- ✅ **Miễn phí**: Mã nguồn mở
- ✅ **Chất lượng cao**: Neural TTS, giọng nói tự nhiên
- ⚠️  **KHÔNG hỗ trợ tiếng Việt**: XTTS v2 không hỗ trợ language="vi"
- ✅ **Có thể fine-tune**: Có thể huấn luyện model riêng

### Nhược điểm
- ❌ **Cần GPU để chạy nhanh**: CPU chậm hơn đáng kể
- ❌ **Model lớn**: Tốn dung lượng (vài trăm MB đến vài GB)
- ❌ **Setup phức tạp hơn**: Cần cài đặt PyTorch và dependencies
- ❌ **Tải model lần đầu**: Model sẽ được download tự động lần đầu tiên

---

## Cài đặt

### 1. Cài đặt Coqui TTS

```bash
pip install TTS
```

**Lưu ý:**
- Coqui TTS yêu cầu Python 3.7-3.10 (không hỗ trợ Python 3.11+)
- Nếu bạn dùng Python 3.11+, có thể cần dùng Python 3.10

### 2. Kiểm tra cài đặt

```bash
python3 -c "from TTS.api import TTS; print('Coqui TTS installed successfully')"
```

### 3. (Tùy chọn) Cài đặt PyTorch với GPU support

Nếu bạn có GPU và muốn tăng tốc:

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

---

## Cấu hình

### 1. Trong `config.json`

```json
{
  "tts_backend": "coqui",
  "coqui_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
  "coqui_device": "",
  "coqui_speaker_wav": "path/to/speaker.wav",
  "coqui_language": "vi"
}
```

**Các tham số:**
- `coqui_model_name`: Tên model (mặc định: `"tts_models/multilingual/multi-dataset/xtts_v2"`)
- `coqui_device`: Thiết bị chạy (`"cpu"`, `"cuda"`, hoặc `""` để tự động)
- `coqui_speaker_wav`: Đường dẫn file audio mẫu cho voice cloning (bắt buộc với XTTS v2)
- `coqui_language`: Mã ngôn ngữ (mặc định: `"vi"` cho tiếng Việt)

### 2. Trong `stories/{story_id}.json`

```json
{
  "tts_backend": "coqui",
  "coqui_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
  "coqui_device": "cpu",
  "coqui_speaker_wav": "path/to/speaker.wav",
  "coqui_language": "vi"
}
```

---

## Các model có sẵn

### 1. Multilingual XTTS v2 (Mặc định, Khuyến nghị)

```json
{
  "coqui_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
  "coqui_speaker_wav": "path/to/speaker.wav",
  "coqui_language": "vi"
}
```

- **Chất lượng**: ⭐⭐⭐⭐⭐
- **Tốc độ**: ⭐⭐⭐ (chậm hơn)
- **Kích thước**: ~1-2 GB
- **Giọng**: Có thể clone giọng (cần `speaker_wav`)
- **Hỗ trợ**: Nhiều ngôn ngữ nhưng **KHÔNG hỗ trợ tiếng Việt**
- **Lưu ý**: 
  - ⚠️  **KHÔNG hỗ trợ tiếng Việt** (language="vi" không được hỗ trợ)
  - **Bắt buộc** có `speaker_wav` (file audio mẫu để clone giọng)
  - Cần license confirmation lần đầu (chấp nhận CPML)
  - Model lớn, download lần đầu mất thời gian
  - Supported languages: `['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'nl', 'cs', 'ar', 'zh-cn', 'hu', 'ko', 'ja', 'hi']`

### 2. Các model khác

Bạn có thể thử các model khác từ [Coqui TTS Model Zoo](https://github.com/coqui-ai/TTS), nhưng lưu ý:
- Model tiếng Việt riêng (`tts_models/vi/viettts/vits`) có thể không còn tồn tại
- Một số model không cần `speaker_wav` (nhưng chất lượng có thể thấp hơn)

---

## Sử dụng

### 1. Qua `run.py`

```bash
python3 run.py --config config.json --tts-backend coqui
```

### 2. Với model tùy chỉnh và speaker file

```bash
python3 run.py --config config.json \
  --tts-backend coqui \
  --coqui-model-name "tts_models/multilingual/multi-dataset/xtts_v2" \
  --coqui-device "cpu" \
  --coqui-speaker-wav "path/to/speaker.wav" \
  --coqui-language "vi"
```

### 3. Với GPU (nếu có)

```bash
python3 run.py --config config.json \
  --tts-backend coqui \
  --coqui-device "cuda"
```

---

## So sánh với các engine khác

| Engine | Offline | Free | Chất lượng | Tốc độ (CPU) | Tốc độ (GPU) | Setup |
|--------|---------|------|------------|--------------|--------------|-------|
| **coqui** | ✅ | ✅ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **piper** | ✅ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **macos** | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A | ⭐ |
| **edge-tts** | ❌ | ✅ | ⭐⭐⭐⭐⭐ | N/A | N/A | ⭐ |
| **google-cloud** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | N/A | N/A | ⭐⭐⭐ |

---

## Troubleshooting

### Lỗi: "Coqui TTS library is not available"

**Giải pháp:**
```bash
pip install TTS
```

### Lỗi: "Python version not supported"

**Nguyên nhân:** Coqui TTS chỉ hỗ trợ Python 3.7-3.10

**Giải pháp:**
- Sử dụng Python 3.10 hoặc thấp hơn
- Hoặc dùng virtual environment với Python 3.10

### Lỗi: "Model not found" hoặc download chậm

**Nguyên nhân:** Model sẽ được download tự động lần đầu tiên

**Giải pháp:**
- Đợi model download (có thể mất vài phút, XTTS v2 ~1-2 GB)
- Kiểm tra kết nối internet
- Model được lưu tại `~/.local/share/tts/`

### Lỗi: "Model requires speaker_wav parameter"

**Nguyên nhân:** XTTS v2 cần file audio mẫu để clone giọng

**Giải pháp:**
- Cung cấp `coqui_speaker_wav` trong config hoặc CLI argument
- File audio nên là WAV hoặc MP3, độ dài 5-30 giây
- File audio nên có giọng nói rõ ràng, không có nhiễu

### Lỗi: "I have purchased a commercial license" prompt

**Nguyên nhân:** XTTS v2 yêu cầu chấp nhận license (CPML) lần đầu

**Giải pháp:**
- Script tự động chấp nhận license (COQUI_TOS_AGREED=1)
- Nếu vẫn bị prompt, set manually: `export COQUI_TOS_AGREED=1`

### Lỗi: "cannot import name 'BeamSearchScorer' from 'transformers'"

**Nguyên nhân:** Version incompatibility giữa TTS và transformers library

**Giải pháp:**
```bash
# Option 1: Downgrade transformers
pip install transformers==4.35.0

# Option 2: Upgrade TTS
pip install --upgrade TTS

# Option 3: Dùng backend khác (khuyến nghị nếu vẫn lỗi)
# Sử dụng google-cloud, azure, hoặc macos thay vì coqui
```

### Lỗi: "CUDA out of memory"

**Nguyên nhân:** GPU không đủ bộ nhớ

**Giải pháp:**
- Dùng `"coqui_device": "cpu"` thay vì `"cuda"`
- Hoặc giảm batch size

### Chạy chậm trên CPU

**Nguyên nhân:** Coqui TTS chạy chậm trên CPU

**Giải pháp:**
- Sử dụng GPU nếu có
- Hoặc dùng Piper TTS thay thế (nhanh hơn trên CPU)

---

## Best Practices

1. **Sử dụng GPU nếu có:**
   - Tăng tốc đáng kể (5-10x)
   - Set `"coqui_device": "cuda"`

2. **Sử dụng CPU nếu không có GPU:**
   - Chấp nhận tốc độ chậm hơn
   - Set `"coqui_device": "cpu"`
   - Hoặc dùng Piper TTS thay thế

3. **Model mặc định:**
   - `"tts_models/multilingual/multi-dataset/xtts_v2"` là model mặc định
   - Hỗ trợ nhiều ngôn ngữ bao gồm tiếng Việt
   - Cần `speaker_wav` để clone giọng
   - Chất lượng cao nhưng model lớn (~1-2 GB)

4. **Batch processing:**
   - Coqui TTS hỗ trợ batch processing
   - Có thể tăng `tts_concurrency` lên 2-4 (tùy GPU/CPU)

---

## Ví dụ cấu hình đầy đủ

### Ví dụ 1: Coqui TTS với CPU

```json
{
  "tts_backend": "coqui",
  "coqui_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
  "coqui_device": "cpu",
  "coqui_speaker_wav": "speaker_samples/speaker.wav",
  "coqui_language": "vi",
  "tts_concurrency": 2
}
```

### Ví dụ 2: Coqui TTS với GPU

```json
{
  "tts_backend": "coqui",
  "coqui_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
  "coqui_device": "cuda",
  "coqui_speaker_wav": "speaker_samples/speaker.wav",
  "coqui_language": "vi",
  "tts_concurrency": 4
}
```

### Ví dụ 3: Coqui TTS với fallback

```json
{
  "tts_backend": "coqui",
  "coqui_model_name": "tts_models/multilingual/multi-dataset/xtts_v2",
  "coqui_device": "cpu",
  "coqui_speaker_wav": "speaker_samples/speaker.wav",
  "coqui_language": "vi",
  "enable_tts_fallback": true,
  "fallback_engines": ["piper", "macos"]
}
```

---

## Tài liệu tham khảo

- Coqui TTS Documentation: https://docs.coqui.ai/
- Model Zoo: https://github.com/coqui-ai/TTS
- Vietnamese VITS Model: https://github.com/coqui-ai/TTS/wiki/Released-Models#vietnamese

---

## Lưu ý quan trọng

1. **Python version**: Coqui TTS chỉ hỗ trợ Python 3.7-3.10 (không hỗ trợ Python 3.11+)
2. **Model download**: Model sẽ được download tự động lần đầu (XTTS v2 ~1-2 GB, có thể mất vài phút)
3. **GPU vs CPU**: GPU nhanh hơn 5-10x so với CPU
4. **File format**: Coqui TTS xuất file `.wav`, hệ thống sẽ tự động convert sang `.mp3` nếu cần
5. **Memory**: Model cần vài trăm MB đến vài GB RAM/VRAM
6. **Speaker WAV**: XTTS v2 **bắt buộc** cần `speaker_wav` để clone giọng. File nên là WAV/MP3, 5-30 giây, giọng rõ ràng
7. **License**: XTTS v2 yêu cầu chấp nhận CPML license lần đầu (có thể set `COQUI_TOS_AGREED=1`)

