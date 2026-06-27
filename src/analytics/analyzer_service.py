import re
import os
import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# استدعاء الأخطاء والقوالب التي أنشأناها مسبقاً
from .exceptions import LLMConnectionError, OutputParsingError, PromptValidationError
from .prompts import SUMMARY_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """
    نموذج بيانات (Data Class) يحفظ مخرجات التلخيص بشكل آمن وثابت.
    يضمن تنظيم مخرجات التلخيص ومطابقتها لمتطلبات الـ PRD (خاصية FR-6).
    """
    short_summary: str
    detailed_summary: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AIAnalyzerService:
    """
    الخدمة الرئيسية للتواصل مع نماذج اللغات الكبيرة (LLM).
    مدمجة ومطورة بأعلى معايير الحماية (Defensive Programming) والـ Performance.
    """

    def __init__(self):
        # تطبيق مبدأ Fail Fast: التحقق الصارم من التوكن قبل قيام الخدمة
        self.github_token = os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required.")

        self.endpoint = os.getenv("LLM_ENDPOINT", "https://models.inference.ai.azure.com/chat/completions")
        self.model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o")

        # استخدام العميل المستمر (Persistent Client) لتوفير تكرار فتح الاتصالات والـ Overhead
        self.http_client = httpx.AsyncClient(timeout=45.0)

    async def close(self):
        """إغلاق عميل HTTP بأمان لتجنب تسريب الموارد في الـ Pipeline."""
        await self.http_client.aclose()

    async def _send_llm_request(self, prompt: str) -> dict:
        """
        [دالة داخلية] مسؤولة عن إرسال الطلب عبر العميل المستمر وإدارة أخطاء الشبكة.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.github_token}",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise data-processing API. Always output raw JSON. Never include markdown formatting like ```json."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.0,  # تقليل الحرارة لضمان عدم الهلوسة والالتزام التام بالمنطق
            "response_format": {"type": "json_object"},
        }

        try:
            response = await self.http_client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error("Network error: %s", e)
            raise LLMConnectionError(f"Connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error("LLM API error %d: %s", e.response.status_code, e.response.text)
            raise LLMConnectionError(f"Server error {e.response.status_code}") from e

    def _sanitize_and_parse_json(self, raw_text: str) -> dict:
        """
        [دالة داخلية] لتنظيف النص المستلم باستخدام الـ Regex كحماية أساسية ضد الهلوسة.
        """
        # اصطياد مصفوفة أو كائن الـ JSON مباشرة عبر الـ Regex لضمان تخطي أي نصوص ترحيبية زائدة
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            cleaned = match.group(0).strip()
        else:
            # خطة دفاعية تراجعية (Fallback) في حال فشل الـ Regex
            cleaned = raw_text.replace('```json', '').replace('```', '').strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON. Raw: %s", raw_text)
            raise OutputParsingError("LLM output was not valid JSON.") from e

    async def generate_summary(self, transcript_text: str) -> SummaryResult:
        """
        [الدالة الخدمية الأساسية] توليد تلخيص دلالي (قصير وتفصيلي) متوافق مع الـ PRD ومحمي من الانهيار.
        """
        # 1. التحقق من صحة المدخلات قبل الاستهلاك
        if not transcript_text or len(transcript_text.strip()) < 20:
            raise PromptValidationError("Transcript too short to summarize.")

        # 2. بناء الـ Prompt بأمان عبر .replace() لحمايتنا من الـ Format Injection الـ خبيث
        prompt = SUMMARY_PROMPT_TEMPLATE.replace('{transcript_text}', transcript_text)

        try:
            logger.info("Sending transcript to LLM for semantic analysis...")
            response_data = await self._send_llm_request(prompt)

            # 3. التحقق البنيوي الصارم من هيكل رد الـ API المستلم
            choices = response_data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                raise OutputParsingError("LLM response missing 'choices' array.")

            message = choices[0].get("message", {})
            raw_content = message.get("content", "{}")
            if not raw_content:
                raw_content = "{}"

            # 4. تنظيف وعمل Parse للـ JSON
            parsed = self._sanitize_and_parse_json(raw_content)

            # 5. استخراج البيانات بأمان وضمان القيم الافتراضية للغة الواجهة
            short = parsed.get("short_summary", "لم يتمكن الذكاء الاصطناعي من توليد ملخص قصير.")
            raw_details = parsed.get("detailed_summary", [])

            # معالجة المصفوفات والنصوص المستخرجة لمنع الـ Type Mismatch
            if isinstance(raw_details, list):
                detail_points = [str(item) for item in raw_details]
            elif isinstance(raw_details, str):
                detail_points = [line.strip() for line in raw_details.split('\n') if line.strip()]
            else:
                detail_points = []

            # 6. الـ Array Padding/Trimming لضمان ثبات الواجهات البرمجية على 4 عناصر بالضبط
            while len(detail_points) < 4:
                detail_points.append("بيانات تفصيلية غير متاحة للمقطع الحالي.")
            detail_points = detail_points[:4]

            logger.info("Summary generated and validated successfully.")
            return SummaryResult(short_summary=short, detailed_summary=detail_points)

        except (LLMConnectionError, OutputParsingError) as e:
            # 7. الـ Graceful Degradation (الخطة البديلة النظيفة لحماية التطبيق من الكراش الكلي)
            logger.warning("Graceful degradation triggered due to: %s", e, exc_info=True)
            return SummaryResult(
                short_summary="فشل التحليل الذكي 🔌",
                detailed_summary=[
                    "تعذر استخراج النقاط التفصيلية بسبب خطأ في المعالجة السحابية.",
                    "يرجى التأكد من اتصال الإنترنت وصلاحية مفتاح GITHUB_TOKEN.",
                    "النظام حمى نفسه لمنع الانهيار الكامل للمشروع (Crash).",
                    "يمكنك إعادة المحاولة لاحقاً واختبار الـ API."
                ]
            )