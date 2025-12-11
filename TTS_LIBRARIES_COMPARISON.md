# So sánh các thư viện TTS cho Python

## Tổng quan

Hệ thống hiện tại đã hỗ trợ 6 TTS engines:
1. **edge-tts** (Online, Free) - Microsoft Edge TTS
2. **macos** (Offline, Free) - macOS native `say` command
3. **gtts** (Online, Free) - Google Text-to-Speech
4. **fpt-ai** (Online, Paid) - FPT.AI TTS
5. **piper** (Offline, Free) - Piper TTS
6. **google-cloud** (Online, Paid) - Google Cloud Text-to-Speech

## Các thư viện TTS khác

### 1. pyttsx3 (Offline, Free)

**Mô tả:**
- Thư viện TTS offline, cross-platform
- Sử dụng engine native của OS:
  - **Windows**: SAPI5
  - **macOS**: NSSpeechSynthesizer (giống `say` command)
  - **Linux**: espeak

**Ưu điểm:**
- ✅ Offline, không cần internet
- ✅ Miễn phí
- ✅ Cross-platform
- ✅ Có thể điều chỉnh tốc độ, âm lượng, giọng nói
- ✅ Đơn giản, dễ sử dụng

**Nhược điểm:**
- ❌ Chất lượng không cao bằng cloud TTS
- ❌ Giọng tiếng Việt hạn chế (phụ thuộc vào OS)
- ❌ Trên macOS: giống với `MacOSTTS` hiện tại (dùng `say` command)
- ❌ Trên Linux: espeak có giọng tiếng Việt kém

**Cài đặt:**
```bash
pip install pyttsx3
```

**Ví dụ sử dụng:**
```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Tốc độ nói
engine.setProperty('volume', 0.9)  # Âm lượng
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)  # Chọn giọng
engine.save_to_file('Xin chào', 'output.mp3')
engine.runAndWait()
```

**Đánh giá:**
- **Trên macOS**: Không cần thiết vì đã có `MacOSTTS` (dùng `say` command trực tiếp)
- **Trên Windows**: Có thể hữu ích nếu muốn offline TTS
- **Trên Linux**: Có thể dùng nhưng chất lượng không tốt

---

### 2. Coqui TTS (Offline, Free, Open Source)

**Mô tả:**
- Thư viện TTS mã nguồn mở, chất lượng cao
- Hỗ trợ nhiều ngôn ngữ, có model tiếng Việt
- Có thể fine-tune model cho giọng cụ thể

**Ưu điểm:**
- ✅ Offline, không cần internet
- ✅ Miễn phí, mã nguồn mở
- ✅ Chất lượng cao (Neural TTS)
- ✅ Hỗ trợ nhiều ngôn ngữ
- ✅ Có thể fine-tune

**Nhược điểm:**
- ❌ Cần GPU để chạy nhanh (CPU chậm hơn)
- ❌ Model lớn, tốn dung lượng
- ❌ Setup phức tạp hơn
- ❌ Cần download model riêng

**Cài đặt:**
```bash
pip install TTS
```

**Ví dụ sử dụng:**
```python
from TTS.api import TTS

tts = TTS("tts_models/vi/viettts/vits", gpu=False)
tts.tts_to_file("Xin chào", file_path="output.wav")
```

**Đánh giá:**
- **Rất tốt** nếu cần chất lượng cao và offline
- Phù hợp với dự án cần chất lượng cao hơn Piper TTS

---

### 3. Bark (Offline, Free, Open Source)

**Mô tả:**
- Thư viện TTS mã nguồn mở từ Suno AI
- Có thể tạo giọng nói tự nhiên, thậm chí có thể tạo âm thanh (nhạc, tiếng động)

**Ưu điểm:**
- ✅ Offline, không cần internet
- ✅ Miễn phí, mã nguồn mở
- ✅ Chất lượng rất cao
- ✅ Có thể tạo âm thanh đặc biệt

**Nhược điểm:**
- ❌ Cần GPU mạnh
- ❌ Model rất lớn
- ❌ Chậm trên CPU
- ❌ Hỗ trợ tiếng Việt hạn chế

**Đánh giá:**
- **Không phù hợp** cho dự án này (quá nặng, hỗ trợ tiếng Việt kém)

---

### 4. ElevenLabs (Online, Paid)

**Mô tả:**
- Dịch vụ TTS thương mại, chất lượng rất cao
- Có thể clone giọng nói
- API dễ sử dụng

**Ưu điểm:**
- ✅ Chất lượng rất cao
- ✅ Có thể clone giọng
- ✅ API đơn giản
- ✅ Hỗ trợ nhiều ngôn ngữ

**Nhược điểm:**
- ❌ Trả phí (khá đắt)
- ❌ Cần internet
- ❌ Cần API key

