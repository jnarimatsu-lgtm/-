# -*- coding: utf-8 -*-
"""要確認リストを最終データから作り直す。
各リストは会話の途中でその場限りに作ったので、成果物の数字が食い違わないよう
1本にまとめた。final_check.sh の前にこれを回す。"""
import csv, re, json, collections

R = "tokium/results/"
rows = list(csv.DictReader(open(R + "IJ_paste_FULL.csv", encoding="utf-8-sig")))
ok = [r for r in rows if r["最終判定"].startswith("架電可")]
NUM = r"[\d,]+(?:\.\d+)?"

def dump(name, data):
    json.dump(data, open(R + name, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  %-38s %d件" % (name, len(data)))

def maxoku(t):
    """文中の最大の金額を億円で返す。URLと法人番号の数字は除く。"""
    t = re.sub(r"(\d)\.\s*(\d)", r"\1.\2", (t or "").replace("　", " "))
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"法人番号\s*\d{13}", "", t)
    best = None
    for m in re.finditer(r"(%s)\s*兆(?:\s*(%s)\s*億)?" % (NUM, NUM), t):
        v = float(m.group(1).replace(",", "")) * 10000 + (float(m.group(2).replace(",", "")) if m.group(2) else 0)
        best = v if best is None else max(best, v)
    for m in re.finditer(r"(%s)\s*億" % NUM, t):
        v = float(m.group(1).replace(",", ""))
        best = v if best is None else max(best, v)
    return best

print("要確認リストを再生成:")

# 1) G列の訂正 — 判定ラベルと I列先頭140字（判定文の位置）で判断する。
NEED = re.compile(r"G列(?:を|は|が|の)?\s*(?:訂正|要訂正|空欄|記入が必要|差し替え|書き換え|修正)")
NOT_ = re.compile(r"(訂正不要|訂正の必要(?:も)?(?:なし|ない|認めず)|修正不要|訂正は不要)")
g = []
for r in rows:
    I = r["I列_検証結果"] or ""
    if "G列訂正" in r["最終判定"] or (NEED.search(I[:140]) and not NOT_.search(I[:140])):
        m = re.search(r"G列(?:訂正)?[：:（(][^。]{0,100}", I) or NEED.search(I)
        g.append({"行": int(r["行"]), "取引先ID": r["取引先ID"], "法人番号": r["法人番号"],
                  "取引先名": r["取引先名"], "最終判定": r["最終判定"],
                  "G列の訂正指示": m.group(0)[:140] if m else "", "I列_検証結果": I})
with open(R + "G_column_corrections.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(g[0].keys())); w.writeheader(); w.writerows(g)
print("  %-38s %d件" % ("G_column_corrections.csv", len(g)))

# 2) 出典の数値でなく推定で架電可になっている行（基準の2倍未満のものだけ）
INFER = r"(規模|と思われ|と見られ|推計|按分|蓋然性|はず|であろう|考えられ|推定|見込ま)"
SKIP = r"(整合|矛盾しな|倍で|クリア|桁違い|誤って当てた|当てたものではな|形跡|大きく超|大幅超|を当てた)"
inf = []
for r in ok:
    I = r["I列_検証結果"] or ""
    for m in re.finditer(r"(?:約)?\s*(%s)\s*(?:〜\s*%s\s*)?億[^。]{0,22}?%s" % (NUM, NUM, INFER), I):
        seg = I[max(0, m.start() - 40):m.end() + 14]
        if re.search(SKIP, seg): continue
        v = float(m.group(1).replace(",", ""))
        if v >= 600: continue
        inf.append({"行": int(r["行"]), "取引先名": r["取引先名"], "推論値_億": v,
                    "該当箇所": seg.strip(), "判定": r["最終判定"]}); break
dump("inferred_number_risk.json", sorted(inf, key=lambda x: x["推論値_億"]))

# 3) 組織再編（売上が移管先に付いている可能性）
REORG = re.compile(r"(会社分割|事業(?:を)?承継|吸収分割|新設分割|事業譲渡|分社化|分社型)")
dump("reorganization_rows.json",
     [{"行": int(r["行"]), "取引先名": r["取引先名"], "判定": r["最終判定"]}
      for r in rows if REORG.search(r["I列_検証結果"] or "")])

# 4) §7-1 の回答を待たずに除外できる行
cat = [r for r in rows if not r["最終判定"].startswith("架電可")
       and ("catr.jp" in (r["I列_検証結果"] or "") + (r["J列_ソース"] or "") or "§7-1" in (r["I列_検証結果"] or ""))]
dump("exclude_regardless_of_catr.json",
     [{"行": int(r["行"]), "取引先名": r["取引先名"], "最大額_億": maxoku(r["I列_検証結果"])}
      for r in cat if (maxoku(r["I列_検証結果"]) or 1e9) < 300])

# 5) 決算公告が貸借対照表のみ＝売上高が構造的に無い行
BS = re.compile(r"(貸借対照表のみ|損益計算書(?:の公告)?(?:が)?(?:ない|なし|非掲載|未掲載)|BSのみ|P/?Lなし|損益(?:の)?記載なし)")
dump("koukoku_bs_only.json",
     [{"行": int(r["行"]), "取引先名": r["取引先名"]} for r in rows if BS.search(r["I列_検証結果"] or "")])

# 6) 出典のgBizINFO法人番号がB列と不一致（大半は §3-3 の親子確定で正常）
mis = []
for r in rows:
    blob = (r["J列_ソース"] or "") + " " + (r["I列_検証結果"] or "")
    nums = set(re.findall(r"hojinBango=(\d{13})", blob))
    own = (r["法人番号"] or "").strip()
    if nums and own and own not in nums:
        mis.append({"行": int(r["行"]), "取引先名": r["取引先名"], "B列法人番号": own,
                    "出典の法人番号": sorted(nums), "判定": r["最終判定"]})
dump("gbiz_hojinbango_mismatch.json", mis)

# 7) 出典の強さ
def tier(r):
    b = (r["I列_検証結果"] or "") + " " + (r["J列_ソース"] or "")
    if re.search(r"有価証券報告書|EDINET|決算短信|TDnet|適時開示", b): return "A 有報・決算短信・適時開示"
    if re.search(r"決算公告|電子公告", b) and "catr.jp" not in b:      return "B 自社HPの決算公告"
    if re.search(r"会社概要|企業情報|会社案内|IR|業績ハイライト|統合報告書", b): return "C 自社HP（会社概要・IR）"
    if re.search(r"関係会社の状況|主要な損益情報", b):                  return "D 親会社IR巻末"
    if re.search(r"新聞|業界紙|専門紙", b):                            return "E 新聞社記事"
    if re.search(r"gBizINFO|経済産業省|金融庁|公的", b):                return "F 公的機関"
    if re.search(r"採用|数字で見る|新卒", b):                          return "G 自社採用ページ"
    if "catr.jp" in b:                                                 return "H catr.jp のみ（§7-1依存）"
    return "I その他・特定できず"
c = collections.Counter(tier(r) for r in ok)
json.dump({k: c[k] for k in sorted(c)}, open(R + "source_strength.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("  %-38s 架電可%d行を分類" % ("source_strength.json", len(ok)))
