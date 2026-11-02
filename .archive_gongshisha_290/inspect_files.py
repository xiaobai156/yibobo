import json, pathlib
for name in ("sites.json", "recent_10_cache.json", "archived_sites.json"):
    b = pathlib.Path(name).read_bytes()
    print(name, "size=", len(b), "crlf=", b.count(b"\r\n"), "lf=", b.count(b"\n"), "tail=", repr(b[-24:]))
a = json.loads(pathlib.Path("archived_sites.json").read_text(encoding="utf-8"))
print("archived keys:", list(a.keys()), "sites=", len(a["sites"]), "names=", [s["name"] for s in a["sites"]])
print("entry keys:", list(a["sites"][0].keys()))
c = json.loads(pathlib.Path("recent_10_cache.json").read_text(encoding="utf-8"))
print("cache sites=", len(c["sites"]), "periods=", c["periods"], "updated_at=", c["updated_at"])
print("公式杀 entry:", json.dumps(c["sites"]["公式杀"], ensure_ascii=False))
s = json.loads(pathlib.Path("sites.json").read_text(encoding="utf-8"))
print("sites.json count=", len(s), "公式杀=", [x for x in s if x["name"]=="公式杀"])
