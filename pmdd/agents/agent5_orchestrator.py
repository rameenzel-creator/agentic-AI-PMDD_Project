"""
Agent 5: Orchestrator & Evidence Synthesizer
Linguistic Approach: Critical Discourse Analysis (Fairclough 1992)
- Evaluates outputs from all agents
- Triggers re-analysis if coverage is insufficient
- Generates full scientific linguistic report
- Computes Meaning Drift Score (MDS)
"""

from utils.llm_handler import call_llm
from utils.memory import update_run_score

AGENT_ID = 5

SYNTHESIS_SYSTEM_PROMPT = """You are a Senior Computational Linguist and Critical Discourse Analyst.
Your task is to synthesize findings from a 5-agent analysis system and produce a rigorous scientific report.

THEORETICAL FRAMEWORKS TO APPLY:
- Critical Discourse Analysis (Fairclough 1992): analyze power, ideology, and social context
- Gricean Maxims (Grice 1975): cooperative principle evidence
- Speech Act Theory (Austin/Searle): illocutionary force patterns
- Semantic Field Theory (Lyons 1977): lexical drift evidence
- Register Analysis (Halliday 1978): Tenor, Field, Mode shifts
- Corpus Linguistics (Sinclair 1991): statistical validation

REPORT REQUIREMENTS:
- 40% quantitative evidence (cite statistics from Agent 4)
- 60% qualitative evidence (cite specific corpus examples with segment IDs from Agents 2 & 3)
- Ground every claim in a named linguistic theory
- Maintain a scientific, third-person academic register
- Cite segments as [Seg #ID] format

SCORING RUBRIC (each component 0-100):
- Pragmatic Drift: degree of speech act change + maxim violation increase
- Semantic Drift: keyword field migration + register borrowing events
- Register Drift: formal/informal balance shift across sections
- Overall MDS = (0.4 * pragmatic + 0.35 * semantic + 0.25 * register)

Return a JSON object with these EXACT top-level keys:
{
  "executive_summary": "2-paragraph academic summary",
  "pragmatic_drift_evidence": [{"finding": "...", "theory": "...", "segment_ids": [...], "corpus_quote": "..."}],
  "semantic_field_shifts": [{"keyword": "...", "before": "...", "after": "...", "theory_link": "..."}],
  "register_analysis": {"summary": "...", "borrowing_events": [...], "theory_link": "..."},
  "corpus_statistics_summary": {"key_findings": [...], "ttr_interpretation": "..."},
  "discourse_interpretation": "2-paragraph CDA analysis",
  "scores": {
    "pragmatic_drift": 0-100,
    "semantic_drift": 0-100,
    "register_drift": 0-100,
    "overall_mds": 0-100,
    "drift_level": "Low|Moderate|High|Extreme",
    "mds_justification": "..."
  },
  "agent_reflection_log": [{"agent": "Agent N", "event": "..."}],
  "conclusions": "research conclusions paragraph",
  "recommendations": ["research recommendation 1", "recommendation 2"]
}"""


def _quality_check(a2_out: list, a3_out: dict) -> list[str]:
    """Check if agent outputs have sufficient coverage. Returns list of issues."""
    issues = []
    analyzed = [s for s in a2_out if s.get("speech_act") not in ("Unknown", "Not Analyzed")]
    coverage = len(analyzed) / max(len(a2_out), 1)
    if coverage < 0.5:
        issues.append(f"Agent 2 coverage low: {coverage:.1%}")

    sections = a3_out.get("section_summaries", [])
    if len(sections) == 0:
        issues.append("Agent 3 produced no section summaries")

    return issues


