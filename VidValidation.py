import os
import ffmpeg

class VideoMetadataExtractor:
    def __init__(self, file_path):
        self.file_path = self.name = file_path
        self.duration=0
        self.size=0
        self.fps = 0
        self.format = ""
        self.codec = ""
        self.audstream ={}
        self.resolution = []

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at: {file_path}")

        try:
            self.probe = ffmpeg.probe(self.file_path)
        except ffmpeg.Error as e:
            raise ValueError("Corrupted video file or invalid media format.") from e

    def sizeValid(self):
        try:
            size = os.path.getsize(self.name)
            return size
        except (OSError, Exception):
            return None

    def duratuionValidation(self):
        try:
            duration = float(self.probe['format']['duration'])
            return duration

        except Exception as e:
            return None

    def formatintVal(self):
        try:
            format = self.probe['format']['format_name']
            return format
        except Exception:
            return None

    def vidCodec(self):
        try:
            for stream in self.probe['streams']:
                if stream.get('codec_type') == 'video':
                    format = stream['codec_name']
                    return format

        except Exception:
            return None

    def AudioVaildation(self):
        try:
            for stream in self.probe.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    return {
                        'codec_name': stream.get('codec_name'),
                        'sample_rate': stream.get('sample_rate'),
                        'channels': stream.get('channels'),
                    }
        except Exception:
            return None

    def ResolutionVali(self):
        try:
            for stream in self.probe['streams']:
                if stream['codec_type'] == 'video':
                    video_width = stream['width']
                    video_height = stream['height']
                    return [video_width, video_height]
        except Exception:
            return None

    def FrameRate(self):
        try:
            for stream in self.probe['streams']:
                if stream['codec_type'] == 'video':
                    fps_string = stream['r_frame_rate']
                    num, den = map(int, fps_string.split('/'))

                    if den == 0:
                        return None

                    fps = num / den
                    return fps
        except Exception:
            return None

    def Full_validation(self):
        ALLOWED_FORMATS = {'mp4', 'mkv', 'mov', 'avi', 'webm'}
        ALLOWED_CODECS = {'h264', 'hevc', 'av1', 'vp9', 'mpeg2', 'mpeg4', 'prores', 'vp8'}
        ALLOWED_AUDIO_CODECS = {'aac', 'mp3'}

        current_size = self.sizeValid()
        current_duration = self.duratuionValidation()
        current_format = self.formatintVal()
        current_codec = self.vidCodec()
        current_audio = self.AudioVaildation()
        current_res = self.ResolutionVali()
        current_fps = self.FrameRate()

        validation_rules = [
            (
                current_size is not None and (10 * 1024 <= current_size <= 500 * 1024 * 1024),
                f"File size out of bounds (10KB - 500MB). Current: {current_size}"
            ),
            (
                current_duration is not None and (3 <= current_duration <= 600),
                f"Invalid video duration. Must be between 3s and 10m. Current: {current_duration}s"
            ),
            (
                current_format is not None and any(fmt in current_format.split(',') for fmt in ALLOWED_FORMATS),
                f"Unsupported container format ({current_format}). Allowed: MP4, MKV, MOV, AVI, WEBM."
            ),
            (
                current_codec in ALLOWED_CODECS,
                f"Unsupported video codec ({current_codec}). Please use H.264 or H.265."
            ),
            (
                current_audio is not None and current_audio.get('codec_name') in ALLOWED_AUDIO_CODECS,
                "Video must contain a valid audio track (AAC/MP3 supported)."
            ),
            (
                current_res is not None and (240 <= current_res[0] <= 3840 and 240 <= current_res[1] <= 3840),
                f"Resolution not supported ({current_res[0]}x{current_res[1]}). Supported range: 240p up to 4K (Landscape or Portrait)."
            ),
            (
                current_fps is not None and (24 <= current_fps <= 60),
                f"Unacceptable frame rate ({current_fps} FPS). Supported range: 24 - 60 FPS."
            )
        ]

        # 4. الـ Loop الذكية: التحقق من الشروط بالتوالي
        for is_passed, error_message in validation_rules:
            if not is_passed:

                return False, error_message

        return True, "All validation checks passed successfully!"

