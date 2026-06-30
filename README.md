# SubStudy

Turn any video into transcripts, translated subtitles, and summaries — with video processing on your machine.

## Privacy model

| Data | Where it goes |
|------|----------------|
| **Video / audio file** | Stays on your machine (`tmp_uploads/` during processing) |
| **Transcript & subtitle text** | Sent to **GitHub Models** (primary) or **Google Gemini** (fallback) for translation and summarization |
| **Job metadata** | Stored locally in SQLite (`substudy_jobs.db`) |

Video is never uploaded to the cloud. Text from Stages 5–6 is sent to the LLM API when `GITHUB_TOKEN` is configured.

## Prerequisites

- **Python 3.10+**
- **ffmpeg** and **ffprobe** on your `PATH`
- **GitHub token** with access to [GitHub Models](https://github.com/marketplace/models) (primary LLM)
- **Google Gemini API key** (recommended fallback when GitHub rate-limits) — [get one here](https://aistudio.google.com/apikey)
- Optional: **NVIDIA GPU + CUDA** for faster speech-to-text (`DEVICE=cuda` in `.env`)

### System packages (Ubuntu/Debian)

```bash
sudo apt update && sudo apt install -y ffmpeg python3-venv python3-pip
```

## Quick start

```bash
git clone <your-repo-url> substudy && cd substudy

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set GITHUB_TOKEN
```

Start the server (serves API **and** the web UI):

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

## Environment variables

Copy `.env.example` to `.env`. Key settings:

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | Yes* | GitHub Models API token (primary) |
| `GEMINI_API_KEY` | Yes* | Google Gemini fallback when GitHub fails or returns 429 |
| `GEMINI_MODEL` | No (default `gemini-2.0-flash`) | Gemini model name |
| `LLM_MIN_REQUEST_INTERVAL` | No (default `6.5`) | Seconds between LLM calls (GitHub limit ≈10/min) |
| `API_KEY` | For remote/scripts | Used when `LOCAL_DEV_MODE=false` |
| `LOCAL_DEV_MODE` | No (default `true`) | Browser on localhost skips API key |
| `MAX_CONCURRENT_JOBS` | No (default `1`) | Only one pipeline at a time |
| `MODEL_SIZE` | No (default `base`) | Whisper model: `tiny`, `base`, `small`, … |
| `DEVICE` | No (default `cpu`) | `cpu` or `cuda` |
| `SILERO_VAD_DIR` | No | Path to Silero VAD clone (default `models/silero-vad`) |

\* At least one of `GITHUB_TOKEN` or `GEMINI_API_KEY` is required.

See `.env.example` for the full list.

## Models

### Silero VAD

Included at `models/silero-vad/`. Verify:

```bash
test -f models/silero-vad/hubconf.py && echo "Silero OK"
```

### Whisper (faster-whisper)

Downloaded automatically on first job. Size depends on `MODEL_SIZE` (e.g. `base` ≈ 150 MB).

First run may take several minutes while models download.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Process liveness |
| `GET` | `/ready` | Dependency checks (Silero path, token, temp dir) |
| `POST` | `/api/v1/process` | Upload video (multipart form) |
| `GET` | `/api/v1/status/{job_id}` | Poll job status |
| `POST` | `/api/v1/cancel/{job_id}` | Cancel a running job |

When `LOCAL_DEV_MODE=true`, browser requests from localhost do not need `X-API-Key`. For curl/scripts with `LOCAL_DEV_MODE=false`:

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/status/<job-id>
```

## Limits (MVP)

- Max file size: **500 MB**
- Max duration: **10 minutes**
- Formats: MP4, MKV, MOV, AVI, WebM
- **One concurrent job** by default (`MAX_CONCURRENT_JOBS=1`)

## Smoke test

With the server running:

```bash
chmod +x scripts/smoke_test.sh
./scripts/smoke_test.sh
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `GITHUB_TOKEN is required` / rate limit 429 | Set `GEMINI_API_KEY` as fallback; increase `LLM_MIN_REQUEST_INTERVAL` if needed |
| Silero model not found | Confirm `models/silero-vad/hubconf.py` exists |
| `librosa not installed` | `pip install librosa` or reinstall requirements |
| Second job returns 503 | Expected — wait for the current job to finish or cancel it |
| Whisper slow on CPU | Use a shorter clip, or set `MODEL_SIZE=tiny`, or enable CUDA |
| ffmpeg not found | Install ffmpeg and ensure it is on `PATH` |

## Project layout

```
main.py                 # FastAPI entry (API + static UI)
frontend-react/         # Web UI (index.html)
src/
  pipeline/             # Orchestrator, job gate, model registry
  stt/                  # faster-whisper
  vad/                  # Silero VAD
  translation/          # LLM subtitle translation
  analytics/            # LLM summarization
models/silero-vad/      # Bundled VAD model
scripts/smoke_test.sh   # Basic health checks
```

## Roadmap (Phase 2)

- Docker + CI
- Dedicated worker queue (Celery/RQ)
- Bundled frontend build (Vite)
- Rate limiting and production auth
- Keyword extraction

## License

See repository license file.
