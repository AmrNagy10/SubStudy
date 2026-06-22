import os
import asyncio
import logging
from .exceptions import AudioTimeoutError, AudioExtractionError, FFmpegExecutionError
from .audio_config import FFMPEG_BINARY_PATH, PROCESS_TIMEOUT_SECONDS, TARGET_RATE, AUDIO_CHANNELS

logger = logging.getLogger(__name__)

class AsyncFFmpegClient:
    def __init__(self, binary_path=None, process_timeout=None):
        self.BINPATH = binary_path or FFMPEG_BINARY_PATH
        self.TIMEOUT = process_timeout or PROCESS_TIMEOUT_SECONDS

        logger.info("AsyncFFmpegClient is initialized ",
                    extra={"binary_path": self.BINPATH, "timeout": self.TIMEOUT})

    async def extract_audio(self, input_path: str, output_path: str, target_rate, channels):
        target_rate = target_rate or TARGET_RATE
        channels = channels or AUDIO_CHANNELS
        command = [self.BINPATH, "-i", input_path,
                       "-vn", "-acodec", "pcm_s16le",
                       "-ar", str(target_rate), "-ac",
                   str(channels), str(output_path)]

        process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
        )

        logger.info("FFmpeg, Start Extracting audio", extra={
            "input_path": input_path,
            "output_path": output_path,
            "target_rate": target_rate,
            "channels": channels,
            "command": " ".join(command)
        })

        try:
                stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.TIMEOUT
                )

                logger.info("asyncio, Subprocess is done ", extra={
                    "input_path": input_path,
                    "output_path": output_path,
                    "target_rate": target_rate,
                    "channels": channels,
                    "command": " ".join(command)
                })
                if (process.returncode == 0):
                    logger.info("asyncio and FFmpeg, The audio process is done correctly and returns 0 ", extra={
                        "input_path": input_path,
                        "output_path": output_path,
                        "target_rate": target_rate,
                        "size": os.path.getsize(output_path) if os.path.exists(output_path) else 0
                    })

                else:
                    error_msg = stderr.decode().strip() if stderr else "Unknown error"
                    logger.error(
                        "Error occur while audio Extraction",
                        extra={"returncode": process.returncode,
                        "error": error_msg,
                        "input_path": input_path

                    })
                    raise FFmpegExecutionError(f"FFmpeg failed with code {process.returncode}")

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.error("Timeout Error happens while audio Extraction ", extra={
                "input_path": input_path,
                "timeout_seconds": self.TIMEOUT
            })
            raise AudioTimeoutError(f"FFmpeg operation timed out after {self.TIMEOUT} seconds")



