# -*- coding: utf-8 -*-
"""§3-6 の決定的ガード。架電可と判定された行のうち、社名が株式会社でないものを落とす。
法人番号の種別コードは組織変更で引き継がれるため判定に使わない（全4,422行で実測）。
このチェックは検索を一切必要とせず、エージェントの判断より優先する。"""
import csv, json, re, sys, collections

NG_FORMS = ["合同会社", "有限会社", "合資会社", "合名会社", "特例有限会社",
            "一般社団法人", "一般財団法人", "公益社団法人", "公益財団法人",
            "協同組合", "組合連合会", "協会", "農業協同組合", "生活協同組合",
            "社会福祉法人", "医療法人", "学校法人", "独立行政法人", "国立大学法人",
            "特定非営利活動法人", "相互会社", "企業組合", "事業協同組合"]

def form_ng(name):
    n = (name or "").replace("　", "").strip()
    if "株式会社" in n:
        # 「株式会社」を含んでいても、他の法人格語が主体なら NG（例: 合同会社◯◯株式会社 は無い想定）
        return None
    for f in NG_FORMS:
        if f in n:
            return f
    # 外国法人・カタカナ末尾の法人格なし
    if re.search(r"(リミテッド|インコーポレーテッド|コーポレーション|Ltd|Inc|LLC|GmbH|S\.A\.)$", n, re.I):
        return "法人格表記なし（外国会社）"
    return "法人格語なし"

def main():
    rows = list(csv.DictReader(open("tokium/results/IJ_paste.csv", encoding="utf-8-sig")))
    bad = []
    for r in rows:
        if not r["最終判定"].startswith("架電可"):
            continue
        ng = form_ng(r["取引先名"])
        if ng:
            bad.append((r["行"], r["取引先名"], r["最終判定"], ng))
    print("架電可のうち §3-6 で落ちる行: %d" % len(bad))
    c = collections.Counter(x[3] for x in bad)
    for k, v in c.most_common():
        print("   %-24s %d" % (k, v))
    for x in bad:
        print("  行%-5s %-34s %-12s → %s" % (x[0], x[1][:34], x[2], x[3]))
    json.dump([{"行": int(x[0]), "取引先名": x[1], "判定": x[2], "NG理由": x[3]} for x in bad],
              open("tokium/results/legal_form_violations.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
