import os
import uuid
import logging
from .ffmpeg_client import AsyncFFmpegClient
from .exceptions import AudioExtractionError, FFmpegExecutionError, AudioTimeoutError
from .audio_config import AUDIO_CHANNELS, TARGET_RATE, OUTPUT_FORMAT
logger = logging.getLogger(__name__)

class AudioExtractionService:
    def __init__(self, ffmpeg_client: AsyncFFmpegClient):
        self.ffmpeg_client = ffmpeg_client

        logger.info(
            "AudioExtractionService is initialized",
        )

    async def process_video(self, video_path: str, output_dir: str) -> str:
        if os.path.exists(video_path) is False:
            raise AudioExtractionError("Input video file not found.")
        os.makedirs(output_dir, exist_ok=True)
        filename = self.generate_unique_filename()
        output_path = os.path.join(output_dir, filename)
        await self.extract_audio(video_path,
                                 output_path
        )

        return output_path

    async def extract_audio(self, video_path, output_path):
        try:
            await self.ffmpeg_client.extract_audio(
                input_path=video_path,
                output_path=output_path,
                target_rate=TARGET_RATE,
                channels=AUDIO_CHANNELS
            )
            logger.info("Audio Extraction Done Correctly. ",
                        extra={
                            "input path" : video_path,
                            "Output path" : output_path,
                            "target rate" : TARGET_RATE,
                            "channels" : AUDIO_CHANNELS,
                        })
        except (FFmpegExecutionError , AudioTimeoutError) as e:
            logger.error(
                "Audio extraction failed due to a specific client error.",
                extra={
                    "input_path": video_path,
                    "output_path": output_path,
                    "error": str(e)
                }
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error occurred during audio extraction.",
                extra={
                    "input_path": video_path,
                    "output_path": output_path,
                    "error": str(e)
                }
            )
            raise AudioExtractionError(f"Unexpected extraction failure: {str(e)}") from e


    def generate_unique_filename(self):
        uniq_id = uuid.uuid4().hex

        return f"audio_{uniq_id}.{OUTPUT_FORMAT}"





