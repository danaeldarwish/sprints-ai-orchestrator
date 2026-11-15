"""Faithful PDF from actual reimported PPTX renders; no invented slide content."""
from pathlib import Path
from reportlab.pdfgen import canvas
ROOT=Path(__file__).resolve().parents[1]
target=ROOT/"submission/stakeholder_presentation.pdf"
images=sorted((ROOT/"evidence/rendered/slides").glob("slide-*.png"))
assert len(images)==10
c=canvas.Canvas(str(target),pagesize=(1280,720),pageCompression=1)
c.setTitle("Sprints Orchestrator Stakeholder Presentation")
for image in images:
    c.drawImage(str(image),0,0,width=1280,height=720,preserveAspectRatio=True)
    c.showPage()
c.save()
print("Created 10-page presentation PDF from final PPTX renders")
