"""
Agent 4: Corpus Statistician
Linguistic Approach: Corpus Linguistics — Frequency, Collocation (Sinclair 1991),
                     Keyness (Scott 1997), MI Score, Type-Token Ratio.
Pure Python/Pandas — no LLM required.
"""

import math
from collections import Counter, defaultdict
import pandas as pd


def _compute_mi_score(word: str, collocate: str, word_freq: int, collocate_freq: int,
                       cooccur_freq: int, total_tokens: int) -> float:
    """Pointwise Mutual Information (PMI) score."""
    if cooccur_freq == 0:
        return 0.0
    p_w = word_freq / total_tokens
    p_c = collocate_freq / total_tokens
    p_wc = cooccur_freq / total_tokens
    return math.log2(p_wc / (p_w * p_c + 1e-10))


def run_agent4(segments: list[dict]) -> dict:
    """
    Compute quantitative corpus statistics.
    Returns frequency tables, collocations, keyness, and TTR per section.
    """
    # --- Per-section word lists ---
    section_words: dict[int, list[str]] = defaultdict(list)
    all_words: list[str] = []

    for seg in segments:
        sec = seg.get("section", 0)
        words = seg.get("content_words", [])
        section_words[sec].extend(words)
        all_words.extend(words)

    total_tokens = len(all_words)
    global_freq = Counter(all_words)

    # --- Per-section frequency tables ---
    section_stats = {}
    for sec, words in section_words.items():
        freq = Counter(words)
        unique = len(set(words))
        total = len(words)
        ttr = round(unique / max(total, 1), 4)
        top_20 = freq.most_common(20)
        section_stats[sec] = {
            "section": sec,
            "total_words": total,
            "unique_words": unique,
            "type_token_ratio": ttr,
            "top_20_words": [{"word": w, "frequency": f, "relative_freq": round(f / max(total, 1), 4)} for w, f in top_20],
        }

    # --- Keyness: compare each section to the rest of the corpus ---
    sections = list(section_words.keys())
    keyness_tables = {}

    for sec in sections:
        focus_words = Counter(section_words[sec])
        focus_total = max(sum(focus_words.values()), 1)
        reference_words = Counter([w for s, ws in section_words.items() if s != sec for w in ws])
        ref_total = max(sum(reference_words.values()), 1)

        keyness = []
        for word, freq in focus_words.items():
            ref_freq = reference_words.get(word, 0)
            norm_focus = freq / focus_total
            norm_ref = (ref_freq + 1) / ref_total  # +1 smoothing
            log_ratio = math.log2(norm_focus / norm_ref)
            keyness.append({"word": word, "focus_freq": freq, "ref_freq": ref_freq, "keyness_score": round(log_ratio, 3)})

        keyness_sorted = sorted(keyness, key=lambda x: x["keyness_score"], reverse=True)[:15]
        keyness_tables[sec] = keyness_sorted

    # --- Collocation Window Analysis (±5 word window) ---
    # Build flat list of (position, word, section)
    flat_tokens: list[tuple[int, str, int]] = []
    for seg in segments:
        sec = seg.get("section", 0)
        for pos, w in enumerate(seg.get("content_words", [])):
            flat_tokens.append((len(flat_tokens), w, sec))

    target_keywords = [word for word, _ in global_freq.most_common(5)]
    collocations = {}

    for target in target_keywords:
        target_positions = [i for i, (_, w, _) in enumerate(flat_tokens) if w == target]
        collocate_counter = Counter()
        for pos in target_positions:
            window_start = max(0, pos - 5)
            window_end = min(len(flat_tokens), pos + 6)
            for j in range(window_start, window_end):
                if j != pos:
                    collocate_counter[flat_tokens[j][1]] += 1

        target_freq = global_freq[target]
        collocate_data = []
        for collocate, cooccur in collocate_counter.most_common(10):
            mi = _compute_mi_score(
                target, collocate,
                target_freq, global_freq[collocate],
                cooccur, total_tokens
            )
            collocate_data.append({"collocate": collocate, "frequency": cooccur, "mi_score": round(mi, 3)})
        collocations[target] = sorted(collocate_data, key=lambda x: x["mi_score"], reverse=True)

    # --- N-gram Frequency (bigrams) ---
    bigrams = Counter()
    for seg in segments:
        words = seg.get("content_words", [])
        for i in range(len(words) - 1):
            bigrams[(words[i], words[i + 1])] += 1

    top_bigrams = [{"bigram": f"{a} {b}", "frequency": f} for (a, b), f in bigrams.most_common(15)]

    # --- Hapax Legomena ---
    hapax = [w for w, f in global_freq.items() if f == 1]
    hapax_ratio = round(len(hapax) / max(len(global_freq), 1), 4)

    return {
        "total_corpus_tokens": total_tokens,
        "total_unique_tokens": len(global_freq),
        "hapax_legomena_count": len(hapax),
        "hapax_legomena_ratio": hapax_ratio,
        "section_stats": section_stats,
        "keyness_tables": keyness_tables,
        "collocations": collocations,
        "top_bigrams": top_bigrams,
        "global_top_30": [{"word": w, "frequency": f} for w, f in global_freq.most_common(30)],
    }