**Đánh giá:**
- **Tốt** nếu có ngân sách và cần chất lượng cao nhất
- Có thể thêm vào hệ thống nếu cần

---

### 5. Azure TTS (Online, Paid)

**Mô tả:**
- Dịch vụ TTS từ Microsoft Azure
- Chất lượng cao, nhiều giọng nói
- Có free tier

**Ưu điểm:**
- ✅ Chất lượng cao
- ✅ Nhiều giọng nói
- ✅ Có free tier
- ✅ Hỗ trợ SSML

**Nhược điểm:**
- ❌ Cần internet
- ❌ Cần Azure account
- ❌ Trả phí sau free tier

**Đánh giá:**
- **Tốt** nếu đã có Azure account
- Tương tự Google Cloud TTS

---

### 6. Amazon Polly (Online, Paid)

**Mô tả:**
- Dịch vụ TTS từ AWS
- Chất lượng cao, nhiều giọng nói
- Có free tier

**Ưu điểm:**
- ✅ Chất lượng cao
- ✅ Nhiều giọng nói
- ✅ Có free tier
- ✅ Hỗ trợ SSML

**Nhược điểm:**
- ❌ Cần internet
- ❌ Cần AWS account
- ❌ Trả phí sau free tier

**Đánh giá:**
- **Tốt** nếu đã có AWS account
- Tương tự Google Cloud TTS

---

### 7. OpenAI TTS (Online, Paid)

**Mô tả:**
- Dịch vụ TTS từ OpenAI (mới ra)
- Chất lượng cao, giọng tự nhiên
- API đơn giản

**Ưu điểm:**
- ✅ Chất lượng cao
- ✅ Giọng tự nhiên
- ✅ API đơn giản
- ✅ Hỗ trợ nhiều ngôn ngữ

**Nhược điểm:**
- ❌ Trả phí
- ❌ Cần internet
- ❌ Cần OpenAI API key

**Đánh giá:**
- **Tốt** nếu đã có OpenAI account
- Có thể thêm vào hệ thống

---

## So sánh tổng quan

| Thư viện | Offline | Free | Chất lượng | Tiếng Việt | Độ khó setup | Đề xuất |
|----------|---------|------|------------|------------|--------------|---------|
| **edge-tts** | ❌ | ✅ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ✅ Đã có |
| **macos** | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ✅ Đã có |
| **gtts** | ❌ | ✅ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ✅ Đã có |
| **fpt-ai** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ✅ Đã có |
| **piper** | ✅ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ✅ Đã có |
| **google-cloud** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Đã có |
| **pyttsx3** | ✅ | ✅ | ⭐⭐⭐ | ⭐⭐ | ⭐ | ⚠️ Trùng với macos |
| **Coqui TTS** | ✅ | ✅ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 💡 Có thể thêm |
| **ElevenLabs** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 💡 Có thể thêm |
| **Azure TTS** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 💡 Có thể thêm |
| **Polly** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 💡 Có thể thêm |
| **OpenAI TTS** | ❌ | 💰 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 💡 Có thể thêm |

---

## Đề xuất

### 1. pyttsx3
- **Trên macOS**: **KHÔNG CẦN** vì đã có `MacOSTTS` (dùng `say` command trực tiếp, nhanh hơn)
- **Trên Windows**: **CÓ THỂ THÊM** nếu cần offline TTS trên Windows
- **Trên Linux**: **KHÔNG KHUYẾN NGHỊ** vì espeak có giọng tiếng Việt kém

### 2. Coqui TTS
- **NÊN THÊM** nếu cần chất lượng cao hơn Piper TTS và offline
- Phù hợp cho dự án cần chất lượng cao nhất mà không muốn trả phí

### 3. ElevenLabs / Azure TTS / Polly / OpenAI TTS
- **CÓ THỂ THÊM** nếu cần thêm lựa chọn cloud TTS
- Ưu tiên: OpenAI TTS (mới, đơn giản) > Azure TTS > ElevenLabs > Polly

---

## Kết luận

**Hệ thống hiện tại đã khá đầy đủ:**
- ✅ 6 engines đã hỗ trợ
- ✅ Có cả offline và online
- ✅ Có cả free và paid
- ✅ Chất lượng từ tốt đến rất tốt

**Nếu muốn thêm:**
1. **Coqui TTS**: Nếu cần chất lượng cao hơn Piper và offline
2. **OpenAI TTS**: Nếu cần thêm lựa chọn cloud TTS mới
3. **pyttsx3**: Chỉ nếu cần hỗ trợ Windows offline (không cần trên macOS)

**pyttsx3 trên macOS:**
- Không cần thiết vì `MacOSTTS` đã dùng cùng engine (NSSpeechSynthesizer)
- `MacOSTTS` nhanh hơn vì dùng `say` command trực tiếp
- `pyttsx3` chỉ là wrapper, không cải thiện chất lượng

