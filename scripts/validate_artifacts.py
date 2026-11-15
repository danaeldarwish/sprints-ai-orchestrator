"""Count and render final artifacts; structural checks supplement visual review."""
from pathlib import Path
import json,re,zipfile,xml.etree.ElementTree as ET
import nbformat
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
def main():
    output=ROOT/"evidence"/"rendered"/"report";output.mkdir(parents=True,exist_ok=True)
    pdf=fitz.open(ROOT/"submission"/"technical_report.pdf")
    boxes=[]
    for i,page in enumerate(pdf):
        page.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(output/f"report-{i+1:02}.png")
        for block in page.get_text("blocks"):
            x0,y0,x1,y1=block[:4]
            if x0<0 or y0<0 or x1>page.rect.width+1 or y1>page.rect.height+1:boxes.append({"page":i+1,"box":block[:4]})
    slides_pdf=fitz.open(ROOT/"submission"/"stakeholder_presentation.pdf")
    with zipfile.ZipFile(ROOT/"submission"/"stakeholder_presentation.pptx") as z:
        slides=[n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml",n)]
        charts=[n for n in z.namelist() if n.endswith(".xml") and "charts/" in n and "/_rels/" not in n and ET.fromstring(z.read(n)).tag.endswith("}chartSpace")]
        tables=sum(len(ET.fromstring(z.read(n)).findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}tbl")) for n in slides)
        assert z.testzip() is None
    nb=nbformat.read(ROOT/"notebooks"/"evaluator_optimizer_loop.ipynb",as_version=4);nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=="code"]
    result={"report_pages":len(pdf),"presentation_slides":len(slides),"presentation_pdf_pages":len(slides_pdf),
            "native_charts":len(charts),"native_tables":tables,"report_outside_page_text_boxes":boxes,
            "notebook_code_cells":len(cells),"notebook_all_executed":all(c.execution_count is not None for c in cells),
            "notebook_errors":sum(o.output_type=="error" for c in cells for o in c.outputs),
            "video_status":"PENDING","video_duration_seconds":None,"powerpoint_application_opened":False}
    assert len(pdf)>0 and len(slides)==len(slides_pdf)==10
    assert len(charts)==1 and tables==1 and not boxes
    assert result["notebook_all_executed"] and result["notebook_errors"]==0
    (ROOT/"evidence"/"artifact_validation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
