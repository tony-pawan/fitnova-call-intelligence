import os
from io import BytesIO
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch

from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag

class PDFService:
    """
    Service responsible for exporting call intelligence metadata, transcripts, and AI analysis scorecards
    to high-quality, professional PDF reports using ReportLab.
    """

    @staticmethod
    def generate_single_call_pdf(db: Session, call_id: int) -> Optional[bytes]:
        """
        Generates a PDF report for a single call intelligence scorecard.
        """
        call = db.query(Call).filter(Call.id == call_id).first()
        if not call:
            return None

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        styles = getSampleStyleSheet()
        
        # Define clean modern styles
        primary_color = colors.HexColor("#4f46e5")  # Indigo
        text_dark = colors.HexColor("#0f172a")     # Slate 900
        text_muted = colors.HexColor("#475569")    # Slate 600
        bg_light = colors.HexColor("#f8fafc")      # Slate 50
        border_color = colors.HexColor("#e2e8f0")  # Slate 200

        # Styles definition
        title_style = ParagraphStyle(
            'PDFTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color,
            spaceAfter=15
        )

        h2_style = ParagraphStyle(
            'PDFH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            'PDFBody',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_dark,
            spaceAfter=6
        )

        bold_style = ParagraphStyle(
            'PDFBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        muted_style = ParagraphStyle(
            'PDFMuted',
            parent=body_style,
            textColor=text_muted
        )

        bullet_style = ParagraphStyle(
            'PDFBullet',
            parent=body_style,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4
        )

        story = []

        # 1. Main Title
        story.append(Paragraph("FitNova Call Audit Scorecard", title_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", muted_style))
        story.append(Spacer(1, 15))

        # 2. Call Information Table
        story.append(Paragraph("Call Information", h2_style))
        min_sec = f"{int(call.duration_seconds // 60)}m {int(call.duration_seconds % 60)}s"
        upload_time = call.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(call.created_at, datetime) else str(call.created_at)
        
        info_data = [
            [Paragraph("Original Filename:", bold_style), Paragraph(call.original_filename, body_style)],
            [Paragraph("Duration:", bold_style), Paragraph(min_sec, body_style)],
            [Paragraph("Upload Time:", bold_style), Paragraph(upload_time, body_style)],
            [Paragraph("Detected Language:", bold_style), Paragraph(call.language or "Unknown", body_style)],
            [Paragraph("Processing Status:", bold_style), Paragraph(call.status.value, body_style)],
        ]
        
        info_table = Table(info_data, colWidths=[2.0 * inch, 5.0 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_light),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 15))

        # 3. AI Audit Summary
        analysis = call.analysis
        story.append(Paragraph("AI Compliance Audit Summary", h2_style))
        
        if not analysis:
            story.append(Paragraph("No AI analysis scorecards generated for this call recording yet.", body_style))
        else:
            # Score card highlight
            score = analysis.overall_score
            score_color = "#10b981" if score >= 80 else ("#f59e0b" if score >= 65 else "#ef4444")
            score_html = f"<font color='{score_color}'><b>{score} / 100</b></font>"
            
            score_data = [
                [Paragraph("Overall Quality Score:", bold_style), Paragraph(score_html, ParagraphStyle('ScoreVal', parent=bold_style, fontSize=14, leading=16))],
                [Paragraph("AI Audit Summary:", bold_style), Paragraph(analysis.summary, body_style)]
            ]
            score_table = Table(score_data, colWidths=[2.0 * inch, 5.0 * inch])
            score_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LINEBELOW', (0,0), (-1,0), 0.5, border_color),
                ('BOX', (0,0), (-1,-1), 1, border_color),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(score_table)
            story.append(Spacer(1, 15))

            # Strengths, Weaknesses, Recommendations
            story.append(Paragraph("Key Strengths & Identified Weaknesses", h2_style))
            
            # Since recommendations/strengths are stored in the database or JSON, let's load from filesystem if possible
            # or try to parse them from the db recommendation string.
            # Usually recommendations is a string in the DB. Let's list strengths/weaknesses by checking the JSON file.
            analysis_json_path = f"./storage/analysis/call_{call_id}.json"
            strengths = []
            weaknesses = []
            recommendations = []
            
            if os.path.exists(analysis_json_path):
                import json
                try:
                    with open(analysis_json_path, 'r', encoding='utf-8') as f:
                        meta_data = json.load(f)
                        strengths = meta_data.get("strengths", [])
                        weaknesses = meta_data.get("weaknesses", [])
                        recommendations = meta_data.get("recommendations", [])
                except Exception:
                    pass

            if not strengths and analysis.recommendation:
                recommendations = analysis.recommendation.split("\n")

            # Strengths
            story.append(Paragraph("🌟 Key Strengths", h2_style))
            if strengths:
                for s in strengths:
                    story.append(Paragraph(f"• {s}", bullet_style))
            else:
                story.append(Paragraph("None identified.", body_style))
                
            story.append(Spacer(1, 10))
            
            # Weaknesses
            story.append(Paragraph("🚨 Identified Weaknesses", h2_style))
            if weaknesses:
                for w in weaknesses:
                    story.append(Paragraph(f"• {w}", bullet_style))
            else:
                story.append(Paragraph("None identified.", body_style))
            story.append(Spacer(1, 15))

            # Recommendations
            story.append(Paragraph("Auditor Recommendations", h2_style))
            if recommendations:
                for r in recommendations:
                    if r.strip():
                        story.append(Paragraph(f"• {r}", bullet_style))
            else:
                story.append(Paragraph("No recommendations provided.", body_style))
            story.append(Spacer(1, 15))

            # 4. Compliance Violations Table
            story.append(Paragraph("Flagged Compliance Violations", h2_style))
            violations = analysis.issue_tags
            
            if not violations:
                story.append(Paragraph("Clean compliance audit. No issue tags flagged.", ParagraphStyle('SuccessText', parent=body_style, textColor=colors.HexColor("#166534"))))
            else:
                v_headers = [
                    Paragraph("<b>Tag</b>", bold_style),
                    Paragraph("<b>Severity</b>", bold_style),
                    Paragraph("<b>Timestamp</b>", bold_style),
                    Paragraph("<b>Dialogue Quote</b>", bold_style),
                    Paragraph("<b>Auditor Reason</b>", bold_style)
                ]
                v_data = [v_headers]
                
                for v in violations:
                    v_data.append([
                        Paragraph(v.tag, body_style),
                        Paragraph(v.severity.value, ParagraphStyle('SevStyle', parent=bold_style, textColor=colors.HexColor("#ef4444") if v.severity.value in ["Critical", "High"] else colors.HexColor("#f59e0b"))),
                        Paragraph(f"{int(v.timestamp)}s", body_style),
                        Paragraph(f"\"{v.quote}\"", muted_style),
                        Paragraph(v.reason, body_style)
                    ])
                
                v_table = Table(v_data, colWidths=[1.3 * inch, 0.8 * inch, 0.8 * inch, 2.1 * inch, 2.0 * inch])
                v_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), bg_light),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
                    ('BOX', (0,0), (-1,-1), 1, border_color),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(v_table)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_cumulative_pdf(db: Session) -> Optional[bytes]:
        """
        Generates a PDF report for all call records and history currently in the system.
        """
        calls = db.query(Call).order_by(Call.created_at.desc()).all()
        if not calls:
            return None

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        styles = getSampleStyleSheet()
        
        primary_color = colors.HexColor("#4f46e5")
        text_dark = colors.HexColor("#0f172a")
        bg_light = colors.HexColor("#f8fafc")
        border_color = colors.HexColor("#e2e8f0")

        title_style = ParagraphStyle(
            'PDFTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=primary_color,
            spaceAfter=15
        )

        h2_style = ParagraphStyle(
            'PDFH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            'PDFBody',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_dark,
            spaceAfter=6
        )

        bold_style = ParagraphStyle(
            'PDFBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        story = []

        # 1. Title
        story.append(Paragraph("FitNova Cumulative Call Intelligence Report", title_style))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 15))

        # 2. Calculate Dashboard Analytics
        total_calls = len(calls)
        completed_calls = sum(1 for c in calls if c.status == CallStatus.Completed)
        
        analyses = db.query(CallAnalysis).all()
        avg_score = round(sum(a.overall_score for a in analyses) / len(analyses), 1) if analyses else 0.0
        avg_duration = round(sum(c.duration_seconds for c in calls) / len(calls), 1) if calls else 0.0
        avg_dur_min = f"{int(avg_duration // 60)}m {int(avg_duration % 60)}s"

        # Stats summary block
        story.append(Paragraph("System Aggregated Analytics", h2_style))
        
        stats_data = [
            [
                Paragraph("<b>Total Calls Processed</b>", bold_style),
                Paragraph("<b>Completed Runs</b>", bold_style),
                Paragraph("<b>Average Quality Score</b>", bold_style),
                Paragraph("<b>Average Call Duration</b>", bold_style)
            ],
            [
                Paragraph(str(total_calls), body_style),
                Paragraph(str(completed_calls), body_style),
                Paragraph(f"{avg_score} / 100", bold_style),
                Paragraph(avg_dur_min, body_style)
            ]
        ]
        
        stats_table = Table(stats_data, colWidths=[1.75 * inch, 1.75 * inch, 1.75 * inch, 1.75 * inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), bg_light),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 20))

        # 3. List Table of All Audits
        story.append(Paragraph("Call History Log & Performance", h2_style))
        
        headers = [
            Paragraph("<b>ID</b>", bold_style),
            Paragraph("<b>Filename</b>", bold_style),
            Paragraph("<b>Uploaded Date</b>", bold_style),
            Paragraph("<b>Duration</b>", bold_style),
            Paragraph("<b>Pipeline Status</b>", bold_style),
            Paragraph("<b>Score</b>", bold_style)
        ]
        list_data = [headers]
        
        for c in calls:
            c_analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == c.id).first()
            score_text = f"<b>{c_analysis.overall_score}</b>" if c_analysis else "N/A"
            dur_str = f"{int(c.duration_seconds // 60)}m {int(c.duration_seconds % 60)}s"
            up_time = c.created_at.strftime("%Y-%m-%d") if isinstance(c.created_at, datetime) else str(c.created_at)[:10]
            
            list_data.append([
                Paragraph(str(c.id), body_style),
                Paragraph(c.original_filename, body_style),
                Paragraph(up_time, body_style),
                Paragraph(dur_str, body_style),
                Paragraph(c.status.value, body_style),
                Paragraph(score_text, body_style)
            ])
            
        list_table = Table(list_data, colWidths=[0.5 * inch, 2.5 * inch, 1.2 * inch, 1.0 * inch, 1.1 * inch, 0.7 * inch])
        list_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), bg_light),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
            ('BOX', (0,0), (-1,-1), 1, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(list_table)

        # 4. Detailed Single Scorecards combined sequentially
        for c in calls:
            c_analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == c.id).first()
            if c_analysis:
                story.append(PageBreak())
                
                # Title for scorecard
                story.append(Paragraph(f"Scorecard Details: {c.original_filename}", title_style))
                story.append(Spacer(1, 10))
                
                # Mini Information Grid
                score = c_analysis.overall_score
                score_color = "#10b981" if score >= 80 else ("#f59e0b" if score >= 65 else "#ef4444")
                score_html = f"<font color='{score_color}'><b>{score} / 100</b></font>"
                
                mini_info = [
                    [Paragraph("Call ID:", bold_style), Paragraph(str(c.id), body_style), Paragraph("Duration:", bold_style), Paragraph(f"{int(c.duration_seconds // 60)}m {int(c.duration_seconds % 60)}s", body_style)],
                    [Paragraph("Upload Time:", bold_style), Paragraph(c.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(c.created_at, datetime) else str(c.created_at), body_style), Paragraph("Quality Score:", bold_style), Paragraph(score_html, bold_style)]
                ]
                mini_table = Table(mini_info, colWidths=[1.5 * inch, 2.0 * inch, 1.5 * inch, 2.0 * inch])
                mini_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), bg_light),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
                    ('BOX', (0,0), (-1,-1), 1, border_color),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                ]))
                story.append(mini_table)
                story.append(Spacer(1, 10))
                
                # Summary
                story.append(Paragraph("AI Compliance Audit Summary", h2_style))
                story.append(Paragraph(c_analysis.summary, body_style))
                story.append(Spacer(1, 10))
                
                # Key strengths / weaknesses from JSON
                analysis_json_path = f"./storage/analysis/call_{c.id}.json"
                strengths = []
                weaknesses = []
                recommendations = []
                
                if os.path.exists(analysis_json_path):
                    import json
                    try:
                        with open(analysis_json_path, 'r', encoding='utf-8') as f:
                            meta_data = json.load(f)
                            strengths = meta_data.get("strengths", [])
                            weaknesses = meta_data.get("weaknesses", [])
                            recommendations = meta_data.get("recommendations", [])
                    except Exception:
                        pass
                
                if strengths or weaknesses:
                    story.append(Paragraph("🌟 Key Strengths", h2_style))
                    if strengths:
                        for s in strengths:
                            story.append(Paragraph(f"• {s}", ParagraphStyle('BulletStyle', parent=body_style, leftIndent=12, firstLineIndent=-8)))
                    else:
                        story.append(Paragraph("None identified.", body_style))
                    
                    story.append(Spacer(1, 10))
                    
                    story.append(Paragraph("🚨 Identified Weaknesses", h2_style))
                    if weaknesses:
                        for w in weaknesses:
                            story.append(Paragraph(f"• {w}", ParagraphStyle('BulletStyle', parent=body_style, leftIndent=12, firstLineIndent=-8)))
                    else:
                        story.append(Paragraph("None identified.", body_style))
                    story.append(Spacer(1, 10))

                # Recommendations
                if recommendations:
                    story.append(Paragraph("Auditor Recommendations", h2_style))
                    for rec in recommendations:
                        story.append(Paragraph(f"• {rec}", ParagraphStyle('BulletStyle', parent=body_style, leftIndent=12, firstLineIndent=-8)))
                    story.append(Spacer(1, 10))
                
                # Compliance violations
                violations = c_analysis.issue_tags
                if violations:
                    story.append(Paragraph("Flagged Compliance Violations", h2_style))
                    v_headers = [Paragraph("<b>Tag</b>", bold_style), Paragraph("<b>Severity</b>", bold_style), Paragraph("<b>Timestamp</b>", bold_style), Paragraph("<b>Dialogue Quote</b>", bold_style)]
                    v_data = [v_headers]
                    for v in violations:
                        v_data.append([
                            Paragraph(v.tag, body_style),
                            Paragraph(v.severity.value, ParagraphStyle('SevStyle', parent=bold_style, textColor=colors.HexColor("#ef4444") if v.severity.value in ["Critical", "High"] else colors.HexColor("#f59e0b"))),
                            Paragraph(f"{int(v.timestamp)}s", body_style),
                            Paragraph(f"\"{v.quote}\"", ParagraphStyle('QuoteStyle', parent=body_style, textColor=colors.HexColor("#475569"), fontName='Helvetica-Oblique'))
                        ])
                    v_table = Table(v_data, colWidths=[1.5 * inch, 0.9 * inch, 0.9 * inch, 3.7 * inch])
                    v_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), bg_light),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
                        ('BOX', (0,0), (-1,-1), 1, border_color),
                        ('TOPPADDING', (0,0), (-1,-1), 4),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                        ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(v_table)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
