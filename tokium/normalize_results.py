# -*- coding: utf-8 -*-
"""検証結果の I列 判定記号を正規化する。

初期の波は「数値・出典は誤りだが架電可否は○」というケースに × を付けていた。
× は「リストから外す」を意味するため、そのままでは架電できる企業を落とす。
本文中に ○維持 等の明示があるものを「○ 妥当（G列訂正：…）」へ倒す。
"""
import json, glob, csv, re, sys

KEEP_OK = [r"（○維持）", r"\(○維持\)", r"○維持", r"架電可否は○", r"架電可否自体は○",
           r"架電可否の結論は動かない", r"○を維持", r"300億超も維持", r"300億超も確実"]
# 明示的に覆したと述べている行は正規化しない（○→△ 等の表記が KEEP_OK に誤マッチするため）
FLIPPED = [r"○\s*[→⇒]\s*[△×]", r"反証成立", r"架電不可", r"載せられない", r"直アポ大に載せ"]

def normalize(I):
    if not I: return I, False
    head = I[:1]
    if head == "○":
        return I, False
    if any(re.search(p, I) for p in FLIPPED):
        return I, False
    if head in ("×", "△") and any(re.search(p, I) for p in KEEP_OK):
        body = re.sub(r"^[×△]\s*(要修正|要再確認)\s*[:：]\s*", "", I)
        return f"○ 妥当（G列訂正：{body}", True
    return I, False

def load_all(SP):
    out = {}
    for pat in (f"{SP}/out/out_*.json", f"{SP}/w2/out_*.json", f"{SP}/waves/out_w*.json"):
        for f in sorted(glob.glob(pat)):
            for x in json.load(open(f, encoding="utf-8")):
                out[x["行"]] = x
    return out

if __name__ == "__main__":
    SP = "/tmp/claude-0/-home-user--/fcda6a82-279b-5a30-a006-b52ce02ba704/scratchpad"
    out = load_all(SP)
    changed = []
    for n, x in out.items():
        new, ch = normalize(x["I"])
        if ch:
            changed.append((n, x["I"][:70], new[:70])); x["I"] = new
    print(f"正規化: {len(changed)}行")
    for n, a, b in sorted(changed):
        print(f"  行{n}\n    前: {a}\n    後: {b}")
    json.dump({str(k): v for k, v in out.items()},
              open(f"{SP}/normalized.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
