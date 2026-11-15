"""Read-only completeness checks; write only this demonstration's new evidence."""
from pathlib import Path
import ast,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/demonstration_20261115'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tests(p):
    cases=ET.parse(p).getroot().findall('.//testcase');failed=sum(x.find('failure') is not None or x.find('error') is not None for x in cases);skipped=sum(x.find('skipped') is not None for x in cases)
    return {'total':len(cases),'passed':len(cases)-failed-skipped,'failed':failed,'skipped':skipped}
def main():
    old=json.loads((ROOT/'evidence/followup_20261115/followup_manifest.json').read_text());known={x['path']:x['sha256'] for x in old['files']}
    checks={'full_suite':tests(ROOT/'evidence/followup_20261115/verified_pid/full_tests.xml'),'focused_suite':tests(OUT/'targeted_tests_final.xml'),'focused_exit_code':json.loads((OUT/'targeted_tests_final.json').read_text())['exit_code'],'readiness':json.loads((OUT/'readiness_actual.stdout.txt').read_text()),'historical_evidence_hash_mismatches':[p for p,h in known.items() if p.startswith('evidence/followup_20261115/') and sha(ROOT/p)!=h]}
    preserved=['data/sprints_learner_db.csv','data/sprints_learner.db','notebooks/evaluator_optimizer_verified.ipynb','submission/technical_report.pdf','submission/stakeholder_presentation.pptx','submission/stakeholder_presentation.pdf','submission/sprints-ai-orchestrator-final.zip']
    checks['preserved_files']={p:sha(ROOT/p)==known[p] for p in preserved}
    expected=['README.md','requirements.txt','requirements-lock.txt','notebooks/evaluator_optimizer_verified.ipynb','data/sprints_learner_db.csv','data/sprints_learner.db','docs/data_provenance.md','submission/technical_report_current.pdf','submission/stakeholder_presentation_current.pptx','submission/stakeholder_presentation_current.pdf','docs/demo_recording_script.md','docs/live_verification_plan.md','docs/openai_preflight.template.json','docs/rag_readiness.md','docs/audit/demo_readiness.md']
    checks['required_local_files']={p:(ROOT/p).is_file() for p in expected}
    checks['report_pages']=len(PdfReader(ROOT/'submission/technical_report_current.pdf').pages);checks['slide_pdf_pages']=len(PdfReader(ROOT/'submission/stakeholder_presentation_current.pdf').pages)
    with zipfile.ZipFile(ROOT/'submission/stakeholder_presentation_current.pptx') as z:
        names=z.namelist();checks['pptx_slides']=sum(bool(re.fullmatch(r'ppt/slides/slide[0-9]+.xml',p)) for p in names);checks['native_chart_present']=any('/charts/' in p and p.endswith('.xml') and '/_rels/' not in p and ET.fromstring(z.read(p)).tag=='{http://schemas.openxmlformats.org/drawingml/2006/chart}chartSpace' for p in names);checks['chart_workbook_present']=any(p.startswith('ppt/embeddings/') and p.endswith('.xlsx') for p in names);checks['native_table_present']=any(b'<a:tbl>' in z.read(p) for p in names if re.fullmatch(r'ppt/slides/slide[0-9]+.xml',p))
    nb=json.loads((ROOT/'notebooks/evaluator_optimizer_verified.ipynb').read_text());cells=[c for c in nb['cells'] if c['cell_type']=='code'];checks['notebook']={'executed_cells':sum(c.get('execution_count') is not None for c in cells),'errors':sum(o.get('output_type')=='error' for c in cells for o in c['outputs'])}
    with zipfile.ZipFile(ROOT/'submission/sprints-ai-orchestrator-final.zip') as z:
        names=z.namelist();checks['preserved_zip_entries']=len(names);checks['preserved_zip_forbidden_entries']=[p for p in names if any(t in p.split('/') for t in ('.venv','.venv-audit','__pycache__','.env','.git'))];checks['preserved_zip_current_source_complete']=all(p in names and z.read(p)==(ROOT/p).read_bytes() for p in ('src/startup.py','src/preflight.py','src/main.py','src/live_controls.py'))
    files=[p for d in ('src','tests','scripts','docs','_client_sources') for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts];broken=[];secrets=[];pycount=0
    for p in files+[ROOT/'README.md',ROOT/'.env.example']:
        if p.suffix not in ('.py','.md','.json','.txt','.ps1') and p.name!='.env.example':continue
        text=p.read_text(encoding='utf-8-sig',errors='replace')
        if p.suffix=='.py':ast.parse(text,filename=str(p));pycount+=1
        if re.search(r'sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',text):secrets.append(p.relative_to(ROOT).as_posix())
        if p.suffix=='.md':
            for href in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
                if href.startswith(('http://','https://','mailto:','#')):continue
                target=href.strip('<>').split('#',1)[0]
                if target and not (p.parent/target).exists():broken.append({'file':str(p.relative_to(ROOT)),'target':target})
    checks.update(parsed_python_files=pycount,broken_links=broken,potential_secret_patterns=secrets,git_metadata_present=(ROOT/'.git').exists(),shareable_source_url=None,video_files=[p.name for p in (ROOT/'submission').iterdir() if p.suffix.lower() in ('.mp4','.mov','.webm','.mkv')],video_status='PENDING',openai_requests=0,full_security_suite_repeated=False,docker_rebuilt=False,dependencies_reinstalled=False,verdict='NOT READY')
    checks['local_checks_pass']=all(checks['preserved_files'].values()) and not checks['historical_evidence_hash_mismatches'] and all(checks['required_local_files'].values()) and checks['full_suite']['passed']==157 and checks['focused_suite']['passed']==70 and checks['focused_exit_code']==0 and checks['report_pages']==16 and checks['slide_pdf_pages']==checks['pptx_slides']==10 and checks['native_chart_present'] and checks['native_table_present'] and checks['chart_workbook_present'] and not broken and not secrets and not checks['preserved_zip_forbidden_entries']
    (OUT/'quality_gate.json').write_text(json.dumps(checks,indent=2),encoding='utf-8');print(json.dumps(checks,indent=2));return 0 if checks['local_checks_pass'] else 1
if __name__=='__main__':raise SystemExit(main())
