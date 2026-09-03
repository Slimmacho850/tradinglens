"""
Script to generate a comprehensive, beautifully styled PDF Field Manual for DR Lens & DR Drive.
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).resolve().parents[1]
PDF_OUTPUT_PATH = ROOT_DIR / "DR_Lens_Comprehensive_Trading_Guide.pdf"


class NumberedCanvas(canvas.Canvas):
    """Adds 'Page X of Y' and running header/footer to all pages."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "DR LENS & DR DRIVE | QUANTITATIVE EXECUTION FIELD MANUAL")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
            
        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 36, footer_text)
        self.drawString(54, 36, "CONFIDENTIAL — STRICTLY FOR SYSTEMATIC & QUANTITATIVE RESEARCH")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * inch - 54, 46)
        
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_OUTPUT_PATH),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Color Tokens
    TEAL = colors.HexColor("#009E73")
    DARK_BLUE = colors.HexColor("#1A202C")
    LIGHT_BG = colors.HexColor("#F7FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")
    ALERT_BG = colors.HexColor("#EDF2F7")
    TEXT_MUTED = colors.HexColor("#4A5568")
    TEXT_MAIN = colors.HexColor("#2D3748")

    # Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=DARK_BLUE,
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=TEAL,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=DARK_BLUE,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=TEAL,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=TEXT_MAIN,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=TEXT_MAIN,
        leftIndent=12,
        spaceAfter=3,
    )

    callout_style = ParagraphStyle(
        "Callout_Text",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=DARK_BLUE,
    )

    story = []

    # ============================================================
    # TITLE & HEADER SECTION
    # ============================================================
    story.append(Paragraph("DR LENS & DR DRIVE TRADING MANUAL", title_style))
    story.append(Paragraph("A Step-by-Step Practical Field Guide for Every Market Scenario", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=TEAL, spaceBefore=0, spaceAfter=12))

    intro_text = (
        "This guide translates 20 years of statistical Defining Range (DR) research into simple, actionable "
        "rules you can apply in the market every single day. Master and Mage designed DR Lens not as a lagging "
        "indicator, but as a real-time navigation system that defines exact price targets, entry zones, and "
        "expiration windows before the trade unfolds."
    )
    story.append(Paragraph(intro_text, body_style))
    story.append(Spacer(1, 8))

    # ============================================================
    # SECTION 1: CORE DEFINITIONS & THE 3 SESSIONS
    # ============================================================
    story.append(Paragraph("1. Core Concepts & Session Windows", h1_style))
    
    concept_p = (
        "Every 24-hour trading day is divided into three independent trading sessions. "
        "During the first hour of each session, the market establishes the <b>Defining Range (DR)</b> "
        "and <b>Implied Defining Range (IDR)</b>:"
    )
    story.append(Paragraph(concept_p, body_style))

    # Sessions Table
    session_data = [
        [Paragraph("<b>Session</b>", body_style), Paragraph("<b>DR Formation (NY Time)</b>", body_style), Paragraph("<b>Trading Window</b>", body_style), Paragraph("<b>Primary Instruments</b>", body_style)],
        [Paragraph("<b>ADR (Asian)</b>", body_style), Paragraph("19:30 – 20:30 ET", body_style), Paragraph("20:30 – 02:00 ET", body_style), Paragraph("Gold (GC), Nikkei, AUD/JPY", body_style)],
        [Paragraph("<b>ODR (London)</b>", body_style), Paragraph("03:00 – 04:00 ET", body_style), Paragraph("04:00 – 08:30 ET", body_style), Paragraph("DAX, FTSE, Euro (6E), Gold", body_style)],
        [Paragraph("<b>RDR (New York)</b>", body_style), Paragraph("09:30 – 10:30 ET", body_style), Paragraph("10:30 – 16:00 ET", body_style), Paragraph("S&P 500 (ES), Nasdaq (NQ), Dow (YM)", body_style)],
    ]
    t_session = Table(session_data, colWidths=[1.1 * inch, 1.6 * inch, 1.4 * inch, 2.7 * inch])
    t_session.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ALERT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_session)
    story.append(Spacer(1, 10))

    # Range Definitions Callout
    def_box = [
        [Paragraph(
            "<b>Key Level Rules:</b><br/>"
            "• <b>DR (Defining Range):</b> The highest body close and lowest body open of the 5-minute candles during the first hour.<br/>"
            "• <b>IDR (Implied DR):</b> The absolute highest wick and lowest wick during the first hour.<br/>"
            "• <b>Confirmation:</b> A full 5-minute candle closes completely outside the IDR (above IDR High = Long, below IDR Low = Short).<br/>"
            "• <b>DR Rule True (81.4% Edge):</b> Once confirmed, price will NOT close a 5-minute candle beyond the opposite DR boundary for the rest of the session.",
            callout_style
        )]
    ]
    t_def = Table(def_box, colWidths=[6.8 * inch])
    t_def.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, TEAL),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_def)
    story.append(Spacer(1, 12))

    # ============================================================
    # SECTION 2: THE 5 TRADING SCENARIOS
    # ============================================================
    story.append(Paragraph("2. Playbooks for Every Market Scenario", h1_style))

    # --- Scenario 1 ---
    story.append(Paragraph("Scenario 1: Standard DR Drive Trend Continuation (The 80% Retracement Setup)", h2_style))
    story.append(Paragraph(
        "<b>When to Use:</b> You observe an early confirmation candle (e.g. 10:30–11:00 RDR or 04:00–04:30 ODR). "
        "Do NOT chase the breakout candle! Wait for the systematic mathematical pullback.",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Execution:</b>", body_style))
    story.append(Paragraph("1. <b>Mark Entry Zone:</b> Place a limit order at <b>0.60x to 0.80x IDR Retracement</b> (or Mid-DR / 0.50x).", bullet_style))
    story.append(Paragraph("2. <b>Set Invalidation Stop:</b> Place stop loss exactly at the <b>Opposite DR level (1.00x SD)</b>. Since the DR Rule holds ~81.4% of the time, this level is protected.", bullet_style))
    story.append(Paragraph("3. <b>Check Retracement Time:</b> Expect your limit order to fill around the <b>First Retracement Median Time</b> (approx. 20–25 mins post-confirmation).", bullet_style))
    story.append(Paragraph("4. <b>Target Levels:</b> Take 50% profit at <b>0.50x SD (Low-Hanging Fruit)</b> and runner at <b>Median SD Extension (1.2x – 1.4x SD)</b>.", bullet_style))
    story.append(Paragraph("5. <b>Risk:Reward:</b> Yields an asymmetric <b>1 : 3.5 to 1 : 5.0 R:R</b>.", bullet_style))
    story.append(Spacer(1, 8))

    # --- Scenario 2 ---
    story.append(Paragraph("Scenario 2: The 'Outside DR' Session-End Setup (Retirement Setup)", h2_style))
    story.append(Paragraph(
        "<b>When to Use:</b> Price has confirmed and retraced deeply into IDR during the mid-session lull. "
        "Historical data shows an overwhelming <b>63.2% probability</b> (up to 65.5% on Mondays) that the session will close outside the DR during the final 15 minutes (3:45–4:00 PM ET).",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Execution:</b>", body_style))
    story.append(Paragraph("1. If price is hovering near IDR Mid between 1:30 PM and 2:30 PM NY time with no opposite DR violation, enter in the confirmed direction.", bullet_style))
    story.append(Paragraph("2. Stop Loss: Opposite DR level.", bullet_style))
    story.append(Paragraph("3. Exit Rule: Hold into the final 15 minutes (3:45–4:00 PM). Close position at market on the highest close (for Long) or lowest close (for Short).", bullet_style))
    story.append(Spacer(1, 8))

    # --- Scenario 3 ---
    story.append(Paragraph("Scenario 3: The False Day Playbook (Opposite Breakout Scenario)", h2_style))
    story.append(Paragraph(
        "<b>When to Use:</b> In ~18.6% of sessions, price confirms one direction, but market structure fails and price closes a 5-minute candle beyond the <b>opposite DR boundary</b>. "
        "This triggers a 'False Day'.",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Execution:</b>", body_style))
    story.append(Paragraph("1. <b>Immediately Cancel Initial Bias:</b> Close any remaining original positions. Invalidation has triggered.", bullet_style))
    story.append(Paragraph("2. <b>Flip to Opposite Breakout:</b> When a full candle closes beyond the opposite DR, historical false days exhibit rapid expansion of <b>2.0x to 2.5x SD</b> in the reverse direction.", bullet_style))
    story.append(Paragraph("3. <b>Target Tiers:</b> Target 1.5x SD, 2.0x SD, and 2.5x SD on the opposite side. False days are often the highest-volatility trending sessions.", bullet_style))
    story.append(Spacer(1, 8))

    # --- Scenario 4 ---
    story.append(Paragraph("Scenario 4: Time Expiration Decay (Managing Stagnant Trades)", h2_style))
    story.append(Paragraph(
        "<b>When to Use:</b> Price is moving slowly and has not reached your target as the clock approaches the <b>Max Extension Median Time</b> (e.g. 05:35 ET for London or 14:15 ET for New York).",
        body_style
    ))
    story.append(Paragraph("<b>Step-by-Step Execution:</b>", body_style))
    story.append(Paragraph("1. <b>The Time Expiration Rule:</b> Once the session clock passes the Max Extension Median Time, the probability of reaching 1.2x or 1.5x SD drops drastically.", bullet_style))
    story.append(Paragraph("2. <b>Scale Back Targets:</b> Immediately move Take-Profit to the <b>0.50x SD (Low-Hanging Fruit)</b> or IDR boundary.", bullet_style))
    story.append(Paragraph("3. <b>Protect Capital:</b> Move your Stop Loss to Breakeven / Entry to eliminate downside risk.", bullet_style))
    story.append(Spacer(1, 8))

    # --- Scenario 5 ---
    story.append(Paragraph("Scenario 5: Multi-Session Momentum Confluence (ADR → ODR → RDR)", h2_style))
    story.append(Paragraph(
        "<b>When to Use:</b> Analyzing the daily sequence of sessions to determine whether momentum is compounding or due for mean reversion.",
        body_style
    ))
    story.append(Paragraph("• <b>Triple Trend Confluence (ADR Long → ODR Long → RDR Long):</b> Occurs in ~28% of trading weeks. When both Asian and London confirm the same direction, New York has an <b>86%+ confirmation rate</b> in that same direction. Take aggressive trend entries.", bullet_style))
    story.append(Paragraph("• <b>London Reversal (ADR Long → ODR Short):</b> Often represents Asian liquidity sweeps. New York typically establishes the true daily expansion.", bullet_style))
    story.append(Spacer(1, 12))

    # ============================================================
    # SECTION 3: RETRACEMENT DEPTH VS TIME MATRIX
    # ============================================================
    story.append(Paragraph("3. Retracement Depth vs. Clock Time Matrix", h1_style))
    story.append(Paragraph(
        "A critical breakthrough of the 20-year DR dataset is that specific retracement depths happen at "
        "statistically distinct clock windows throughout the session:",
        body_style
    ))

    ret_time_data = [
        [Paragraph("<b>Retracement Tier</b>", body_style), Paragraph("<b>RDR (New York) Window</b>", body_style), Paragraph("<b>ODR (London) Window</b>", body_style), Paragraph("<b>Statistical Behavior & Playbook</b>", body_style)],
        [Paragraph("<b>Shallow (0.0x – 0.2x SD)</b>", body_style), Paragraph("10:30 – 11:30 ET", body_style), Paragraph("04:00 – 05:00 ET", body_style), Paragraph("Fast runner sessions. Occurs right after confirmation.", body_style)],
        [Paragraph("<b>Standard (0.4x – 0.6x SD)</b>", body_style), Paragraph("11:00 – 12:30 ET", body_style), Paragraph("04:30 – 05:30 ET", body_style), Paragraph("Mid-session pullback. Ideal 50% limit order entry.", body_style)],
        [Paragraph("<b>Deep (0.6x – 0.8x SD)</b>", body_style), Paragraph("11:30 – 13:30 ET", body_style), Paragraph("05:00 – 06:30 ET", body_style), Paragraph("<b>Golden Entry Zone:</b> Highest R:R limit order fill.", body_style)],
        [Paragraph("<b>Max Retest (0.8x – 1.0x SD)</b>", body_style), Paragraph("12:00 – 14:00 ET", body_style), Paragraph("05:30 – 07:00 ET", body_style), Paragraph("Final test of opposite IDR boundary before extension.", body_style)],
        [Paragraph("<b>Breach (>1.00x SD)</b>", body_style), Paragraph("After 13:30 ET", body_style), Paragraph("After 06:30 ET", body_style), Paragraph("False Day trigger. Close position and flip direction.", body_style)],
    ]
    t_ret_time = Table(ret_time_data, colWidths=[1.6 * inch, 1.4 * inch, 1.4 * inch, 2.4 * inch])
    t_ret_time.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ALERT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_ret_time)
    story.append(Spacer(1, 12))

    # ============================================================
    # SECTION 4: QUICK CHEAT SHEET TABLE
    # ============================================================
    story.append(Paragraph("4. Quick Reference Decision Matrix", h1_style))

    matrix_data = [
        [Paragraph("<b>Market State</b>", body_style), Paragraph("<b>Action / Order Type</b>", body_style), Paragraph("<b>Entry Price Level</b>", body_style), Paragraph("<b>Stop Loss</b>", body_style), Paragraph("<b>Target Exit</b>", body_style)],
        [Paragraph("<b>Early Confirmed (Long)</b>", body_style), Paragraph("Limit Buy", body_style), Paragraph("0.60x – 0.80x IDR Retrace", body_style), Paragraph("Opposite DR", body_style), Paragraph("0.5x & 1.2x SD", body_style)],
        [Paragraph("<b>Early Confirmed (Short)</b>", body_style), Paragraph("Limit Sell", body_style), Paragraph("0.60x – 0.80x IDR Retrace", body_style), Paragraph("Opposite DR", body_style), Paragraph("0.5x & 1.2x SD", body_style)],
        [Paragraph("<b>Opposite DR Violated</b>", body_style), Paragraph("Flip Direction", body_style), Paragraph("Opposite Breakout Close", body_style), Paragraph("Original IDR Mid", body_style), Paragraph("2.0x – 2.5x SD", body_style)],
        [Paragraph("<b>Time > Max Ext. Time</b>", body_style), Paragraph("Scale Out / Tighten", body_style), Paragraph("Current Market", body_style), Paragraph("Move to Entry", body_style), Paragraph("0.50x SD / Mid-DR", body_style)],
        [Paragraph("<b>Late Session (3:45 PM)</b>", body_style), Paragraph("Retirement Close", body_style), Paragraph("Pre-close 15m candle", body_style), Paragraph("DR Level", body_style), Paragraph("M15 Session Close", body_style)],
    ]
    t_matrix = Table(matrix_data, colWidths=[1.4 * inch, 1.3 * inch, 1.5 * inch, 1.1 * inch, 1.5 * inch])
    t_matrix.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ALERT_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_matrix)
    story.append(Spacer(1, 14))

    # ============================================================
    # SECTION 5: GOLDEN RULES FOR DISCIPLINE
    # ============================================================
    story.append(Paragraph("5. The 5 Golden Rules of DR Trading", h1_style))
    story.append(Paragraph("1. <b>Never Enter Before Confirmation:</b> The Defining Range hour (9:30–10:30, 3:00–4:00, 19:30–20:30) is strictly for range building. Entering before confirmation reduces your edge from 81% to a 50/50 coin toss.", bullet_style))
    story.append(Paragraph("2. <b>Never Chase Breakout Wicks:</b> More than 86.9% of confirmed sessions retrace into the IDR. Patiently place your limit orders in the 0.60x–0.80x retracement zone.", bullet_style))
    story.append(Paragraph("3. <b>Respect the Clock:</b> Price and time are inseparable. When the clock hits your session's median extension time, do not greedily seek big runners. Bank profits at 0.50x SD.", bullet_style))
    story.append(Paragraph("4. <b>Risk 1% Maximum Per Trade:</b> Use the built-in Trade Calculator to size your contract count so your maximum loss never exceeds 1% of total equity.", bullet_style))
    story.append(Paragraph("5. <b>Trust the 20-Year Baseline:</b> Individual days have noise, but across 36,000+ sessions the math is immutable. Execute the systematic rules without emotional interference.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF generated: {PDF_OUTPUT_PATH} ({os.path.getsize(PDF_OUTPUT_PATH) / 1024:.1f} KB)")


if __name__ == "__main__":
    build_pdf()
