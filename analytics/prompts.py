# قالب التلخيص الذكي (Short & Detailed Summary)
# يضمن هذا القالب استخراج الملخصات باللغة العربية وبصيغة JSON صارمة

SUMMARY_PROMPT_TEMPLATE = """
You are a highly precise audio-transcript analysis engine.
Your sole purpose is to read the provided video transcript and compress it semantically into a structured JSON response.

Video Transcript:
\"\"\"
{transcript_text}
\"\"\"

You MUST respond ONLY with a valid JSON object matching this EXACT format:
{{
  "short_summary": "A highly concise paragraph (15-30 words) in Arabic outlining the overall core theme of the video.",
  "detailed_summary": [
    "النقطة الأولى: تلخيص دقيق ومحترف للجزئية الأولى من الفيديو.",
    "النقطة الثانية: تلخيص الفكرة التالية المطروحة في الفيديو باللغة العربية.",
    "النقطة الثالثة: تلخيص فكرة هامة أخرى.",
    "النقطة الرابعة: الاستنتاج أو الخاتمة التي انتهى إليها المقطع."
  ]
}}

CRITICAL RULES:
1. All generated text (short_summary and detailed_summary) MUST be in Arabic.
2. `detailed_summary` MUST be a JSON array containing EXACTLY 4 strings.
3. DO NOT include any introductory greetings, markdown formatting (like ```json), or any explanations outside the JSON block.
4. If the transcript is mostly silence or meaningless, output a JSON stating that no clear context was found.
"""

# قالب الترجمة (مجهز للمستقبل القريب لتنفيذ FR-7)
TRANSLATION_PROMPT_TEMPLATE = """
You are a highly accurate context-aware subtitle translator.
Translate the following JSON array of subtitle segments from {source_lang} to {target_lang}.

Segments:
\"\"\"
{segments_json}
\"\"\"

You MUST return a JSON array with the exact same number of items, keeping the 'id', 'start', and 'end' values strictly intact.
Only translate the 'text' field.
Respond ONLY with the JSON array.
"""