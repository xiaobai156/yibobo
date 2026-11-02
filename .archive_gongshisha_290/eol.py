import pathlib
for n in ("sites.json", "recent_10_cache.json", "archived_sites.json"):
    b = pathlib.Path(n).read_bytes(); b0 = pathlib.Path(".archive_gongshisha_290/before") / n
    b0 = b0.read_bytes()
    print(f"{n}: now size={len(b)} crlf={b.count(bytes([13,10]))} lf={b.count(bytes([10]))} tail={b[-12:]!r}")
    print(f"    before size={len(b0)} crlf={b0.count(bytes([13,10]))} lf={b0.count(bytes([10]))} tail={b0[-12:]!r}")