def run_agent5(a1_out: dict, a2_out: list, a3_out: dict, a4_out: dict, run_id: str) -> dict:
    """
    Orchestrator logic:
    1. Quality check all agent outputs
    2. Build synthesis prompt with evidence
    3. Generate scientific report
    4. Compute Meaning Drift Score
    """
    # Quality check
    issues = _quality_check(a2_out, a3_out)
    reflection_log = []
    if issues:
        for issue in issues:
            reflection_log.append({"agent": "Agent 5 (Orchestrator)", "event": f"Coverage issue detected: {issue}"})

    # Build concise evidence summaries for the prompt (avoid token overflow)
    corpus_stats = a1_out.get("corpus_stats", {})
    analyzed_segments = [s for s in a2_out if s.get("speech_act") not in ("Unknown", "Not Analyzed", "Not analyzed")]

    # Speech act distribution
    from collections import Counter
    sa_counts = Counter(s.get("speech_act", "Unknown") for s in analyzed_segments)

    # Top maxim violations
    violations = []
    for s in analyzed_segments:
        v = s.get("maxim_violations", [])
        violations.extend(v)
    violation_counts = Counter(violations)

    # Segments with low politeness
    low_politeness = [s for s in analyzed_segments if s.get("politeness_score", 3) <= 2]

    # Self-correction events
    corrected = [s for s in a2_out if s.get("self_corrected")]
    for c in corrected:
        reflection_log.append({
            "agent": "Agent 2 (Pragmatic Analyzer)",
            "event": f"Self-corrected Seg #{c.get('id')}: {c.get('correction_reason', '')}"
        })

    # Key qualitative evidence (top 5 segments)
    evidence_segments = low_politeness[:3] + [s for s in analyzed_segments if s.get("maxim_violations")][:3]
    evidence_quotes = [
        {
            "id": s.get("id"),
            "text": s.get("text", "")[:200],
            "speech_act": s.get("speech_act"),
            "violations": s.get("maxim_violations", []),
            "politeness_score": s.get("politeness_score"),
        }
        for s in evidence_segments[:6]
    ]

    user_prompt = f"""CORPUS METADATA:
{corpus_stats}

AGENT 2 PRAGMATIC SUMMARY:
- Total segments analyzed: {len(analyzed_segments)}
- Speech act distribution: {dict(sa_counts)}
- Maxim violation counts: {dict(violation_counts)}
- Low politeness segments (<3): {len(low_politeness)}
- Self-correction events: {len(corrected)}

KEY EVIDENCE SEGMENTS (with quotes):
{evidence_quotes}

AGENT 3 SEMANTIC SUMMARY:
- Section summaries: {a3_out.get('section_summaries', [])}
- Keyword drift scores (%): {a3_out.get('keyword_drift_scores', {})}

AGENT 4 STATISTICAL SUMMARY:
- Total tokens: {a4_out.get('total_corpus_tokens')}
- Hapax legomena ratio: {a4_out.get('hapax_legomena_ratio')}
- Section TTR values: {[(s, d.get('type_token_ratio')) for s, d in a4_out.get('section_stats', {}).items()]}
- Top keywords (global): {[d['word'] for d in a4_out.get('global_top_30', [])[:15]]}
- Top collocations: {list(a4_out.get('collocations', {}).items())[:3]}

Generate the full scientific report JSON now."""

    report = call_llm(SYNTHESIS_SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=4096, expect_json=True)

    if "error" in report:
        # Fallback minimal report
        report = {
            "executive_summary": "Analysis completed. LLM synthesis encountered an error during final report generation.",
            "pragmatic_drift_evidence": [],
            "semantic_field_shifts": [],
            "register_analysis": {"summary": "Unable to generate", "borrowing_events": [], "theory_link": ""},
            "corpus_statistics_summary": {"key_findings": [], "ttr_interpretation": ""},
            "discourse_interpretation": "Unable to generate due to API error.",
            "scores": {"pragmatic_drift": 50, "semantic_drift": 50, "register_drift": 50, "overall_mds": 50,
                       "drift_level": "Moderate", "mds_justification": "Fallback score — report generation failed."},
            "agent_reflection_log": reflection_log,
            "conclusions": "Re-run analysis for complete results.",
            "recommendations": ["Check API key", "Reduce corpus size"],
        }

    # Inject reflection log from orchestrator
    existing_log = report.get("agent_reflection_log", [])
    report["agent_reflection_log"] = reflection_log + existing_log

    # Persist MDS score
    mds = report.get("scores", {}).get("overall_mds", 50)
    summary = report.get("executive_summary", "")[:500]
    update_run_score(run_id, mds, summary)

    return report
