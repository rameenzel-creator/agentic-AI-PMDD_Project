"""
Agent 3: Semantic Field & Register Detector
Linguistic Approach: Semantic Field Theory (Lyons 1977), Register Analysis (Halliday 1978)
Adaptive: queries episodic memory to adjust semantic field clustering.
"""

from collections import defaultdict
from utils.llm_handler import call_llm
from utils.memory import get_past_lessons, save_decision, update_lesson

AGENT_ID = 3

SYSTEM_PROMPT = """You are an expert computational linguist specializing in Semantic Field Theory and Register Analysis.

Analyze the provided BATCH of text segments using:

1. SEMANTIC FIELD THEORY (Lyons 1977):
   Assign the DOMINANT semantic field from this list:
   CONFLICT, ECONOMY, TECHNOLOGY, EMOTION, POLITICS, NATURE, SOCIAL, EDUCATION, HEALTH, LAW, RELIGION, SCIENCE, CULTURE, FAMILY, IDENTITY

2. REGISTER ANALYSIS (Halliday 1978 — Tenor, Field, Mode):
   - register: "Formal" | "Semi-Formal" | "Informal" | "Technical" | "Colloquial"
   - tenor: "Expert-to-Expert" | "Expert-to-Layperson" | "Peer-to-Peer" | "Authority-to-Subordinate" | "Intimate"
   - mode: "Written-Planned" | "Written-Spontaneous" | "Speech-Like"

3. KEYWORD DRIFT:
   List 1-2 keywords that seem to be used in a context that might differ from their typical semantic field.
   For each: {{"word": "...", "expected_field": "...", "actual_field": "...", "drift_detected": true/false}}

4. REGISTER BORROWING:
   Is there evidence of formal vocabulary in informal context or vice versa?
   "register_borrowing": true/false, "borrowing_evidence": "brief description"

{memory_hint}

Return ONLY a valid JSON ARRAY, one object per segment, with EXACTLY these keys:
{{
  "segment_id": 123,
  "semantic_field": "POLITICS",
  "register": "Formal",
  "tenor": "Authority-to-Subordinate",
  "mode": "Written-Planned",
  "keyword_drift": [],
  "register_borrowing": false,
  "borrowing_evidence": "",
  "field_confidence": 0.9
}}"""


def run_agent3(segments: list[dict], keywords: list[str], run_id: str, batch_size: int = 10) -> dict:
    """
    Analyze semantic fields and register for corpus sections in batches.
    Returns: drift_map and per-section register summary.
    """
    drift_map = defaultdict(list)
    section_summaries = []
    sections_seen = {}

    working_segments = segments[:100]

    for i in range(0, len(working_segments), batch_size):
        batch = working_segments[i:i + batch_size]

        memory_hint = ""
        for kw in keywords:
            lessons = get_past_lessons(AGENT_ID, kw)
            if lessons:
                memory_hint += f"Historical: '{kw}' previously in '{lessons[0]['learned_field']}'.\n"

        prompt_system = SYSTEM_PROMPT.format(memory_hint=memory_hint if memory_hint else "No prior memory available.")
        
        segments_text = "\n\n".join([f"Segment ID: {s['id']}\nText: {s['text']}" for s in batch])
        user_prompt = f"Target keywords to track: {keywords}\n\nAnalyze these segments:\n{segments_text}"

        batch_results = call_llm(prompt_system, user_prompt, temperature=0.25, expect_json=True, retries=5)

        if not isinstance(batch_results, list):
            batch_results = []
            
        analysis_lookup = {item.get("segment_id"): item for item in batch_results if isinstance(item, dict)}

        for seg in batch:
            section = seg.get("section", 0)
            result = analysis_lookup.get(seg["id"])
            
            if not result:
                result = {
                    "semantic_field": "UNKNOWN", "register": "Unknown", "tenor": "Unknown", "mode": "Unknown",
                    "keyword_drift": [], "register_borrowing": False, "borrowing_evidence": "", "field_confidence": 0.0,
                }

            # Track section-level aggregates
            if section not in sections_seen:
                sections_seen[section] = {
                    "section": section, "label": seg.get("section_label", f"Section {section + 1}"),
                    "fields": [], "registers": [], "borrowing_events": [],
                }

            sections_seen[section]["fields"].append(result.get("semantic_field", "UNKNOWN"))
            sections_seen[section]["registers"].append(result.get("register", "Unknown"))
            if result.get("register_borrowing"):
                sections_seen[section]["borrowing_events"].append(result.get("borrowing_evidence", ""))

            # Update drift map robustly
            raw_kd = result.get("keyword_drift", [])
            if not isinstance(raw_kd, list):
                raw_kd = []
                
            for kd in raw_kd:
                word = ""
                expected = ""
                actual = ""
                drift = False
                
                if isinstance(kd, dict):
                    word = kd.get("word", "")
                    expected = kd.get("expected_field", "")
                    actual = kd.get("actual_field", "")
                    drift = bool(kd.get("drift_detected", False))
                elif isinstance(kd, str):
                    word = kd
                    
                if word:
                    drift_map[word].append({
                        "section": section, "expected_field": expected,
                        "actual_field": actual, "drift_detected": drift,
                    })
                    if drift:
                        update_lesson(AGENT_ID, word, result.get("register", ""), actual)

            save_decision(
                run_id=run_id, agent_id=AGENT_ID, segment_id=seg["id"],
                decision_type="semantic_register", decision_data=result,
                confidence=float(result.get("field_confidence", 1.0)),
            )

    # Summarize sections
    for sec_data in sections_seen.values():
        fields = sec_data["fields"]
        registers = sec_data["registers"]
        dominant_field = max(set(fields), key=fields.count) if fields else "UNKNOWN"
        dominant_register = max(set(registers), key=registers.count) if registers else "Unknown"
        section_summaries.append({
            "section": sec_data["section"], "label": sec_data["label"],
            "dominant_field": dominant_field, "dominant_register": dominant_register,
            "register_borrowing_count": len(sec_data["borrowing_events"]),
            "borrowing_samples": sec_data["borrowing_events"][:3],
        })

    keyword_drift_scores = {}
    for kw, events in drift_map.items():
        if events:
            drift_rate = sum(1 for e in events if e["drift_detected"]) / len(events)
            keyword_drift_scores[kw] = round(drift_rate * 100, 1)

    return {
        "section_summaries": section_summaries, "drift_map": dict(drift_map), "keyword_drift_scores": keyword_drift_scores,
    }
