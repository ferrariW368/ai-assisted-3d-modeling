"""Convert a .glb into a single self-contained .gltf JSON file (binary buffer as a data URI).

Useful when a hosting environment serves JSON but blocks binary model files.
Note: the browser side then has to rebuild a GLB (or let the loader read the data URI).

Usage:
    python glb_to_embedded_gltf.py in.glb out.json
"""
import base64
import json
import struct
import sys

data = open(sys.argv[1], "rb").read()
off, js, binc = 12, None, b""
while off < len(data):
    length, ctype = struct.unpack_from("<I4s", data, off)
    chunk = data[off + 8: off + 8 + length]
    if ctype == b"JSON":
        js = json.loads(chunk)
    elif ctype == b"BIN\x00":
        binc = chunk
    off += 8 + length

js["buffers"] = [{
    "byteLength": len(binc),
    "uri": "data:application/octet-stream;base64," + base64.b64encode(binc).decode(),
}]
with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write(json.dumps(js, separators=(",", ":")))
