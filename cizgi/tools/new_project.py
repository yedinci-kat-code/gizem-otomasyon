#!/usr/bin/env python3
"""cizgi-short · yeni proje kurar.  python new_project.py <hedef_klasör>
Kiti (engine, three.js, font, araçlar) kopyalar; story.js'i örnekten başlatır. İnternet gerekmez."""
import sys, os, shutil
kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2: sys.exit(__doc__)
dst = os.path.abspath(sys.argv[1]); os.makedirs(dst, exist_ok=True)
for d in ("engine", "vendor", "fonts", "tools"):
    shutil.copytree(os.path.join(kit, d), os.path.join(dst, d), dirs_exist_ok=True)
for d in ("work", "frames", "stills", "out"): os.makedirs(os.path.join(dst, d), exist_ok=True)
if not os.path.exists(os.path.join(dst, "story.js")):
    shutil.copy(os.path.join(kit, "example", "story.js"), os.path.join(dst, "story.js"))
print("proje hazır:", dst)
print("sıradaki: work/voice.mp3 + script.txt koy → python tools/timing.py", dst)
