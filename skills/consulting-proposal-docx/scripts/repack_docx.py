#!/usr/bin/env python
"""
repack_docx.py - 解包/重打包 .docx 用于精细 XML 编辑

用法:
  python repack_docx.py unpack input.docx _unpacked_dir
  python repack_docx.py pack _unpacked_dir output.docx
"""
import sys, os, zipfile, shutil

def unpack(src, dst):
    if os.path.exists(dst): shutil.rmtree(dst)
    os.makedirs(dst)
    with zipfile.ZipFile(src) as z:
        z.extractall(dst)
    print(f"✓ Unpacked {src} → {dst}")

def pack(src, dst):
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(src):
            for f in files:
                fp = os.path.join(root, f)
                z.write(fp, os.path.relpath(fp, src))
    print(f"✓ Packed {src} → {dst}")

if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] not in ('unpack', 'pack'):
        print(__doc__); sys.exit(1)
    (unpack if sys.argv[1] == 'unpack' else pack)(sys.argv[2], sys.argv[3])
