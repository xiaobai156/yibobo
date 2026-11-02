import json, pathlib
c = json.loads(pathlib.Path("recent_10_cache.json").read_text(encoding="utf-8"))
for n in ("桃花没酒", "软妹味道"):
    d = c["sites"][n]["data"]
    print(n, "缺:", [p for p in c["periods"] if str(p) not in d], "289/290:", d.get("289"), d.get("290"))
