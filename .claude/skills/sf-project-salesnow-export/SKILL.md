---
name: sf-project-salesnow-export
description: |
  Salesforce の取引先（Account）を「プロジェクト名」で絞り込み、取引先ID・取引先名と
  SalesNow 項目（qw_snpf__sn_* の 54 項目）を Google スプレッドシートに出力する。
  Coupler.io MCP 経由で SOQL を投げてデータフローを作る。
  MANDATORY TRIGGERS: プロジェクト名 取引先 出して, SalesNow 項目 出力, 取引先 スプシ 落とす,
  Acct_projectname__c, プロジェクト別 リスト 抽出, SF 取引先 エクスポート, 案件別 取引先リスト,
  イクシアス 取引先, Taan 取引先 リスト, SalesNow エクスポート
---

# SF取引先 × SalesNow プロジェクト別エクスポート

プロジェクト名を1つ（または複数）受け取り、その取引先を SalesNow 項目つきで
Google スプレッドシートへ出力する。

## デフォルトで出す項目

指定がなければ **57列**を出す。

| 種別 | 項目 |
|---|---|
| 取引先ID | `Id` |
| 取引先名 | `Name` |
| プロジェクト名 | `Acct_projectname__c` |
| SalesNow | `references/salesnow_fields.txt` の54項目すべて |

ユーザーが「この項目だけ」と言った場合のみ絞る。`Id` は常に含める
（Data Loader で書き戻すときの結合キーになるため、外してはいけない）。

## 手順

### 1. プロジェクト名を確定する

表記ゆれと文字化けがあるので、**必ず実在する値を確認してから** WHERE に入れる。
確認用 SOQL:

```sql
SELECT Acct_projectname__c, COUNT(Id) cnt FROM Account
GROUP BY Acct_projectname__c ORDER BY COUNT(Id) DESC
```

ユーザーが言った名前と完全一致しない候補（前方一致・文字化け・サフィックス違い）が
あれば、**勝手に決めずに提示して確認する**。例:

- `サイバーエース` / `サイバーエース_BDR` / `サイバーエースBDR` / `サイバーエース_BDR_返却` は別々の値
- `ã¤ã¯ã·ã¢ã¹` は `イクシアス` の文字化けが Salesforce 側に保存されたもの（131件）
- `ãµã¤ãã¼ã¨ã¼ã¹_ChatGPT` は `サイバーエース_ChatGPT` の文字化け（1件）
- プロジェクト名が空欄の取引先が 434 件ある

文字化け側を含めるかどうかは毎回確認する。含めるなら `IN ('イクシアス','ã¤ã¯ã·ã¢ã¹')` のように両方書く。

### 2. 行数を見積もる

`件数 × 57列` が **1,000万セル**（Googleスプレッドシート1ファイルの上限）を超えないか確認する。
57列なら約17.5万件が上限。超えるなら項目を絞るか、プロジェクトを分割する。

全79プロジェクト・約79.5万件を1ファイルに入れることは**できない**。
「全部出して」と言われたらこの制約を伝えてプロジェクトを選んでもらう。

### 3. Coupler.io でデータフローを作る

```
create-dataflow            name: "SF取引先 × SalesNow｜プロジェクト: <名前>"
create-dataflow-source     integration_key: salesforce
                           credential_id: <list-credentials で取得。依頼者本人のものを使う>
                           params: { dataType: {value:"soql", label:"Custom SOQL"},
                                     customSOQL: "<下記>" }
create-dataflow-destination integration_key: google_spreadsheet
                           credential_id: <destination の google_spreadsheet 認証>
                           params: { sheet_name: "<プロジェクト名>", insert_at: "A1" }
get-dataflow               → available_views の key を取得
update-dataflow-destination transformation_set_key: <その key>   ※全 destination に必要
run-dataflow               run_mode: "full"
```

SOQL:

```sql
SELECT Id, Name, Acct_projectname__c, <SalesNow 54項目>
FROM Account
WHERE Acct_projectname__c IN ('<プロジェクト名>')
```

### 4. ユーザーに出力先スプレッドシートを選んでもらう

**ここは自動化できない。** Coupler.io の Google Sheets 出力は、対象スプレッドシートを
ウィザードのファイルピッカーで手動選択する必要がある（MCP にスプレッドシートIDのパラメータが無い）。

データフロー編集URL（`https://app.coupler.io/app/dataflows/<id>/edit`）を渡して、
出力先ファイルを選んでもらってから実行してもらう。
**「スプシに出しました」と先に言わないこと。**

## 検証

`claude` destination も同じ view に紐づけておくと、`get-data` で中身をSQL検証できる。
最低限これは確認する:

```sql
SELECT COUNT(*) rows, COUNT(DISTINCT "Id") ids,
       COUNT("qw_snpf__sn_corporate_number__c") sn_filled FROM data
```

- `rows` が手順1の件数と一致するか
- `ids` が `rows` と一致するか（重複していないか）
- SalesNow の充足率（全体では81%程度。極端に低ければ WHERE か項目名を疑う）

## 注意点

- **参照専用。** Coupler.io から Salesforce へ書き戻すことはできない。更新は
  従来どおり Data Loader 用 CSV を作る（`tokium/build_sf_update.py` 参照）。
- **スナップショット。** 実行時点のコピーであってライブ接続ではない。
- **取得範囲は実行者の権限まで。** 認証情報の持ち主が見られない項目は取れない。
- SalesNow 項目名は `references/salesnow_fields.txt` に置いてあるが、
  パッケージ更新で増減しうる。件数が合わない時は
  `SELECT FIELDS(ALL) FROM Account LIMIT 5` を流して現物のスキーマを取り直す。
