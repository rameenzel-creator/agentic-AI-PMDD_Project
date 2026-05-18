"""
Agent 2: Pragmatic Analyzer
Linguistic Approach: Speech Act Theory (Austin/Searle), Gricean Maxims, Politeness Theory (Brown & Levinson)
Self-Correction: Chain of Verification (CoV) loop on every batch.
"""

from utils.llm_handler import call_llm
from utils.memory import get_past_lessons, save_decision, update_lesson

AGENT_ID = 2

SYSTEM_PROMPT = """You are an expert computational linguist specializing in Pragmatics.
Your task is to analyze a BATCH of text segments using the following EXACT theoretical frameworks:

1. SPEECH ACT THEORY (Searle 1969):
   Classify the dominant illocutionary act as ONE of:
   - Assertive: stating facts, describing, claiming
   - Directive: requesting, commanding, questioning
   - Commissive: promising, offering, committing
   - Expressive: thanking, apologizing, congratulating, lamenting
   - Declaration: declaring, pronouncing, appointing

2. GRICEAN MAXIMS (Grice 1975):
   List ALL maxim violations detected:
   - Quantity: too much / too little information
   - Quality: unverifiable or false claim
   - Relation: irrelevant content (flouting)
   - Manner: obscure, ambiguous, or unnecessarily long
   If none, return empty list.

3. IMPLICATURE TYPE:
   - "conventional": meaning encoded in the words themselves
   - "conversational": meaning inferred from context/maxim violation
   - "none": no significant implicature

4. POLITENESS SCORE (Brown & Levinson 1987):
   Score 1-5:
   1 = Highly face-threatening (aggressive, commanding)
   3 = Neutral
   5 = Highly polite, deferential

5. PRAGMATIC INTENT (your interpretation):
   One short phrase describing the speaker's underlying communicative goal.

Return ONLY a valid JSON ARRAY of objects, one for each segment.
Each object must have these EXACT keys:
{
  "segment_id": 123,
  "speech_act": "Assertive|Directive|Commissive|Expressive|Declaration",
  "maxim_violations": ["Quantity", "Manner"],
  "implicature_type": "conventional|conversational|none",
  "politeness_score": 3,
  "pragmatic_intent": "brief description",
  "confidence": 0.9
}"""

COV_PROMPT = """You previously classified a text segment. Now verify your analysis for logical consistency.
Check:
1. Does the speech act label match the verb semantics?
2. Are the maxim violations genuinely present or over-detected?
3. Is the politeness score consistent with the speech act and vocabulary?

If corrections are needed, return corrected JSON with an added "correction_reason" key.
If no corrections needed, return the original JSON with "correction_reason": "verified_no_change".

Original segment: {segment}
Original classification: {original}

Return ONLY valid JSON."""


def _analyze_batch(batch: list[dict], memory_context: str) -> list[dict]:
    """Run pragmatic analysis on a batch of segments."""
    segments_text = "\n\n".join([f"Segment ID: {s['id']}\nText: {s['text']}" for s in batch])
    
    user_prompt = f"""Memory context from previous analyses: {memory_context}

Analyze these segments:
{segments_text}

Apply all frameworks and return a JSON array."""

    result = call_llm(SYSTEM_PROMPT, user_prompt, temperature=0.2, expect_json=True, retries=5)
    
    if isinstance(result, dict) and "error" in result:
        return []
    if not isinstance(result, list):
        return []
    return result


def _chain_of_verification(segment: dict, original: dict) -> dict:
    """CoV: agent reflects on its own output and self-corrects if needed."""
    prompt = COV_PROMPT.format(segment=segment["text"], original=str(original))
    verified = call_llm(
        "You are a meticulous pragmatics peer-reviewer.",
        prompt,
        temperature=0.1,
        expect_json=True,
    )
    if "error" in verified:
        return original
    return verified


def run_agent2(segments: list[dict], run_id: str, batch_size: int = 10, progress_callback = None) -> list[dict]:
    """
    Main entry: analyze segments in batches, apply CoV on low-confidence items.
    Returns enriched segment list with pragmatic annotations.
    """
    results = []
    
    # Limit to first 100 segments to avoid API overload
    working_segments = segments[:100]

    for i in range(0, len(working_segments), batch_size):
        batch = working_segments[i:i + batch_size]
        
        if progress_callback:
            progress_callback(f"Agent 2: Processing batch {i//batch_size + 1} of {(len(working_segments)-1)//batch_size + 1} (segments {i} to {i+len(batch)-1})...")

        # Build combined memory context for the batch
        memory_ctx = ""
        for seg in batch:
            keywords = seg.get("content_words", [])[:2]
            for kw in keywords:
                lessons = get_past_lessons(AGENT_ID, kw)
                if lessons:
                    memory_ctx += f" '{kw}' previously seen as {lessons[0]['learned_field']}."

        # Primary analysis (Batch)
        batch_analyses = _analyze_batch(batch, memory_ctx)
        
        # Create a lookup by segment_id
        analysis_lookup = {item.get("segment_id"): item for item in batch_analyses if isinstance(item, dict)}

        for seg in batch:
            analysis = analysis_lookup.get(seg["id"])
            if not analysis:
                analysis = {
                    "speech_act": "Unknown",
                    "maxim_violations": [],
                    "implicature_type": "none",
                    "politeness_score": 3,
                    "pragmatic_intent": "batch_failed",
                    "confidence": 0.0,
                }
                
            corrected = False
            correction_reason = ""

            # CoV for low-confidence or directive/expressive (more ambiguous)
            confidence = float(analysis.get("confidence", 1.0))
            if confidence < 0.75 or analysis.get("speech_act") in ("Expressive", "Directive"):
                if progress_callback:
                    progress_callback(f"Agent 2: Ambiguity detected in Segment #{seg['id']} (Speech Act: '{analysis.get('speech_act')}', Conf: {confidence}). Triggering CoV review...")
                verified = _chain_of_verification(seg, analysis)
                reason = verified.get("correction_reason", "")
                if reason and reason != "verified_no_change":
                    corrected = True
                    correction_reason = reason
                    analysis = verified
                    if progress_callback:
                        progress_callback(f"  └─ [Self-Correction] Segment #{seg['id']} corrected: {reason}")

            # Save to episodic memory
            save_decision(
                run_id=run_id,
                agent_id=AGENT_ID,
                segment_id=seg["id"],
                decision_type="speech_act",
                decision_data=analysis,
                confidence=confidence,
                self_corrected=corrected,
                correction_reason=correction_reason,
            )

            # Update lessons learned
            keywords = seg.get("content_words", [])[:3]
            for kw in keywords:
                sa = analysis.get("speech_act", "Unknown")
                update_lesson(AGENT_ID, kw, sa, analysis.get("pragmatic_intent", ""))

            enriched = {**seg, **analysis, "self_corrected": corrected, "correction_reason": correction_reason}
            results.append(enriched)

    # Attach unprocessed segments (without analysis)
    for seg in segments[100:]:
        results.append({**seg, "speech_act": "Not Analyzed", "maxim_violations": [], "implicature_type": "none", "politeness_score": 3, "pragmatic_intent": "large_corpus_limit", "confidence": 0.0})

    return results
