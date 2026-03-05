"""Create a multi-page sample customer call transcript PDF for call log analytics demos."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


OUTPUT_DIR = Path(__file__).resolve().parent / "sample_data" / "call_logs"
OUTPUT_FILE = OUTPUT_DIR / "skyler_young_call_transcript_2026-02-21.pdf"


def _transcript_paragraphs() -> list[str]:
    return [
        "Call title: Territory follow-up with Skyler Young (Cardiovascular Surgeon) at Valley Regional Hospital.",
        "Date: 2026-02-21. Channel: In-person follow-up summarized and transcribed by sales notes workflow.",
        "Rep (J&J): Dr. Young, thank you for making time today. I wanted to follow up on your previous outreach where you noted interest in strengthening product adoption and clinical follow-up support for your cardiovascular cases.",
        "Skyler Young: Thanks for coming by. We are trying to standardize usage patterns across the team. We have mixed familiarity with specific heart recovery products and are also balancing OR schedule pressure.",
        "Rep (J&J): That aligns with what we have seen in similar institutions. I reviewed your utilization trends and wanted to discuss where Impella CP and Impella 5.5 could be used more consistently, especially for qualifying high-risk PCI and cardiogenic shock workflows.",
        "Skyler Young: Clinically, the cases are there. The blocker is confidence and cadence. Some physicians are very experienced, but newer team members are less comfortable selecting early support strategies.",
        "Rep (J&J): Understood. We can sequence this in three phases: clinical refresher, case-selection alignment, and post-case debrief support. We can also provide role-specific materials for surgeons, interventional cardiologists, and ICU partners.",
        "Skyler Young: That would help. If we can bring everyone to a common baseline, we can reduce variation in the first 24 hours of post-op management.",
        "Rep (J&J): I also want to make sure the nursing and cath lab teams have practical checklists. We can combine product training with process checkpoints so handoffs remain predictable.",
        "Skyler Young: Yes, handoffs are where we lose consistency. A short checklist and quick-reference sheet would be useful.",
        "Rep (J&J): Great. On the product side, are there specific scenarios where your team is uncertain between Impella CP and Impella 5.5?",
        "Skyler Young: The ambiguity is mostly around escalation timing and expected duration of support. We have internal preferences, but they are not always documented clearly.",
        "Rep (J&J): We can address that with a concise decision support worksheet built around your local protocols. We can draft it with your clinical lead and adjust language so it matches your governance process.",
        "Skyler Young: That sounds reasonable. We need something practical, not another dense deck.",
        "Rep (J&J): Agreed. We will keep it operational. We can run one 30-minute team touchpoint focused on three representative case types and leave behind one-page guidance.",
        "Skyler Young: Good. Also include common pitfalls, especially around communication timing between surgery, ICU, and pharmacy.",
        "Rep (J&J): Noted. I captured that as a follow-up objective. We can incorporate communication triggers and ownership checkpoints into the support materials.",
        "Skyler Young: If we can make this easy to adopt, I can advocate for a pilot in the next cycle.",
        "Rep (J&J): Perfect. Proposed next steps: (1) send draft support packet by Tuesday, (2) align on pilot cohort with your coordinator, (3) schedule a 15-minute checkpoint in two weeks.",
        "Skyler Young: Works for me. Send it to my office and copy our coordinator so we can move quickly.",
        "Rep (J&J): Will do. Last question: any concerns about implementation burden from your side?",
        "Skyler Young: Time and staffing, mainly. If your materials are concise and we keep the pilot focused, I think we can proceed.",
        "Rep (J&J): Thanks, that is clear. I will keep the package lightweight and outcome-oriented. I appreciate the partnership.",
        "Skyler Young: Thank you. Looking forward to the follow-up.",
        "Post-call rep note: Customer remains high-priority with strong receptiveness. Recommended action is a short, role-specific follow-up with practical assets tied to cardiovascular workflows and Abiomed Impella products.",
        "Post-call rep note: Suggested content package should include one-page scenario mapping, checklist for handoffs, escalation timing reminders, and a concise implementation cadence for the pilot team.",
        "Post-call rep note: Customer asked for direct coordination with internal stakeholders; include coordinator in outreach and keep scheduling ask low-friction.",
    ]


def create_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    heading = styles["Heading2"]
    heading.fontName = "Helvetica-Bold"

    body = ParagraphStyle(
        "TranscriptBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        spaceAfter=8,
    )

    story = [
        Paragraph("Butterfly Customer Intelligence - Sample Call Transcript", heading),
        Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", body),
        Spacer(1, 8),
    ]

    for line in _transcript_paragraphs() * 2:
        story.append(Paragraph(line, body))

    doc.build(story)


if __name__ == "__main__":
    create_pdf(OUTPUT_FILE)
    print(f"Wrote {OUTPUT_FILE}")
