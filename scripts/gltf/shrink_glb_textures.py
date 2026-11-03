"""Shrink the embedded textures of a binary glTF (.glb) without touching geometry.

AI image-to-3D generators often return GLBs with several 2K-4K PNG textures.
This script re-encodes colour textures (base colour, emissive) as JPEG when
they have no transparency, keeps data textures (normal, metallic-roughness,
occlusion) as PNG, and optionally caps the longest edge of each.

Usage:
    python shrink_glb_textures.py in.glb out.glb [max_edge=2048] [jpeg_quality=85] [max_edge_data=max_edge]
"""
import io
import json
import struct
import sys

from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
MAX_COLOR = int(sys.argv[3]) if len(sys.argv) > 3 else 2048
QUALITY = int(sys.argv[4]) if len(sys.argv) > 4 else 85
MAX_DATA = int(sys.argv[5]) if len(sys.argv) > 5 else MAX_COLOR

data = open(src, "rb").read()
magic, _version, length = struct.unpack_from("<4sII", data, 0)
assert magic == b"glTF", "not a binary glTF file"

off, js, binc = 12, None, b""
while off < length:
    clen, ctype = struct.unpack_from("<I4s", data, off)
    chunk = data[off + 8: off + 8 + clen]
    if ctype == b"JSON":
        js = json.loads(chunk)
    elif ctype == b"BIN\x00":
        binc = chunk
    off += 8 + clen

views = js["bufferViews"]
image_of_view = {im["bufferView"]: i for i, im in enumerate(js.get("images", [])) if "bufferView" in im}

# Colour textures may become JPEG; normal / ORM maps must stay lossless.
color_images = set()
for mat in js.get("materials", []):
    for tex in (mat.get("pbrMetallicRoughness", {}).get("baseColorTexture"), mat.get("emissiveTexture")):
        if tex:
            color_images.add(js["textures"][tex["index"]]["source"])

out = bytearray()
new_views = []
for i, view in enumerate(views):
    start = view.get("byteOffset", 0)
    raw = binc[start: start + view["byteLength"]]
    if i in image_of_view:
        ii = image_of_view[i]
        im = Image.open(io.BytesIO(raw))
        limit = MAX_COLOR if ii in color_images else MAX_DATA
        if max(im.size) > limit:
            im.thumbnail((limit, limit), Image.LANCZOS)
        buf = io.BytesIO()
        if ii in color_images:
            if im.mode == "P":
                im = im.convert("RGBA")
            if im.mode == "RGBA" and im.getextrema()[3][0] == 255:  # fully opaque
                im = im.convert("RGB")
        if ii in color_images and im.mode == "RGB":
            im.save(buf, "JPEG", quality=QUALITY, optimize=True)
            js["images"][ii]["mimeType"] = "image/jpeg"
        else:
            if im.mode not in ("RGB", "RGBA", "L"):
                im = im.convert("RGBA")
            im.save(buf, "PNG", optimize=True)
            js["images"][ii]["mimeType"] = "image/png"
        raw = buf.getvalue()
    while len(out) % 4:
        out.append(0)
    nv = dict(view)
    nv["byteOffset"] = len(out)
    nv["byteLength"] = len(raw)
    out += raw
    new_views.append(nv)
while len(out) % 4:
    out.append(0)

js["bufferViews"] = new_views
js["buffers"] = [{"byteLength": len(out)}]
jb = json.dumps(js, separators=(",", ":")).encode()
while len(jb) % 4:
    jb += b" "
total = 12 + 8 + len(jb) + 8 + len(out)
with open(dst, "wb") as f:
    f.write(struct.pack("<4sII", b"glTF", 2, total))
    f.write(struct.pack("<I4s", len(jb), b"JSON"))
    f.write(jb)
    f.write(struct.pack("<I4s", len(out), b"BIN\x00"))
    f.write(out)
print(dst, total // 1024, "KB", [im.get("mimeType") for im in js.get("images", [])])
