from pathlib import Path
import zipfile,pytest
from utils.progress import bar
from zip_handler import extract_zip,ZipSecurityError

def test_bar():assert bar(50,10)=='█████░░░░░'
@pytest.mark.asyncio
async def test_extract(tmp_path:Path):
 z=tmp_path/'x.zip'
 with zipfile.ZipFile(z,'w') as f:f.writestr('a/b.txt','ok')
 out=tmp_path/'out';entries=await extract_zip(z,out,10,1000);assert entries[0].path=='a/b.txt'
@pytest.mark.asyncio
async def test_zip_slip(tmp_path:Path):
 z=tmp_path/'x.zip'
 with zipfile.ZipFile(z,'w') as f:f.writestr('../evil','x')
 with pytest.raises(ZipSecurityError):await extract_zip(z,tmp_path/'out',10,1000)
