import asyncio
import logging
import os

# Import your real service and real client
from audio_extraction.audio_extractor import AudioExtractionService
from audio_extraction.ffmpeg_client import AsyncFFmpegClient

logging.basicConfig(level=logging.INFO)


async def main():
    # 1. Point to your ACTUAL video file (from your screenshot)
    video_file = "أنا_حزين_والله_العظيم_تلاتة_حزين_جدا.mp4"
    output_directory = "./output_audio"

    # 2. Instantiate the REAL FFmpeg client instead of the dummy
    real_ffmpeg_client = AsyncFFmpegClient()

    # 3. Pass the real client into your service
    service = AudioExtractionService(ffmpeg_client=real_ffmpeg_client)

    print("--- Starting REAL Audio Extraction ---")
    try:
        # 4. Process the video
        resulting_file = await service.process_video(video_file, output_directory)
        print(f"SUCCESS: Real audio saved to -> {resulting_file}")

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())