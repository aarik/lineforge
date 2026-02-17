import sys
from pathlib import Path
from .utils import which

def resource_path(rel:str)->Path:
    base=getattr(sys,"_MEIPASS",None)
    if base:
        return Path(base)/rel
    return Path(__file__).resolve().parent.parent/rel

def find_potrace()->str|None:
    bundled=resource_path(r"bin\potrace.exe")
    if bundled.exists():
        return str(bundled)
    return which("potrace") or which("potrace.exe")

def find_inkscape()->str|None:
    return which("inkscape") or which("inkscape.exe")

def find_magick()->str|None:
    return which("magick")
