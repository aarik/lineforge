from pathlib import Path
from PIL import Image

def pad_square(in_path:Path,out_base:Path,size:int,bg_mode:str,out_fmt:str,jpeg_quality:int=95)->Path:
    bg=(0,0,0) if bg_mode=="black" else (255,255,255)
    img=Image.open(in_path)

    if img.mode in ("RGBA","LA") or "transparency" in img.info:
        img=img.convert("RGBA")
        flat=Image.new("RGBA",img.size,bg+(255,))
        flat.paste(img,(0,0),img)
        img=flat.convert("RGB")
    else:
        img=img.convert("RGB")

    w,h=img.size
    scale=min(size/w,size/h)
    nw,nh=int(w*scale),int(h*scale)
    img=img.resize((nw,nh),Image.LANCZOS)

    canvas=Image.new("RGB",(size,size),bg)
    canvas.paste(img,((size-nw)//2,(size-nh)//2))

    out_base.parent.mkdir(parents=True,exist_ok=True)

    if out_fmt in ("jpg","jpeg"):
        p=out_base.with_suffix(".jpg")
        canvas.save(p,quality=jpeg_quality)
    else:
        p=out_base.with_suffix(".png")
        canvas.save(p)

    return p
