import os
import logging
from abc import ABC, abstractmethod
from .exceptions import FileWriteError

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    def _ensure_directory_exists(self, output_path: str):
        """
        دالة مساعدة للتأكد من وجود المجلد الذي سيتم حفظ الملف فيه.
        تقوم بإنشاء المجلدات الفرعية تلقائياً إذا لم تكن موجودة (Self-healing).
        """
        directory = os.path.dirname(output_path)

        # إذا كان المسار يحتوي على مجلدات (ليس فقط اسم ملف في المسار الحالي)
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                logger.error(f"❌ Failed to create directory '{directory}': {e}")
                raise FileWriteError(f"Could not create output directory: {e}") from e

    @abstractmethod
    def export(self, data: list, output_path: str) -> str:
        """
        الدالة الأساسية للتصدير.
        يجب على كل كلاس يرث من BaseExporter أن يكتب الكود الخاص به هنا.

        :param data: قائمة القواميس التي تحتوي على (start, end, text).
        :param output_path: مسار حفظ الملف النهائي.
        :return: المسار النهائي للملف الذي تم حفظه.
        """
        pass