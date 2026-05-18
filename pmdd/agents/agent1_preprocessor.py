"""
Agent 1: Corpus Preprocessor & Segmenter
Linguistic Approach: Sinclair's Corpus Linguistics methodology
"""

import re
import json
import spacy
from pathlib import Path


# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    try:
        import en_core_web_sm
        nlp = en_core_web_sm.load()
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            import en_core_web_sm
            nlp = en_core_web_sm.load()


def _clean_text(raw: str) -> str:
    """Remove HTML, excessive whitespace, and control characters."""
    text = re.sub(r"<[^>]+>", " ", raw)               # HTML tags
    text = re.sub(r"[^\x20-\x7E\n\r\t]", " ", text)   # Non-ASCII
    text = re.sub(r"\r\n|\r", "\n", text)               # Normalize line endings
    text = re.sub(r"[ \t]{2,}", " ", text)              # Excessive spaces
    text = re.sub(r"\n{3,}", "\n\n", text)              # Excessive newlines
    return text.strip()


def _detect_sections(text: str) -> list[str]:
    """
    Heuristic section splitter: split on double newlines / headings.
    Returns a list of section blocks.
    """
    blocks = re.split(r"\n{2,}", text)
    return [b.strip() for b in blocks if len(b.strip()) > 30]


def run_agent1(file_path: str, source_name: str = "uploaded_corpus") -> dict:
    """
    Main entry point for Agent 1.
    Returns structured JSON with corpus stats and segments.
    """
    path = Path(file_path)
    raw = path.read_text(encoding="utf-8", errors="replace")

    # Clean
    cleaned = _clean_text(raw)

    # Section-level split for temporal/genre analysis
    sections = _detect_sections(cleaned)

    segments = []
    seg_id = 0

    for sec_idx, section in enumerate(sections):
        # spaCy sentence tokenization (max 1M chars per chunk for memory safety)
        chunk = section[:500_000]
        doc = nlp(chunk)
        sents = list(doc.sents)
        total_sents = len(sents)

        for sent_idx, sent in enumerate(sents):
            text = sent.text.strip()
            if len(text) < 5:
                continue
            tokens = [t for t in sent if not t.is_space and not t.is_punct]
            content_words = [t.lemma_.lower() for t in tokens if not t.is_stop and t.is_alpha]

            segments.append({
                "id": seg_id,
                "text": text,
                "section": sec_idx,
                "section_label": f"Section {sec_idx + 1}",
                "position": round(sent_idx / max(total_sents, 1), 3),
                "word_count": len(tokens),
                "content_words": content_words[:20],  # top 20 for downstream agents
                "char_count": len(text),
            })
            seg_id += 1

    total_words = sum(s["word_count"] for s in segments)
    all_tokens = [w for s in segments for w in s["content_words"]]
    unique_tokens = set(all_tokens)
    ttr = round(len(unique_tokens) / max(len(all_tokens), 1), 4)

    corpus_stats = {
        "source": source_name,
        "total_segments": len(segments),
        "total_sections": len(sections),
        "total_words": total_words,
        "unique_words": len(unique_tokens),
        "type_token_ratio": ttr,
        "avg_segment_length": round(total_words / max(len(segments), 1), 1),
    }

    return {
        "corpus_stats": corpus_stats,
        "segments": segments,
    }
