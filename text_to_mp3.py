#!/usr/bin/env python3
"""Simple CLI tool to convert text to MP3 using various TTS backends.

Supported backends:
    - edge-tts (default): Microsoft Edge TTS
    - gtts: Google Text-to-Speech (free, simple, no API key)
    - fpt-ai: FPT.AI TTS (high quality, requires API key)
    - google-cloud: Google Cloud Text-to-Speech (high quality, requires credentials)

Usage:
    python3 text_to_mp3.py --text "Xin chào" --output hello.mp3 --backend gtts
    python3 text_to_mp3.py --file chapter.txt --output chapter.mp3 --backend edge-tts --voice "vi-VN-NamMinhNeural"
    python3 text_to_mp3.py --text "Xin chào" --output hello.mp3 --backend fpt-ai --fpt-api-key YOUR_KEY
    python3 text_to_mp3.py --text "Xin chào" --output hello.mp3 --backend google-cloud --google-cloud-credentials credentials.json --voice "vi-VN-Neural2-D"
"""
import argparse
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Try to use converter from crawler for unified backend support
try:
    from crawler.converter import TextToAudioConverter
    USE_CONVERTER = True
except ImportError:
    USE_CONVERTER = False
    # Fallback to edge-tts only
    try:
        import edge_tts
    except ImportError:
        print("Error: edge-tts not installed. Install it with:")
        print("  pip install edge-tts")
        print("\nOr install gtts for alternative backend:")
        print("  pip install gtts")
        sys.exit(1)


