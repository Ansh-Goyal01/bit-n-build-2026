"""One-time Gemini transcription of the scanned PMS-SC guidelines PDF.

The official Dept. of Social Justice & Empowerment guidelines PDF has no text
layer. Gemini (multimodal) transcribes it to markdown; the result is cached to
data/raw/pms-sc-transcript.md, committed, and human spot-checked against the
source PDF, whose URL stays in the corpus provenance.
"""

from google import genai
from google.genai import types

from app.config import settings

PROMPT = """Transcribe this scanned Government of India scheme guidelines document to clean
markdown, verbatim. Rules:
- Preserve the original paragraph/clause numbering exactly (e.g. "4.1", "(i)").
- Use markdown headings (##) for the document's section headings.
- Transcribe the main body fully. For large tabular annexures, transcribe the
  annexure heading and a one-line note "[table not transcribed]" instead of the table.
- Mark anything unreadable as [illegible]. Do not paraphrase, summarise, or add anything."""


def run_transcribe() -> None:
    out_path = settings.raw_dir / "pms-sc-transcript.md"
    if out_path.exists():
        print(f"SKIP transcription: {out_path} exists")
        return
    pdf_bytes = (settings.raw_dir / "pms-sc.pdf").read_bytes()
    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(max_output_tokens=60000, temperature=0),
    )
    out_path.write_text(response.text, encoding="utf-8")
    print(f"TRANSCRIBED -> {out_path} ({len(response.text)} chars)")


if __name__ == "__main__":
    run_transcribe()
