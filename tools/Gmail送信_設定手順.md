# Gmail 自動送信の設定手順（最初の1回だけ）

zip をチャットにアップロードすると、Claude が PDF だけを取り出して `tutomu.koyama@shimz.co.jp` に送るための設定です。
送信元は `tutomu.koyama.1026@gmail.com`。許可するのは **メールの送信だけ**（受信箱は読めない）です。

PC のブラウザで作業してください（15〜20分）。画面の文言は英語表示のことがあります。

## 1. Google Cloud でプロジェクトを作る
1. https://console.cloud.google.com/ を開き、`tutomu.koyama.1026@gmail.com` でログイン（初回は利用規約に同意）。
2. 画面上部のプロジェクト選択 →「新しいプロジェクト」→ 名前は `pdf-mail` など → 作成。作ったプロジェクトが選ばれていることを確認。

## 2. Gmail API を有効にする
1. 左上メニュー →「API とサービス」→「ライブラリ」。
2. `Gmail API` を検索 →「有効にする」。

## 3. 同意画面（Google Auth Platform）を設定する
1. 左上メニュー →「API とサービス」→「OAuth 同意画面」（または「Google Auth Platform」）→「開始」。
2. アプリ名：`pdf-mail`、ユーザーサポートメール：自分のアドレス → 対象：**外部** → 連絡先：自分のアドレス → 同意して作成。
3. 「対象（Audience）」→「テストユーザー」に `tutomu.koyama.1026@gmail.com` を追加。
4. 同じ画面の「公開ステータス」で **「アプリを公開」→ 本番環境** にする。
   - テスト中のままだと、7日でトークンが切れて送れなくなります。
   - 自分しか使わないので Google の審査は不要です（ログイン時に「確認されていないアプリ」と出るだけ）。

## 4. 認証情報（OAuth クライアント）を作る
1. 「クライアント」（または「認証情報」→「認証情報を作成」→「OAuth クライアント ID」）。
2. アプリケーションの種類：**ウェブ アプリケーション**、名前は任意。
3. 「承認済みのリダイレクト URI」に次を追加：`https://developers.google.com/oauthplayground`
4. 作成 → 表示される **クライアント ID** と **クライアント シークレット** を控える（あとで手順6で使う。チャットには貼らない）。

## 5. リフレッシュトークンを取る（OAuth Playground）
1. https://developers.google.com/oauthplayground を開く。
2. 右上の歯車 →「Use your own OAuth credentials」にチェック → 手順4のクライアント ID とシークレットを入力。
3. 左の Step 1 の入力欄に次を入れて「Authorize APIs」：
   `https://www.googleapis.com/auth/gmail.send`
4. `tutomu.koyama.1026@gmail.com` を選ぶ →「このアプリは Google で確認されていません」→「詳細」→「pdf-mail（安全ではないページ）に移動」→「続行」。
5. Step 2 で「Exchange authorization code for tokens」→ 表示される **Refresh token** を控える。

## 6. Claude の環境に登録する
1. Claude（claude.ai/code またはアプリ）のセッション画面上部の **環境メニュー → Edit**。
2. 環境変数に次の3行を追加して保存（`=` の右に手順4・5の値。前後に空白や引用符を入れない）：
   ```
   GMAIL_CLIENT_ID=（クライアント ID）
   GMAIL_CLIENT_SECRET=（クライアント シークレット）
   GMAIL_REFRESH_TOKEN=（リフレッシュトークン）
   ```
3. **新しいセッション**を始める（今のセッションには反映されません）。zip をアップロードすれば送信されます。

## うまくいかないとき
- `invalid_grant`：トークンが切れた・取り消された。手順3-4（本番環境）を確認し、手順5からやり直して `GMAIL_REFRESH_TOKEN` を更新。
- 止めたいとき：https://myaccount.google.com/permissions で `pdf-mail` のアクセスを削除すれば、すぐに送れなくなります。
