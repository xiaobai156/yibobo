import json, pathlib
p = pathlib.Path("杀一波/recent_10_cache.json"); t = p.read_text(encoding="utf-8")
b = p.read_bytes()
print("cache size=", len(b), "crlf=", b.count(b"\r\n"), "lf=", b.count(b"\n"), "tail=", repr(b[-16:]))
print("cache sites=", len(json.loads(t)["sites"]), "公式杀 in cache:", "公式杀" in t)
s = pathlib.Path("七类数据统一归纳/290期-一波.txt"); st = s.read_text(encoding="utf-8")
print("succ size=", s.stat().st_size, "lines=", len(st.splitlines()), "crlf=", st.count("\r\n"), "lf=", st.count("\n"))
print("头 3 行:", st.splitlines()[:3]); print("尾 6 行:", st.splitlines()[-6:])
