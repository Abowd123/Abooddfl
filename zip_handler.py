from __future__ import annotations
import asyncio, shutil, zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

@dataclass(slots=True)
class ZipEntry:
    path:str; source:Path; size:int

class ZipSecurityError(ValueError): pass

def sanitize_member(name:str)->str:
    normalized=str(PurePosixPath(name.replace('\\','/')))
    if normalized.startswith('/') or '..' in PurePosixPath(normalized).parts or '\x00' in normalized: raise ZipSecurityError(f'Unsafe path: {name}')
    if normalized.startswith('__MACOSX/'): return ''
    return normalized.lstrip('/')

async def extract_zip(zip_path:Path,destination:Path,max_files:int,max_bytes:int)->list[ZipEntry]:
    return await asyncio.to_thread(_extract,zip_path,destination,max_files,max_bytes)

def _extract(zip_path:Path,destination:Path,max_files:int,max_bytes:int)->list[ZipEntry]:
    shutil.rmtree(destination,ignore_errors=True); destination.mkdir(parents=True,exist_ok=True)
    entries=[]; total=0
    with zipfile.ZipFile(zip_path) as zf:
        infos=[i for i in zf.infolist() if not i.is_dir()]
        if len(infos)>max_files: raise ZipSecurityError(f'عدد الملفات يتجاوز الحد: {max_files}')
        for info in infos:
            name=sanitize_member(info.filename)
            if not name: continue
            total+=info.file_size
            if total>max_bytes: raise ZipSecurityError('الحجم بعد فك الضغط يتجاوز الحد المسموح')
            target=(destination/name).resolve()
            if destination.resolve() not in target.parents: raise ZipSecurityError('ZIP path traversal detected')
            target.parent.mkdir(parents=True,exist_ok=True)
            with zf.open(info) as src,target.open('wb') as dst: shutil.copyfileobj(src,dst,1024*1024)
            entries.append(ZipEntry(name,target,info.file_size))
    return sorted(entries,key=lambda e:e.path)
