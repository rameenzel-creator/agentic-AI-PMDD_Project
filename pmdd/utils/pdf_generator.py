"""
PDF Report Generator — Research-grade output
40% Quantitative, 60% Qualitative Evidence Ratio
"""

from fpdf import FPDF
import datetime
import os


COLORS = {
    "primary":   (15, 23, 42),     # Deep midnight
    "accent":    (59, 130, 246),   # Electric blue
    "success":   (16, 185, 129),   # Emerald
    "danger":    (239, 68, 68),    # Red
    "warning":   (245, 158, 11),   # Amber
    "light_bg":  (248, 250, 252),  # Near-white
    "text":      (30, 41, 59),     # Dark slate
    "muted":     (100, 116, 139),  # Slate 500
    "table_hdr": (30, 58, 138),    # Dark blue
    "white":     (255, 255, 255),
}


class PMDDReport(FPDF):
    def __init__(self, corpus_name: str, run_date: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.corpus_name = corpus_name
        self.run_date = run_date
        self.set_auto_page_break(auto=True, margin=20)
        self.set_left_margin(20)
        self.set_right_margin(20)

    def header(self):
        if self.page_no() == 1:
            return
        r, g, b = COLORS["primary"]
        self.set_fill_color(r, g, b)
        self.rect(0, 0, 210, 14, "F")
        self.set_text_color(*COLORS["white"])
        self.set_font("Helvetica", "B", 8)
        self.set_xy(10, 4)
        self.cell(0, 6, _sanitize_for_pdf(f"PMDD Scientific Analysis Report  |  {self.corpus_name}  |  {self.run_date}"), 0, 0, "L")
        self.set_xy(0, 4)
        self.cell(200, 6, f"Page {self.page_no()}", 0, 0, "R")
        self.ln(12)
        self.set_text_color(*COLORS["text"])

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        r, g, b = COLORS["primary"]
        self.set_fill_color(r, g, b)
        self.rect(0, 283, 210, 14, "F")
        self.set_text_color(*COLORS["white"])
        self.set_font("Helvetica", "I", 7)
        self.set_x(10)
        self.cell(0, 8, "Pragmatic Meaning Drift Detector (PMDD) | Agentic AI Linguistic Analysis System", 0, 0, "L")
        self.set_text_color(*COLORS["text"])

    def section_title(self, num: str, title: str, color=None):
        self.ln(6)
        r, g, b = color or COLORS["accent"]
        self.set_fill_color(r, g, b)
        self.rect(self.get_x(), self.get_y(), 170, 8, "F")
        self.set_text_color(*COLORS["white"])
        self.set_font("Helvetica", "B", 11)
        self.set_x(20)
        self.cell(0, 8, _sanitize_for_pdf(f"  {num}  {title.upper()}"), 0, 1, "L")
        self.set_text_color(*COLORS["text"])
        self.ln(3)

    def subsection(self, title: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*COLORS["table_hdr"])
        self.cell(0, 6, _sanitize_for_pdf(title), 0, 1, "L")
        self.set_text_color(*COLORS["text"])
        self.set_draw_color(*COLORS["accent"])
        self.set_line_width(0.5)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(2)

    def body_text(self, text: str, indent: int = 0):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*COLORS["text"])
        self.set_x(20 + indent)
        self.multi_cell(170 - indent, 5, _sanitize_for_pdf(text))
        self.ln(1)

    def italic_text(self, text: str):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(*COLORS["muted"])
        self.multi_cell(170, 5, _sanitize_for_pdf(text))
        self.ln(1)
        self.set_text_color(*COLORS["text"])

    def quote_box(self, quote: str, label: str):
        """Styled corpus evidence quote box."""
        r, g, b = COLORS["light_bg"]
        self.set_fill_color(r, g, b)
        self.set_draw_color(*COLORS["accent"])
        self.set_line_width(0.8)
        x, y = self.get_x(), self.get_y()
        self.rect(x, y, 170, max(16, len(quote) // 3 + 14), "DF")
        self.set_xy(x + 3, y + 2)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*COLORS["accent"])
        self.cell(0, 4, _sanitize_for_pdf(label), 0, 1, "L")
        self.set_x(x + 3)
        self.set_font("Helvetica", "I", 8.5)
        self.set_text_color(*COLORS["text"])
        self.multi_cell(164, 4.5, _sanitize_for_pdf(f'"{quote}"'))
        self.ln(2)
        self.set_text_color(*COLORS["text"])

    def table_header(self, cols: list[tuple[str, int]]):
        self.set_fill_color(*COLORS["table_hdr"])
        self.set_text_color(*COLORS["white"])
        self.set_font("Helvetica", "B", 8)
        for label, w in cols:
            self.cell(w, 7, _sanitize_for_pdf(label), 1, 0, "C", fill=True)
        self.ln()
        self.set_text_color(*COLORS["text"])

    def table_row(self, values: list, widths: list[int], fill: bool = False):
        r, g, b = COLORS["light_bg"] if fill else COLORS["white"]
        self.set_fill_color(r, g, b)
        self.set_font("Helvetica", "", 8)
        for val, w in zip(values, widths):
            self.cell(w, 6, _sanitize_for_pdf(str(val)[:40]), 1, 0, "L", fill=fill)
        self.ln()

    def score_badge(self, label: str, score: float, x_offset: float = 0):
        """Draw a colored score badge."""
        score = float(score)
        if score >= 75:
            r, g, b = COLORS["danger"]
        elif score >= 50:
            r, g, b = COLORS["warning"]
        else:
            r, g, b = COLORS["success"]

        self.set_fill_color(r, g, b)
        self.set_text_color(*COLORS["white"])
        self.set_font("Helvetica", "B", 9)
        self.cell(55, 12, _sanitize_for_pdf(f"{label}: {score:.0f}/100"), 0, 0, "C", fill=True)
        self.set_text_color(*COLORS["text"])


def _sanitize_for_pdf(text: str) -> str:
    """Replace non-Latin-1 characters that FPDF's standard fonts can't handle."""
    if not text:
        return ""
    # Map common problematic unicode characters to ASCII/Latin-1 equivalents
    replacements = {
        "\u2014": "-",   # em dash
        "\u2013": "-",   # en dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # non-breaking space
        "\u2022": "*",   # bullet point
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Finally, encode and decode to Latin-1, ignoring anything that still doesn't fit
    return text.encode("latin-1", "ignore").decode("latin-1")


def _safe_str(val, max_len=200) -> str:
    if val is None:
        return ""
    s = _sanitize_for_pdf(str(val))
    return s[:max_len] + ("..." if len(s) > max_len else "")


def generate_pdf(
    report: dict,
    a1_out: dict,
    a4_out: dict,
    output_path: str,
    corpus_name: str = "Corpus",
    run_id: str = "",
) -> str:
    run_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    pdf = PMDDReport(corpus_name=corpus_name, run_date=run_date)

    # ─────────────────────────────────────────
    # PAGE 1: TITLE PAGE
    # ─────────────────────────────────────────
    pdf.add_page()
    r, g, b = COLORS["primary"]
    pdf.set_fill_color(r, g, b)
    pdf.rect(0, 0, 210, 297, "F")

    pdf.set_y(50)
    pdf.set_text_color(*COLORS["accent"])
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "AGENTIC AI LINGUISTIC ANALYSIS", 0, 1, "C")
    pdf.ln(4)

    pdf.set_text_color(*COLORS["white"])
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(0, 14, "Pragmatic Meaning", 0, 1, "C")
    pdf.cell(0, 14, "Drift Detector", 0, 1, "C")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*COLORS["accent"])
    pdf.cell(0, 10, "(PMDD)", 0, 1, "C")
    pdf.ln(10)

    pdf.set_text_color(200, 210, 230)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, "Scientific Analysis Report", 0, 1, "C")
    pdf.cell(0, 8, f"Corpus: {corpus_name}", 0, 1, "C")
    pdf.cell(0, 8, f"Generated: {run_date}", 0, 1, "C")
    pdf.cell(0, 8, f"Run ID: {run_id}", 0, 1, "C")

    pdf.ln(20)
    scores = report.get("scores", {})
    mds = float(scores.get("overall_mds", 50))
    drift_level = scores.get("drift_level", "Moderate")

    if mds >= 75:
        badge_color = COLORS["danger"]
    elif mds >= 50:
        badge_color = COLORS["warning"]
    else:
        badge_color = COLORS["success"]

    r2, g2, b2 = badge_color
    pdf.set_fill_color(r2, g2, b2)
    pdf.set_text_color(*COLORS["white"])
    pdf.set_font("Helvetica", "B", 36)
    pdf.cell(0, 24, _sanitize_for_pdf(f"{mds:.0f} / 100"), 0, 1, "C", fill=False)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, _sanitize_for_pdf(f"Overall Meaning Drift Score - {drift_level.upper()} DRIFT DETECTED"), 0, 1, "C")

    pdf.ln(20)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(150, 170, 200)
    pdf.cell(0, 6, _sanitize_for_pdf("5-Agent Agentic AI System | Evidence-Based Linguistic Research"), 0, 1, "C")

    # ─────────────────────────────────────────
    # PAGE 2: EXECUTIVE SUMMARY & CORPUS STATS
    # ─────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("1.", "Executive Summary", COLORS["table_hdr"])
    summary = report.get("executive_summary", "No summary generated.")
    pdf.body_text(summary)

    pdf.section_title("2.", "Meaning Drift Score (MDS) Breakdown", COLORS["accent"])
    pdf.subsection("Score Components")
    pdf.ln(2)
    # Score badges
    badges = [
        ("Pragmatic Drift", scores.get("pragmatic_drift", 50)),
        ("Semantic Drift",  scores.get("semantic_drift", 50)),
        ("Register Drift",  scores.get("register_drift", 50)),
    ]
    pdf.set_x(20)
    for label, val in badges:
        pdf.score_badge(label, val)
        pdf.set_x(pdf.get_x() + 5)
    pdf.ln(16)

    justification = scores.get("mds_justification", "")
    if justification:
        pdf.italic_text(f"Justification: {justification}")

    # Corpus metadata table
    pdf.section_title("3.", "Corpus Metadata (Agent 1)", COLORS["success"])
    cs = a1_out.get("corpus_stats", {})
    cols = [("Metric", 80), ("Value", 90)]
    pdf.table_header(cols)
    rows = [
        ("Total Segments", cs.get("total_segments", "—")),
        ("Total Words", cs.get("total_words", "—")),
        ("Unique Words", cs.get("unique_words", "—")),
        ("Type-Token Ratio (TTR)", cs.get("type_token_ratio", "—")),
        ("Avg. Segment Length", cs.get("avg_segment_length", "—")),
        ("Total Corpus Sections", cs.get("total_sections", "—")),
    ]
    for i, (m, v) in enumerate(rows):
        pdf.table_row([m, v], [80, 90], fill=(i % 2 == 0))

    # ─────────────────────────────────────────
    # PAGE 3: QUANTITATIVE ANALYSIS (40%)
    # ─────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("4.", "Quantitative Corpus Analysis — 40% of Evidence (Agent 4)", COLORS["table_hdr"])
    pdf.italic_text(
        "Grounded in Corpus Linguistics (Sinclair 1991): Frequency, Collocation, Keyness, "
        "and Type-Token Ratio provide the statistical substrate for identifying significant lexical patterns."
    )

    # Per-section stats
    pdf.subsection("4.1 — Section-Level Frequency Statistics")
    sec_stats = a4_out.get("section_stats", {})
    cols = [("Section", 35), ("Total Words", 35), ("Unique Words", 35), ("TTR", 30), ("Top Keywords", 35)]
    pdf.table_header(cols)
    for i, (sec, data) in enumerate(sec_stats.items()):
        top = ", ".join([d["word"] for d in data.get("top_20_words", [])[:4]])
        pdf.table_row(
            [f"Section {int(sec)+1}", data.get("total_words"), data.get("unique_words"), data.get("type_token_ratio"), top],
            [35, 35, 35, 30, 35], fill=(i % 2 == 0),
        )

    # Hapax Legomena
    pdf.ln(4)
    pdf.subsection("4.2 — Hapax Legomena & Lexical Richness")
    hapax_ratio = a4_out.get("hapax_legomena_ratio", 0)
    hapax_count = a4_out.get("hapax_legomena_count", 0)
    pdf.body_text(
        f"Hapax Legomena: {hapax_count} words (ratio: {hapax_ratio:.4f}). A high hapax ratio (>0.40) "
        "indicates a corpus with rich, non-repetitive vocabulary, which may signal domain-specific register shifts."
    )

    # Collocation evidence
    pdf.subsection("4.3 — Collocation Analysis (MI Scores)")
    pdf.body_text(
        "Mutual Information (MI) scores quantify the strength of word associations. High MI scores (>3.0) "
        "indicate significant, non-random collocations — the building blocks of semantic field identification."
    )
    collocations = a4_out.get("collocations", {})
    cols = [("Target Word", 40), ("Collocate", 40), ("Co-occurrence Freq.", 40), ("MI Score", 40)]
    pdf.table_header(cols)
    i = 0
    for target, colls in list(collocations.items())[:3]:
        for c in colls[:3]:
            pdf.table_row([target, c["collocate"], c["frequency"], c["mi_score"]], [40, 40, 40, 40], fill=(i % 2 == 0))
            i += 1

    # ─────────────────────────────────────────
    # PAGE 4: PRAGMATIC EVIDENCE (60%)
    # ─────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("5.", "Qualitative Linguistic Evidence — 60% of Evidence (Agents 2 & 3)", COLORS["danger"])
    pdf.italic_text(
        "Grounded in Pragmatics (Grice 1975; Austin 1962; Searle 1969) and Semantic Field Theory (Lyons 1977). "
        "Each finding is supported by direct corpus citations and theoretical interpretation."
    )

    pdf.subsection("5.1 — Pragmatic Drift Evidence (Agent 2)")
    pragmatic_evidence = report.get("pragmatic_drift_evidence", [])
    if pragmatic_evidence:
        for ev in pragmatic_evidence[:5]:
            finding = _safe_str(ev.get("finding", ""))
            theory = _safe_str(ev.get("theory", ""))
            quote = _safe_str(ev.get("corpus_quote", ""), 180)
            segs = ev.get("segment_ids", [])
            if finding:
                pdf.body_text(f"● {finding}", indent=2)
                pdf.italic_text(f"   Theory: {theory}")
                if segs:
                    pdf.italic_text(f"   Referenced Segments: {', '.join([f'[Seg #{s}]' for s in segs[:4]])}")
                if quote:
                    pdf.quote_box(quote, f"Corpus Evidence" + (f" [Seg #{segs[0]}]" if segs else ""))
    else:
        pdf.body_text("No pragmatic drift evidence was generated in this analysis run.")

    # ─────────────────────────────────────────
    # PAGE 5: SEMANTIC & REGISTER EVIDENCE
    # ─────────────────────────────────────────
    pdf.add_page()
    pdf.subsection("5.2 — Semantic Field Shifts (Agent 3)")
    pdf.italic_text(
        "Following Lyons (1977), words are organized into semantic fields. Drift occurs when a lexical item "
        "migrates between fields or acquires new field membership across corpus sections."
    )
    semantic_shifts = report.get("semantic_field_shifts", [])
    if semantic_shifts:
        cols = [("Keyword", 40), ("Period A Field", 45), ("Period B Field", 45), ("Theory Link", 40)]
        pdf.table_header(cols)
        for i, sh in enumerate(semantic_shifts[:8]):
            pdf.table_row(
                [sh.get("keyword", ""), sh.get("before", ""), sh.get("after", ""), sh.get("theory_link", "")],
                [40, 45, 45, 40], fill=(i % 2 == 0)
            )
    else:
        pdf.body_text("No semantic field shifts were detected.")

    pdf.ln(4)
    pdf.subsection("5.3 — Register Analysis (Agent 3, Halliday 1978)")
    reg_analysis = report.get("register_analysis", {})
    pdf.body_text(_safe_str(reg_analysis.get("summary", "No register analysis available.")))
    borrowings = reg_analysis.get("borrowing_events", [])
    if borrowings:
        pdf.body_text(f"Register Borrowing Events Detected: {len(borrowings)}")
        for b in borrowings[:3]:
            pdf.body_text(f"   → {_safe_str(b)}", indent=4)

    pdf.ln(4)
    pdf.subsection("5.4 — Critical Discourse Analysis Interpretation (Agent 5)")
    pdf.italic_text("Grounded in Fairclough (1992): analyzing power, ideology, and social context in text.")
    cda = report.get("discourse_interpretation", "No CDA interpretation available.")
    pdf.body_text(cda)

    # ─────────────────────────────────────────
    # PAGE 6: AGENTIC REFLECTION & CONCLUSIONS
    # ─────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("6.", "Agentic Reflection & Self-Correction Log", COLORS["warning"])
    pdf.body_text(
        "This section provides scientific transparency. All self-correction events are logged "
        "to allow peer review of the agentic reasoning process."
    )
    reflection_log = report.get("agent_reflection_log", [])
    if reflection_log:
        for entry in reflection_log[:10]:
            agent = entry.get("agent", "Agent ?")
            event = _safe_str(entry.get("event", ""), 250)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COLORS["table_hdr"])
            pdf.cell(50, 5, f"[{agent}]", 0, 0)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*COLORS["text"])
            pdf.multi_cell(120, 5, event)
            pdf.ln(1)
    else:
        pdf.body_text("No self-correction events were recorded in this analysis run.")

    pdf.section_title("7.", "Conclusions & Research Recommendations", COLORS["table_hdr"])
    pdf.body_text(_safe_str(report.get("conclusions", "No conclusions generated."), 800))
    pdf.ln(4)
    pdf.subsection("Research Recommendations")
    recommendations = report.get("recommendations", [])
    for rec in recommendations[:5]:
        pdf.body_text(f"→ {_safe_str(rec)}", indent=4)

    # ─────────────────────────────────────────
    # PAGE 7: STATISTICAL APPENDIX
    # ─────────────────────────────────────────
    pdf.add_page()
    pdf.section_title("8.", "Statistical Appendix — Corpus Statistics Summary", COLORS["muted"])

    stats_summary = report.get("corpus_statistics_summary", {})
    key_findings = stats_summary.get("key_findings", [])
    if key_findings:
        pdf.subsection("Key Statistical Findings")
        for kf in key_findings[:6]:
            pdf.body_text(f"• {_safe_str(kf)}", indent=2)

    ttr_interp = stats_summary.get("ttr_interpretation", "")
    if ttr_interp:
        pdf.body_text(f"\nTTR Interpretation: {ttr_interp}")

    # Top 30 frequency table
    pdf.subsection("Global Top-30 Content Words")
    global_top = a4_out.get("global_top_30", [])
    if global_top:
        cols = [("Word", 45), ("Frequency", 45), ("Word", 45), ("Frequency", 35)]
        pdf.table_header(cols)
        pairs = [(global_top[i], global_top[i + 1] if i + 1 < len(global_top) else {}) for i in range(0, min(30, len(global_top)), 2)]
        for i, (w1, w2) in enumerate(pairs):
            pdf.table_row(
                [w1.get("word", ""), w1.get("frequency", ""), w2.get("word", ""), w2.get("frequency", "")],
                [45, 45, 45, 35], fill=(i % 2 == 0)
            )

    # Reference section
    pdf.ln(8)
    pdf.section_title("9.", "Theoretical References", COLORS["primary"])
    refs = [
        "Austin, J.L. (1962). How to Do Things with Words. Oxford University Press.",
        "Brown, P. & Levinson, S.C. (1987). Politeness: Some Universals in Language Usage. Cambridge University Press.",
        "Fairclough, N. (1992). Discourse and Social Change. Polity Press.",
        "Grice, H.P. (1975). Logic and Conversation. In P. Cole & J. Morgan (Eds.), Syntax and Semantics, Vol. 3.",
        "Halliday, M.A.K. (1978). Language as Social Semiotic. Edward Arnold.",
        "Lyons, J. (1977). Semantics, Vols. 1 & 2. Cambridge University Press.",
        "Scott, M. (1997). PC Analysis of Key Words and Key Texts. System, 25(2), 233-245.",
        "Searle, J.R. (1969). Speech Acts: An Essay in the Philosophy of Language. Cambridge University Press.",
        "Sinclair, J. (1991). Corpus, Concordance, Collocation. Oxford University Press.",
    ]
    for ref in refs:
        pdf.body_text(ref, indent=4)

    pdf.output(output_path)
    return output_path
