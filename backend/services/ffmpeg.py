
import os
import sys
import subprocess
import numpy as np

FFMPEG_PATH = None


def find_ffmpeg():

    global FFMPEG_PATH

    # 1. Try system ffmpeg first
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        FFMPEG_PATH = "ffmpeg"
        print("✓ ffmpeg found (system)!")
        return True
    except FileNotFoundError:
        pass

    # 2. Try imageio-ffmpeg bundled binary (most reliable fallback)
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            FFMPEG_PATH = ffmpeg_exe
            print(f"✓ ffmpeg found (imageio-ffmpeg): {ffmpeg_exe}")
            return True
    except ImportError:
        pass

    # 3. Try common installation locations
    common_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"),
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
    ]
    
    for path in common_paths:
        ffmpeg_exe = os.path.join(path, "ffmpeg.exe")
        if os.path.exists(ffmpeg_exe):
            FFMPEG_PATH = ffmpeg_exe
            print(f"✓ ffmpeg found: {ffmpeg_exe}")
            return True
        
        # Walk through subdirectories
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                if "ffmpeg.exe" in files:
                    FFMPEG_PATH = os.path.join(root, "ffmpeg.exe")
                    print(f"✓ ffmpeg found: {FFMPEG_PATH}")
                    return True

    # ffmpeg not found
    _print_ffmpeg_install_instructions()
    return False


def _print_ffmpeg_install_instructions():
    """Print installation instructions for ffmpeg"""
    print("=" * 60)
    print("  ERROR: ffmpeg is NOT installed!")
    print("  Whisper needs ffmpeg to extract audio from videos.")
    print()
    print("  Install it with:")
    print("    pip install imageio-ffmpeg")
    print()
    print("  Then run again (no restart needed).")
    print("=" * 60)


def patch_whisper_audio_loader():
    """
    Monkey-patch Whisper's load_audio function to use discovered ffmpeg binary.
    This is needed because imageio-ffmpeg's binary has a different name.
    """
    if not FFMPEG_PATH or FFMPEG_PATH == "ffmpeg":
        return

    import whisper.audio

    _ORIGINAL_SAMPLE_RATE = whisper.audio.SAMPLE_RATE

    def _patched_load_audio(file, sr=_ORIGINAL_SAMPLE_RATE):
        """Load audio using our discovered ffmpeg binary."""
        cmd = [
            FFMPEG_PATH,
            "-nostdin",
            "-threads", "0",
            "-i", file,
            "-f", "s16le",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-ar", str(sr),
            "-"
        ]
        try:
            out = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            ).stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg error: {e.stderr.decode(errors='replace')}") from e

        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

    whisper.audio.load_audio = _patched_load_audio
    print("✓ Whisper patched to use discovered ffmpeg binary")


def is_ffmpeg_available():
    return FFMPEG_PATH is not None


def get_ffmpeg_path():
    return FFMPEG_PATH


def extract_thumbnail(video_path: str, output_path: str, timestamp: float = 1.0) -> bool:
    """
    Extract a single frame from the video at the given timestamp using ffmpeg.
    
    Args:
        video_path: Path to the input video file
        output_path: Path to save the extracted JPEG thumbnail
        timestamp: Time in seconds to extract the frame from
        
    Returns:
        True if successful, False otherwise
    """
    if not FFMPEG_PATH:
        return False
        
    cmd = [
        FFMPEG_PATH,
        "-y",               # Overwrite output file
        "-ss", str(timestamp), # Seek to timestamp
        "-i", video_path,   # Input file
        "-vframes", "1",    # Output 1 frame
        "-q:v", "2",        # High quality JPEG
        output_path         # Output path
    ]
    
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return os.path.exists(output_path)
    except Exception as e:
        print(f"Failed to extract thumbnail: {e}")
        return False
