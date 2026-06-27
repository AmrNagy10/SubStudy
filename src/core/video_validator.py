import os
import asyncio
import ffmpeg
from typing import Tuple

from src.core.exceptions import VideoValidationError
from src.core.config import settings

class VideoValidator:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._is_valid = False
        self._error_message = ""
        self.probe = {}
        self._size = 0
        self._format_info = {}
        self._streams = []
            
    async def validate_async(self) -> Tuple[bool, str]:
        if not await asyncio.to_thread(os.path.exists, self.file_path):
            self._is_valid = False
            self._error_message = f"File not found at: {self.file_path}"
            return False, self._error_message

        try:
            self.probe = await asyncio.to_thread(ffmpeg.probe, self.file_path)
            self._size = await asyncio.to_thread(os.path.getsize, self.file_path)
            # Pre-compute format and stream properties
            self._format_info = self.probe.get('format', {})
            self._streams = self.probe.get('streams', [])
            
            # Run validation
            self._is_valid, self._error_message = self.validate()
        except ffmpeg.Error as e:
            self._is_valid = False
            self._error_message = "Corrupt payload. ffmpeg failed to parse file header."
            
        return self._is_valid, self._error_message

    def get_error_message(self) -> str:
        return self._error_message
        
    def is_valid(self) -> bool:
        return self._is_valid

    def validate_size(self) -> float:
        return float(self._size)

    def validate_duration(self) -> float:
        try:
            return float(self._format_info.get('duration', 0))
        except Exception:
            return 0.0

    def validate_format(self) -> str:
        try:
            return self._format_info.get('format_name', "")
        except Exception:
            return ""

    def validate_video_codec(self) -> str:
        try:
            for stream in self._streams:
                if stream.get('codec_type') == 'video':
                    return stream.get('codec_name', "")
            return ""
        except Exception:
            return ""

    def validate_audio(self) -> dict:
        try:
            for stream in self._streams:
                if stream.get('codec_type') == 'audio':
                    return {
                        'codec_name': stream.get('codec_name', ""),
                        'sample_rate': stream.get('sample_rate', 0),
                        'channels': stream.get('channels', 0),
                    }
            return None
        except Exception:
            return None

    def validate_resolution(self) -> Tuple[int, int]:
        try:
            for stream in self._streams:
                if stream.get('codec_type') == 'video':
                    video_width = int(stream.get('width', 0))
                    video_height = int(stream.get('height', 0))
                    return video_width, video_height
            return None
        except Exception:
            return None

    def validate_framerate(self) -> float:
        try:
            for stream in self._streams:
                if stream.get('codec_type') == 'video':
                    fps_string = stream.get('r_frame_rate', "0/0")
                    num, den = map(int, fps_string.split('/'))
                    if den == 0:
                        return 0.0
                    return num / den
            return 0.0
        except Exception:
            return 0.0

    def validate(self) -> Tuple[bool, str]:
        current_size = self.validate_size()
        current_duration = self.validate_duration()
        current_format = self.validate_format()
        current_codec = self.validate_video_codec()
        current_audio = self.validate_audio()
        current_res = self.validate_resolution()
        current_fps = self.validate_framerate()

        # Format helper: match e.g. "mp4" format with ".mp4" in ALLOWED_CONTAINERS
        formats_split = [fmt.strip().lower() for fmt in current_format.split(',')]
        is_format_allowed = any(f".{fmt}" in settings.ALLOWED_CONTAINERS for fmt in formats_split)

        # Codec helper: match e.g. "h264" with settings
        is_codec_allowed = current_codec.lower() in settings.ALLOWED_VIDEO_CODECS

        # Audio helper:
        is_audio_allowed = (
            current_audio is not None and 
            current_audio.get('codec_name', '').lower() in settings.ALLOWED_AUDIO_CODECS
        )

        validation_rules = [
            (
                settings.MIN_FILE_SIZE_BYTES <= current_size <= settings.MAX_FILE_SIZE_BYTES,
                f"File size out of bounds ({settings.MIN_FILE_SIZE_BYTES}B - {settings.MAX_FILE_SIZE_BYTES}B). Current: {current_size}"
            ),
            (
                settings.MIN_DURATION_SECONDS <= current_duration <= settings.MAX_DURATION_SECONDS,
                f"Invalid video duration. Must be between {settings.MIN_DURATION_SECONDS}s and {settings.MAX_DURATION_SECONDS}s. Current: {current_duration}s"
            ),
            (
                is_format_allowed,
                f"Unsupported container format ({current_format}). Allowed: {list(settings.ALLOWED_CONTAINERS)}."
            ),
            (
                is_codec_allowed,
                f"Unsupported video codec ({current_codec}). Allowed: {list(settings.ALLOWED_VIDEO_CODECS)}."
            ),
            (
                is_audio_allowed,
                f"Video must contain a valid audio track. Allowed codecs: {list(settings.ALLOWED_AUDIO_CODECS)}."
            ),
            (
                current_res is not None and (
                    (settings.MIN_RESOLUTION_WIDTH <= current_res[0] <= settings.MAX_RESOLUTION_WIDTH and
                     settings.MIN_RESOLUTION_HEIGHT <= current_res[1] <= settings.MAX_RESOLUTION_HEIGHT) or
                    (settings.MIN_RESOLUTION_HEIGHT <= current_res[0] <= settings.MAX_RESOLUTION_HEIGHT and
                     settings.MIN_RESOLUTION_WIDTH <= current_res[1] <= settings.MAX_RESOLUTION_WIDTH)
                ),
                f"Resolution not supported ({current_res[0] if current_res else 0}x{current_res[1] if current_res else 0}). "
                f"Supported range: {settings.MIN_RESOLUTION_WIDTH}x{settings.MIN_RESOLUTION_HEIGHT} up to {settings.MAX_RESOLUTION_WIDTH}x{settings.MAX_RESOLUTION_HEIGHT}."
            ),
            (
                settings.MIN_FPS <= current_fps <= settings.MAX_FPS,
                f"Unacceptable frame rate ({current_fps:.2f} FPS). Supported range: {settings.MIN_FPS} - {settings.MAX_FPS} FPS."
            )
        ]

        for is_passed, error_message in validation_rules:
            if not is_passed:
                return False, error_message

        return True, "All validation checks passed successfully!"
