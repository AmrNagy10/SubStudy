import os
import logging
import asyncio
import aiofiles
from uuid import UUID

from src.core.config import settings
from src.pipeline.state_manager import data_store

# Domain-specific components
from src.core.video_validator import VideoValidator
from src.audio_extraction.audio_extractor import AudioExtractionService
from src.audio_extraction.ffmpeg_client import AsyncFFmpegClient
from src.vad.vad_config import SileroVADConfig
from src.vad.vad_client import SileroVADClient
from src.vad.vad_service import SileroVADService
from src.stt.stt_client import STTClient
from src.stt.stt_service import STTService
from src.exporters.srt_exporter import SRTExporter
from src.translation.translation_service import TranslationService
from src.analytics.analyzer_service import AIAnalyzerService

logger = logging.getLogger(__name__)


async def _is_canceled(job_id: UUID) -> bool:
    job = await data_store.get_job(job_id)
    return True if (job and job.get('status') == 'canceled') else False


async def run_pipeline_job(job_id: UUID, file_path: str, source_lang: str, target_lang: str):
    """
    Sequential execution pipeline traversing Stages 1 to 7 safely.
    Encapsulates lifecycle updates, step validation, and defensive file purging.
    """
    logger.info(f"🔄 Starting Pipeline Job Coordinator for ID: {job_id}")
    await data_store.initialize_job(job_id)

    # Track paths generated during pipeline to wipe them at exit
    extracted_audio_path = None
    original_srt_path = None

    try:
        # ==========================================
        # STAGE 1: Deep Metadata Validation (ffprobe)
        # ==========================================
        await data_store.update_job(job_id, status="processing", progress=5.0)
        if await _is_canceled(job_id):
            logger.info(f"[{job_id}] Canceled before Stage 1; aborting pipeline.")
            return
        logger.info(f"[{job_id}] Stage 1: Running deep structural validation...")

        validator = VideoValidator(file_path)
        is_valid, err_msg = await validator.validate_async()
        if not is_valid:
            raise ValueError(f"Validation Matrix Failed: {err_msg}")

        # ==========================================
        # STAGE 2: Audio Demuxing & Extraction (16kHz Mono WAV)
        # ==========================================
        await data_store.update_job(job_id, status="processing", progress=15.0)
        if await _is_canceled(job_id):
            logger.info(f"[{job_id}] Canceled before Stage 2; aborting pipeline.")
            return
        logger.info(f"[{job_id}] Stage 2: Extracting standard 16kHz mono audio payload...")

        ffmpeg_client = AsyncFFmpegClient()
        extractor = AudioExtractionService(ffmpeg_client=ffmpeg_client)
        extracted_audio_path = os.path.join(settings.TEMP_DIR, f"{job_id}_extracted.wav")

        # Extract track
        await extractor.extract_audio(
            video_path=file_path,
            output_path=extracted_audio_path
        )

        # ==========================================
        # STAGE 3: Voice Activity Detection (Silero VAD)
        # ==========================================
        await data_store.update_job(job_id, status="processing", progress=35.0)
        if await _is_canceled(job_id):
            logger.info(f"[{job_id}] Canceled before Stage 3; aborting pipeline.")
            return
        logger.info(f"[{job_id}] Stage 3: Segmenting active voice intervals via Silero VAD...")

        vad_config = SileroVADConfig()
        vad_client = SileroVADClient(config=vad_config)
        vad_service = SileroVADService(config=vad_config, client=vad_client)
        
        await vad_client.load_model()
        speech_segments = await vad_service.process_audio_file(extracted_audio_path)

        if not speech_segments:
            raise ValueError("No speech segments detected in the audio payload.")

        # ==========================================
        # STAGE 4: Automated Speech Recognition (faster-whisper)
        # ==========================================
        await data_store.update_job(job_id, status="processing", progress=55.0)
        if await _is_canceled(job_id):
            logger.info(f"[{job_id}] Canceled before Stage 4; aborting pipeline.")
            return
        logger.info(f"[{job_id}] Stage 4: Transcribing segments using faster-whisper core runtime...")

        stt_client = STTClient()
        stt_worker = STTService(stt_client=stt_client)
        
        stt_lang = None
        if source_lang == "English":
            stt_lang = "en"
        elif source_lang == "Arabic":
            stt_lang = "ar"

        raw_transcript_data = await stt_worker.process_audio(
            audio_path=extracted_audio_path,
            speech_segments=speech_segments,
            language=stt_lang
        )

        # ==========================================
        # STAGE 5: SRT Export and Translation
        # ==========================================
        await data_store.update_job(job_id, status="processing", progress=75.0)
        if await _is_canceled(job_id):
            logger.info(f"[{job_id}] Canceled before Stage 5; aborting pipeline.")
            return
        logger.info(f"[{job_id}] Stage 5: Exporting original subtitles and translating...")

        exporter = SRTExporter()
        original_srt_path = os.path.join(settings.TEMP_DIR, f"{job_id}_original.srt")
        exporter.export(data=raw_transcript_data, output_path=original_srt_path)

        async with aiofiles.open(original_srt_path, "r", encoding="utf-8") as f:
            original_srt_content = await f.read()

        # Get translation credentials
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required.")

        translator = TranslationService(
            api_base_url="https://models.inference.ai.azure.com",
            api_key=github_token,
            model="gpt-4o",
            chunk_size=15
        )
        
        trans_source = "English" if source_lang == "Auto" else source_lang
        try:
            translated_srt = await translator.translate_srt(
                srt_content=original_srt_content,
                source_lang=trans_source,
                target_lang=target_lang
            )
        finally:
            await translator.close()

        # Extract translated texts for payload representation
        try:
            dummy_translator = TranslationService(api_base_url="", api_key="", model="")
            translated_blocks = dummy_translator._parse_srt(translated_srt)
            translated_text = " ".join([block["text"] for block in translated_blocks])
        except Exception as e:
            logger.warning(f"Could not parse translated SRT back to text: {e}")
            translated_text = ""

        # ==========================================
        # STAGE 6 & 7: Semantic Analysis (Summary)
        # ==========================================
        await data_store.update_job(job_id, status="processing", progress=90.0)
        if await _is_canceled(job_id):
            logger.info(f"[{job_id}] Canceled before Stages 6-7; aborting pipeline.")
            return
        logger.info(f"[{job_id}] Stages 6-7: Compiling semantic summaries...")

        full_transcript_text = " ".join([seg["text"] for seg in raw_transcript_data])

        analyzer = AIAnalyzerService()
        try:
            summary_result = await analyzer.generate_summary(full_transcript_text)
        finally:
            await analyzer.close()

        # ==========================================
        # SUCCESS PIPELINE TERMINATION
        # ==========================================
        final_payload = {
            "transcripts": {
                "source": full_transcript_text,
                "translated": translated_text
            },
            "srt_output": translated_srt,
            "analysis": {
                "short_summary": summary_result.short_summary,
                "detailed_points": summary_result.detailed_summary,
                "keywords": []
            }
        }

        await data_store.update_job(job_id, status="completed", progress=100.0, result=final_payload)
        logger.info(f"✅ Pipeline complete. Results mapped for Job ID: {job_id}")

    except Exception as error:
        logger.error(f"❌ Core processing failure on job {job_id}: {str(error)}", exc_info=True)
        current = await data_store.get_job(job_id)
        if current and current.get('status') == 'canceled':
            logger.info(f"Job {job_id} was canceled by user. Skipping failure update.")
        else:
            await data_store.update_job(
                job_id,
                status="failed",
                progress=100.0,
                error_message=f"Pipeline processing halted: {str(error)}"
            )

    finally:
        # ==========================================
        # DEFENSIVE STORAGE CLEANUP BOUNDARY
        # ==========================================
        logger.info(f"🧹 Commencing defensive isolation cleanup for job {job_id}...")

        # 1. Clear original file ingest
        if await asyncio.to_thread(os.path.exists, file_path):
            await asyncio.to_thread(os.remove, file_path)

        # 2. Clear extracted intermediate WAV
        if extracted_audio_path and await asyncio.to_thread(os.path.exists, extracted_audio_path):
            await asyncio.to_thread(os.remove, extracted_audio_path)

        # 3. Clear original SRT file
        if original_srt_path and await asyncio.to_thread(os.path.exists, original_srt_path):
            await asyncio.to_thread(os.remove, original_srt_path)

        logger.info(f"✨ Safe memory state preserved. All intermediate files purged.")