async def text_to_speech(text: str, output_path: str, voice: str = "vi-VN-NamMinhNeural", rate: float = 1.0, max_retries: int = 3) -> None:
    """Convert text to MP3 using edge-tts.

    Args:
        text: Text to convert
        output_path: Output MP3 file path
        voice: Edge-tts voice name (default: vi-VN-NamMinhNeural for Vietnamese male)
        rate: Speech rate (0.5 to 2.0, default 1.0)
        max_retries: Maximum number of retry attempts (default: 3)
    """
    if not text.strip():
        print("Error: Text is empty")
        sys.exit(1)

    # Convert rate to edge-tts format (+X% or -X%)
    if rate == 1.0:
        rate_str = "+0%"
    elif rate > 1.0:
        rate_str = f"+{int((rate - 1.0) * 100)}%"
    else:
        rate_str = f"{int((rate - 1.0) * 100)}%"

    print(f"Converting text to speech...")
    print(f"  Voice: {voice}")
    print(f"  Rate: {rate}x")
    print(f"  Output: {output_path}")
    
    # Try with retries
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            # Create communicate object
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str)
            
            # Save to file with timeout
            import asyncio
            await asyncio.wait_for(communicate.save(output_path), timeout=60.0)
            
            # Verify file was created and has content
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                if size > 0:
                    size_mb = size / (1024 * 1024)
                    print(f"✓ Success! Created {output_path} ({size_mb:.2f} MB)")
                    return
                else:
                    print(f"⚠️  Attempt {attempt}: File created but is empty, retrying...")
                    os.remove(output_path)
            else:
                print(f"⚠️  Attempt {attempt}: File was not created, retrying...")
                
        except asyncio.TimeoutError:
            last_error = f"Timeout after 60 seconds (attempt {attempt}/{max_retries})"
            print(f"⚠️  {last_error}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            last_error = str(e)
            error_msg = str(e).lower()
            if "no audio was received" in error_msg or "connection" in error_msg:
                print(f"⚠️  Attempt {attempt}/{max_retries}: {e}")
                if attempt < max_retries:
                    print(f"   Retrying in {2 ** attempt} seconds...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                # Non-retryable error
                print(f"Error during conversion: {e}")
                sys.exit(1)
    
    # All retries failed
    print(f"\n✗ Failed after {max_retries} attempts")
    print(f"Last error: {last_error}")
    print("\nTroubleshooting tips:")
    print("1. Check your internet connection")
    print("2. Try a different voice: --voice vi-VN-HoaiMyNeural")
    print("3. Check if firewall/VPN is blocking edge-tts connections")
    print("4. Try upgrading edge-tts: pip install --upgrade edge-tts")
    sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert text to MP3 using edge-tts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert text directly
  python3 text_to_mp3.py --text "Xin chào" --output hello.mp3

  # Convert from file
  python3 text_to_mp3.py --file chapter.txt --output chapter.mp3

  # Use different voice
  python3 text_to_mp3.py --text "Hello" --output hello.mp3 --voice "vi-VN-HoaiMyNeural"

  # Adjust speech rate (0.5 = slower, 1.5 = faster)
  python3 text_to_mp3.py --text "Hello" --output hello.mp3 --rate 0.8

  # Use Google Cloud TTS
  python3 text_to_mp3.py --text "Xin chào" --output hello.mp3 --backend google-cloud \\
      --google-cloud-credentials credentials/google-cloud-tts.json \\
      --voice "vi-VN-Neural2-D"

Available Vietnamese voices:
  - Edge TTS: vi-VN-NamMinhNeural (male, default), vi-VN-HoaiMyNeural (female)
  - Google Cloud: vi-VN-Neural2-D (male), vi-VN-Neural2-A (female), vi-VN-Wavenet-B (male), etc.
"""
    )

    parser.add_argument('--text', help='Text to convert (or use --file)')
    parser.add_argument('--file', help='Text file to convert (alternative to --text)')
    parser.add_argument('--output', '-o', required=True, help='Output MP3 file path')
    parser.add_argument('--backend', default='edge-tts', choices=['edge-tts', 'gtts', 'fpt-ai', 'google-cloud'],
                        help='TTS backend to use (default: edge-tts)')
    parser.add_argument('--voice', default='vi-VN-NamMinhNeural', 
                        help='Voice name (for edge-tts: vi-VN-NamMinhNeural, vi-VN-HoaiMyNeural; for fpt-ai: banmai, lannhi, leminh, giahuy; for google-cloud: vi-VN-Neural2-D, vi-VN-Wavenet-B, etc.)')
    parser.add_argument('--rate', type=float, default=1.0, help='Speech rate 0.5-2.0 (default: 1.0, only for edge-tts)')
    parser.add_argument('--fpt-api-key', help='FPT.AI API key (required if using fpt-ai backend)')
    parser.add_argument('--google-cloud-credentials', help='Google Cloud credentials JSON file path (required if using google-cloud backend)')
    parser.add_argument('--google-cloud-language', default='vi-VN', help='Google Cloud language code (default: vi-VN)')
    parser.add_argument('--google-cloud-ssml-gender', choices=['NEUTRAL', 'FEMALE', 'MALE'], help='Google Cloud SSML gender (optional)')

    args = parser.parse_args(argv)

    # Get text from either --text or --file
    if args.text:
        text = args.text
        # Create temporary file for converter
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_file = f.name
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        temp_file = args.file
    else:
        parser.print_help()
        print("\nError: Provide either --text or --file")
        sys.exit(1)

    # Use converter if available (supports all backends)
    if USE_CONVERTER:
        try:
            fpt_api_key = args.fpt_api_key or os.environ.get('FPT_API_KEY')
            google_cloud_credentials = args.google_cloud_credentials or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            
            # Validate Google Cloud credentials if using google-cloud backend
            if args.backend == 'google-cloud':
                if not google_cloud_credentials:
                    print("Error: Google Cloud credentials are required.")
                    print("  Set --google-cloud-credentials or GOOGLE_APPLICATION_CREDENTIALS environment variable")
                    sys.exit(1)
                if not os.path.exists(google_cloud_credentials):
                    print(f"Error: Google Cloud credentials file not found: {google_cloud_credentials}")
                    sys.exit(1)
            
            converter = TextToAudioConverter(
                backend=args.backend,
                dry_run=False,
                fpt_api_key=fpt_api_key,
                fpt_voice=args.voice if args.backend == 'fpt-ai' else 'banmai',
                google_cloud_credentials_path=google_cloud_credentials if args.backend == 'google-cloud' else None,
                google_cloud_language_code=args.google_cloud_language if args.backend == 'google-cloud' else 'vi-VN',
                google_cloud_voice_name=args.voice if args.backend == 'google-cloud' else None,
                google_cloud_ssml_gender=args.google_cloud_ssml_gender if args.backend == 'google-cloud' else None
            )
            
            print(f"Converting text to speech using {args.backend}...")
            print(f"  Backend: {args.backend}")
            if args.backend == 'edge-tts':
                print(f"  Voice: {args.voice}")
                print(f"  Rate: {args.rate}x")
            elif args.backend == 'fpt-ai':
                print(f"  Voice: {args.voice}")
            elif args.backend == 'google-cloud':
                print(f"  Voice: {args.voice}")
                print(f"  Language: {args.google_cloud_language}")
                if args.google_cloud_ssml_gender:
                    print(f"  SSML Gender: {args.google_cloud_ssml_gender}")
            print(f"  Output: {args.output}")
            
            # For edge-tts, we still need to use the async function for rate control
            if args.backend == 'edge-tts' and args.rate != 1.0:
                # Use async function for rate control
                asyncio.run(text_to_speech(text, args.output, voice=args.voice, rate=args.rate))
            else:
                # Use converter for other backends
                # For google-cloud, voice is already set in converter initialization
                voice_arg = None
                if args.backend == 'gtts':
                    voice_arg = None  # gTTS doesn't use voice parameter
                elif args.backend == 'google-cloud':
                    voice_arg = None  # Voice is set in converter initialization
                else:
                    voice_arg = args.voice
                converter.convert(temp_file, args.output, voice=voice_arg)
            
            # Verify file was created
            if os.path.exists(args.output):
                size = os.path.getsize(args.output)
                if size > 0:
                    size_mb = size / (1024 * 1024)
                    print(f"✓ Success! Created {args.output} ({size_mb:.2f} MB)")
                else:
                    print("Error: Output file is empty")
                    sys.exit(1)
            else:
                print("Error: Output file was not created")
                sys.exit(1)
                
        except Exception as e:
            print(f"Error during conversion: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            # Clean up temp file if we created it
            if args.text and os.path.exists(temp_file):
                os.unlink(temp_file)
    else:
        # Fallback to edge-tts only
        if args.backend != 'edge-tts':
            print(f"Error: Backend '{args.backend}' requires crawler.converter module.")
            print("Make sure you're running from the project root directory.")
            sys.exit(1)
        asyncio.run(text_to_speech(text, args.output, voice=args.voice, rate=args.rate))


if __name__ == '__main__':
    main()
