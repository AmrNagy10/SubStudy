import logging
from .base_exporter import BaseExporter
from .exceptions import InvalidDataError, FileWriteError

logger = logging.getLogger(__name__)


class SRTExporter(BaseExporter):
    """
    مستخرج ملفات الترجمة بصيغة SRT القياسية.
    يتعامل مع ترميز النصوص وتحويل التوقيتات بدقة عالية وحماية ضد أخطاء الكتابة.
    """

    def export(self, data: list, output_path: str) -> str:
        """
        تصدير قائمة النصوص والتوقيتات إلى ملف .srt

        :param data: قائمة قواميس مثل: [{'start': 1.2, 'end': 3.5, 'text': 'مرحباً'}]
        :param output_path: المسار النهائي لحفظ ملف الـ SRT
        :return: مسار الملف الذي تم حفظه
        """
        # 1. التحقق الدفاعي من صحة البيانات (Data Validation)
        if not data:
            logger.error("❌ Cannot export SRT: Provided data list is empty.")
            raise InvalidDataError("The data list for SRT export cannot be empty.")

        logger.info(f"💾 Prepared to export {len(data)} segments to SRT: {output_path}")

        # 2. التأكد من وجود المجلدات (Self-healing directory check)
        self._ensure_directory_exists(output_path)

        # 3. فتح الملف والكتابة بصيغة UTF-8 الصارمة
        try:
            with open(output_path, "w", encoding="utf-8") as srt_file:
                for index, segment in enumerate(data, 1):

                    # التحقق من وجود المفاتيح الأساسية في القاموس
                    if not all(k in segment for k in ('start', 'end', 'text')):
                        raise InvalidDataError(f"Segment at index {index} is missing required keys (start, end, text).")

                    start_time = segment['start']
                    end_time = segment['end']
                    text = segment['text'].strip()

                    # معالجة منطقية: التأكد من أن وقت النهاية ليس قبل وقت البداية
                    if end_time < start_time:
                        logger.warning(
                            f"⚠️ Paradoxical timestamps at block {index}: start={start_time}, end={end_time}. Adjusting end time.")
                        end_time = start_time

                    # تحويل الثواني (float) إلى الصيغة النصية للـ SRT
                    start_str = self._format_timestamp(start_time)
                    end_str = self._format_timestamp(end_time)

                    # كتابة البلوك بالصيغة القياسية للـ SRT
                    srt_file.write(f"{index}\n")
                    srt_file.write(f"{start_str} --> {end_str}\n")
                    srt_file.write(f"{text}\n\n")  # السطر الفارغ الإجباري بين كل بلوك والتالي

            logger.info(f"🎉 SRT file successfully generated and saved at: {output_path}")
            return output_path

        except InvalidDataError:
            # إعادة توجيه أخطاء البيانات لتلتقطها الطبقات الأعلى
            raise
        except Exception as e:
            logger.error(f"❌ Core system failed to write SRT file at {output_path}: {e}")
            raise FileWriteError(f"Failed to write SRT file due to I/O error: {e}") from e

    def _format_timestamp(self, seconds: float) -> str:
        """
        دالة مساعدة لتحويل الثواني الرقمية إلى صيغة SRT الصارمة: HH:MM:SS,mmm
        """
        # حساب أجزاء الألف من الثانية (Milliseconds) مع التقريب لأقرب رقم صحييح
        milliseconds = int(round((seconds % 1) * 1000))

        # حماية هندسية (Edge Case): إذا كان التقريب يرفع الـ Milliseconds لـ 1000 كاملة،
        # نقوم بزيادة ثانية كاملة وإعادة تعيين الـ Milliseconds لصفر لتفادي صيغ مثل "00:00:05,1000"
        if milliseconds == 1000:
            seconds += 1
            milliseconds = 0

        # حساب الساعات والدقائق والثواني الأساسية
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        # إعادة النص بالفورمات المحدد، مع إضافة أصفار جهة اليسار إذا كانت الأرقام خانة واحدة
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"