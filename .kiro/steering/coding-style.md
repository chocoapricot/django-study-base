# コーディングスタイル

## HTML/テンプレート編集方針
- **改行制限**: 200文字程度まで改行しない
- **コメント保持**: 既存のコメントを勝手に削除しない
- **フォーマット保持**: 元のファイルの改行構造を保持する
- **最小限修正**: 必要最小限の修正のみを行う

## ファイル編集の基本原則
1. 元のフォーマットを尊重する
2. 不要な改行や空白の変更を避ける
3. コメントや説明文を保持する
4. 機能的な修正のみに集中する

## テンプレートファイル（HTML）
- 長い属性リストでも200文字以内なら1行で記述
- 既存のインデントレベルを維持
- コメント（<!-- -->）を保持
- 不要な空行を追加しない

## Bootstrapボタンのスタイル統一
- **必須ルール**: すべてのボタンに `btn-sm` クラスを追加する
- **例**: `class="btn btn-sm btn-primary"`, `class="btn btn-sm btn-secondary"`
- **対象**: フォームボタン、リンクボタン、操作ボタンすべて
- **例外**: 特別な理由がある場合のみ例外を認める

## 戻るボタンの配置ルール
- **基本原則**: 戻るボタンはコンテンツ内の左下に配置する
- **禁止**: カードフッター（card-footer）での戻るボタン配置は禁止
- **card-footer使用可能**: 「全て表示」などの補助リンクは card-footer 使用可
- **推奨レイアウト**: 
  ```html
  <div class="row mt-3">
      <div class="col text-left">
          <a href="..." class="btn btn-sm btn-secondary">戻る</a>
      </div>
  </div>
  ```
- **参考**: クライアント変更履歴一覧のレイアウトに準拠

## フォームデザインの統一ルール
- **ラベル配置**: `col-form-label` + `text-align:right` で右寄せ
- **ラベルスタイル**: 太字（`<strong>`）は使用しない、通常の文字重量
- **入力欄サイズ**: すべての入力欄に `form-control-sm` クラスを追加
- **ボタン分離**: API呼び出しボタンは入力欄と分離して独立したカラムに配置
- **推奨レイアウト**:
  ```html
  <div class="row mb-3 align-items-center">
      <label for="..." class="col-sm-2 col-form-label" style="text-align:right">ラベル</label>
      <div class="col-sm-4">
          <input class="form-control form-control-sm" ...>
      </div>
      <div class="col-sm">
          <button type="button" class="btn btn-sm btn-secondary">ボタン</button>
      </div>
  </div>
  ```
- **参考**: クライアントフォームのレイアウトに準拠

## Tooltipの統一ルール
- **アイコン**: Bootstrap Icons の `bi-question-circle` を使用
- **スタイル**: `style="color: #66bbff; cursor: pointer;"`
- **属性**: `data-bs-toggle="tooltip" data-bs-placement="top"`
- **配置**: ラベルの直後、またはボタンの直後に配置
- **推奨実装**:
  ```html
  <label>ラベル名
      <i class="bi bi-question-circle" style="color: #66bbff; cursor: pointer;" 
         data-bs-toggle="tooltip" data-bs-placement="top" title="説明文"></i>
  </label>
  ```
- **共通メッセージ**:
  - 法人番号: "半角数字13桁ハイフンなし"
  - 郵便番号: "半角数字7桁ハイフンなし"
  - 法人情報取得: "経産省のgBizINFO-APIで取得"
  - 住所検索: "フリーの郵便番号APIで取得"

## 削除ボタンの統一ルール
- **すべての削除ボタン**: `btn-dark` を使用して統一
- **対象**:
  - 詳細画面の削除ボタン
  - 一覧画面のアイコン削除ボタン
  - 削除確認画面の実行ボタン
- **理由**: 
  - プロジェクト全体での視覚的統一性を重視
  - `btn-danger` は緊急性の高いエラーやアラート用に予約
- **推奨実装**:
  ```html
  <!-- 詳細画面 -->
  <a href="..." class="btn btn-sm btn-dark">削除</a>
  
  <!-- 削除確認画面 -->
  <button type="submit" class="btn btn-sm btn-dark">削除する</button>
  
  <!-- 一覧画面のアイコン -->
  <a href="..." class="btn btn-dark btn-sm" title="削除">
      <i class="bi bi-x"></i>
  </a>
  ```

## フォームウィジェットの統一ルール
- **必須クラス**: すべてのフォーム入力欄に `form-control form-control-sm` を適用
- **テキスト入力**: `forms.TextInput(attrs={'class': 'form-control form-control-sm'})`
- **テキストエリア**: `forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3})`
- **URL入力**: `forms.URLInput(attrs={'class': 'form-control form-control-sm'})`
- **選択欄**: `forms.Select(attrs={'class': 'form-control form-control-sm'})`

## カラム幅の推奨設定
- **ラベル**: `col-sm-2` (固定)
- **短い入力欄**: `col-sm-3` (郵便番号など)
- **中程度入力欄**: `col-sm-4` (法人番号など)
- **標準入力欄**: `col-sm-6` (名前など)
- **長い入力欄**: `col-sm-8` (URL、メモなど)
- **最大幅入力欄**: `col-sm-10` (住所など)
- **ボタン用**: `col-sm` (残り幅を自動調整)

## Pythonファイル
- PEP 8に準拠
- 日本語コメントを積極的に使用
- docstringは日本語で記述
- 変数名・関数名は英語

## JavaScriptファイル
- 既存のスタイルに合わせる
- コメントは日本語で記述
- 不要な改行を避ける

## CSSファイル
- 既存のフォーマットを維持
- コメントを保持
- プロパティの順序を変更しない