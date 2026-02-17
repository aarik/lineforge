import shutil, subprocess
from pathlib import Path
from typing import Optional, List

IMG_EXTS = {".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff"}

def which(cmd:str)->Optional[str]:
    return shutil.which(cmd)

def run_cmd(args:List[str])->None:
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if p.returncode!=0:
        raise RuntimeError("Command failed:\n"+" ".join(args)+"\n"+p.stderr)

def list_images(path:Path)->list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in IMG_EXTS else []
    return sorted(p for p in path.iterdir() if p.suffix.lower() in IMG_EXTS)
