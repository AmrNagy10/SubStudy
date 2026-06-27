# Strict system prompt enforcing SubRip format preservation
TRANSLATION_SYSTEM_PROMPT = (
    "You are an expert linguistic translator specializing in maintaining SubRip (.srt) file structures. "
    "Your task is to translate the text content of the provided SRT blocks from {source_lang} to {target_lang}.\n\n"
    "STRICT RULES:\n"
    "1. DO NOT alter, merge, or split the numeric IDs of the SRT blocks.\n"
    "2. DO NOT alter, reformat, or lose the timestamp lines (e.g., 00:00:01,000 --> 00:00:04,000).\n"
    "3. Translate ONLY the text payload beneath the timestamp line.\n"
    "4. Maintain the original tone, context, and meaning.\n"
    "5. Return ONLY the valid SRT formatted text. No markdown, no explanations."
)


def build_translation_prompt(source_lang: str, target_lang: str, srt_chunk: str) -> str:
    """
    Constructs the user prompt safely using string replacement.
    We avoid .format() or f-strings because LLM outputs or transcripts
    may contain unescaped curly braces {} which would crash formatting.
    """
    prompt = TRANSLATION_SYSTEM_PROMPT.replace("{source_lang}", source_lang)
    prompt = prompt.replace("{target_lang}", target_lang)

    # Append the chunk to be translated
    full_prompt = f"{prompt}\n\nSRT Chunk to Translate:\n{srt_chunk}"
    return full_prompt