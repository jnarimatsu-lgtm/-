# -*- coding: utf-8 -*-
"""G/H列の機械監査（Web不要）。ルール文書 §3/§4/§6/§8 に対する形式・整合チェック。"""
import re, sys, json, csv

NG_KAKU = ["合同会社","有限会社","信用金庫","信用組合","医療法人","社会福祉法人",
           "農業協同組合","生活協同組合","相互会社","一般社団法人","財団法人",
           "独立行政法人","合資会社","合名会社","労働金庫","共済組合"]
BANNED = ["shukatsu-kaigi.jp","syukatsu-kaigi","baseconnect","salesnow","mynavi","rikunabi",
          "doda.jp","openwork","jobtalk","en-hyouban","lighthouse","wantedly","wikipedia",
          "yahoo.co.jp/shigoto","job-", "tenshoku", "nikkei-compass","newspicks"]
MARKS = ("○","×","△")

def parse_oku(g):
    """G列から億円単位の数値を取り出す。§6-1の複合単位・兆表記に対応。"""
    if not g: return None
    s = g.replace("\\","").replace(",","").replace(" ","").replace("\u3000","")
    s = s.replace("\u200b","")  # ゼロ幅スペース
    # X兆Y億円 / X兆円
    m = re.search(r"(\d+(?:\.\d+)?)\u5146(?:(\d+(?:\.\d+)?)\u5104)?\u5186", s)
    if m:
        v = float(m.group(1))*10000
        if m.group(2): v += float(m.group(2))
        return v
    # X億Y千万円
    m = re.search(r"(\d+(?:\.\d+)?)\u5104(\d+)\u5343\u4e07\u5186", s)
    if m: return float(m.group(1)) + float(m.group(2))/10
    m = re.search(r"(\d+(?:\.\d+)?)\u5104\u5186", s)
    if m: return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\u767e\u4e07\u5186", s)
    if m: return float(m.group(1))/100
    return None

def fiscal_year(g):
    m = re.search(r"(\d{4})年\d{1,2}月期", g or "")
    return int(m.group(1)) if m else None

def audit(rows, first_row_no=2):
    out=[]
    for i,r in enumerate(rows):
        n = first_row_no + i
        r = (r + [""]*8)[:8]
        acc_id,houjin,name,web,rng,memo,G,H = [ (c or "").replace("\\","").strip() for c in r ]
        f=[]
        mark = H[:1] if H else ""
        amt = parse_oku(G)
        has_under = "【300億未満】" in G
        urls = re.findall(r"https?://[^\s、。）)]+", H)

        # 1. 判定記号
        if not H:
            f.append("H列が空")
        elif mark not in MARKS:
            f.append(f"H列先頭に判定記号なし(先頭='{H[:6]}')")

        # 2. 【300億未満】の付け忘れ  ← doc §8 の明示的宿題
        if amt is not None and amt < 300 and not has_under and "対象外" not in G:
            f.append(f"G列{amt}億円<300なのに【300億未満】なし")
        # 3. 逆パターン
        if amt is not None and amt >= 300 and has_under:
            f.append(f"G列{amt}億円>=300なのに【300億未満】あり")

        # 4. G/H整合
        if mark=="○" and (has_under or "対象外" in G or "確認不可" in G):
            f.append("H列○なのにG列がNG内容")
        if mark=="○" and amt is not None and amt < 300:
            f.append(f"H列○なのにG列{amt}億円<300")
        if mark=="△" and "確認不可" not in G:
            f.append("H列△なのにG列が確認不可でない")
        if mark=="×" and amt is not None and amt>=300 and "子会社" not in H and "法人格" not in H:
            f.append(f"H列×だがG列{amt}億円>=300で理由不明")

        # 5. 法人格
        hit=[k for k in NG_KAKU if k in name]
        if hit and mark!="×":
            f.append(f"社名に{hit[0]}を含むがH列が×でない")
        if hit and "法人格" not in H and mark=="×":
            pass

        # 6. ○なのに出典URLなし
        if mark=="○" and not urls:
            f.append("H列○だが参照URLなし")

        # 7. 300字上限
        if len(H) > 300:
            f.append(f"H列{len(H)}字（上限300字超過）")

        # 8. 禁止ソース
        for u in urls:
            lu=u.lower()
            for b in BANNED:
                if b in lu:
                    f.append(f"禁止ソースURL: {b}")
                    break

        # 9. catr.jp（§7-1 先方未確認）
        if any("catr.jp" in u.lower() for u in urls):
            f.append("catr.jp使用（§7-1 承認可否が先方未確認）")

        # 10. 法人番号
        if not re.fullmatch(r"\d{13}", houjin or ""):
            f.append(f"法人番号が13桁でない('{houjin}')")

        # 11. 決算期の鮮度（直近3期＝2023年以降）
        fy = fiscal_year(G)
        if fy is not None and fy < 2023:
            f.append(f"決算期{fy}年（直近3期外）")

        if f:
            out.append({"行":n,"取引先名":name,"G列":G,"H列":H[:120],"指摘":f})
    return out

if __name__=="__main__":
    src=sys.argv[1]
    rows=[]
    for ln in open(src,encoding="utf-8"):
        if not ln.startswith("|"): continue
        cells=[c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells)!=8: continue
        rows.append(cells)
    rows=rows[3:]  # ヘッダ3行を除去
    res=audit(rows)
    print(f"検査対象: {len(rows)}行 / 指摘のある行: {len(res)}行")
    from collections import Counter
    c=Counter()
    for r in res:
        for x in r["指摘"]:
            c[re.sub(r"[\d.]+億円|\('.*?'\)|\(先頭=.*?\)|: .*|\d+字","…",x)] += 1
    print("\n--- 指摘の種類別件数 ---")
    for k,v in c.most_common(): print(f"{v:5d}  {k}")
    json.dump(res, open(src+".audit.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
