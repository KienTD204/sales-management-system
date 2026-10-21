"""Đóng gói nguồn đã kiểm thử và đối chiếu SHA256 từng file."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.venv','venv','__pycache__','.pytest_cache','node_modules','instance','htmlcov','playwright-report'}


def release_files():
    files=[]
    for file in ROOT.rglob('*'):
        if not file.is_file():continue
        relative=file.relative_to(ROOT)
        if any(part in EXCLUDED for part in relative.parts):continue
        if file.name.startswith('.env') and file.name!='.env.example':continue
        if file.name.startswith('failure') or 'development' in file.name:continue
        if file.suffix in {'.pyc','.log','.zip'} or file.name.endswith(('-qa.pdf','-qa.csv')):continue
        if file.name=='RELEASE-MANIFEST.sha256':continue
        files.append(file)
    return sorted(files)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    summary=json.loads((ROOT/'docs/test-results/week9-summary.json').read_text(encoding='utf-8'))
    assert summary['failures']==0 and summary['modules']==13 and summary['python_passed']>=237 and summary['browser_passed']>=131, 'Chưa có đủ log đạt'
    assert (ROOT/'report/Phu-luc-Kiem-thu-Tuan-9.docx').is_file()
    missing=[]
    for file in ROOT.rglob('*.md'):
        if any(part in EXCLUDED for part in file.relative_to(ROOT).parts):continue
        for target in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            if not (file.parent/target.split('#')[0]).exists():missing.append((str(file.relative_to(ROOT)),target))
    assert not missing,missing
    files=release_files()
    hashes={file.relative_to(ROOT).as_posix():hashlib.sha256(file.read_bytes()).hexdigest() for file in files}
    manifest=ROOT/'RELEASE-MANIFEST.sha256'
    manifest.write_text(''.join(f'{value}  {name}\n' for name,value in hashes.items()),encoding='utf-8')
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for file in files+[manifest]:archive.write(file,Path(ROOT.name)/file.relative_to(ROOT))
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        for name,digest in hashes.items():assert hashlib.sha256(archive.read(ROOT.name+'/'+name)).hexdigest()==digest
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n',encoding='utf-8')
    print(json.dumps({'archive':str(output),'files':len(files)+1,'bytes':output.stat().st_size,'sha256':digest,'tests':summary},ensure_ascii=False))


if __name__=='__main__':main()
