# 接続プロセスにおける権限（パーミッション）付与のタイミング

Djangoアプリケーション内での調査結果に基づき、クライアントおよびスタッフの接続プロセスにおける権限付与のタイミングと内容をまとめました。
現状の実装では、Djangoの「グループ（Group）」機能は使用されておらず、`user.user_permissions` に対して直接「パーミッション（Permission）」が付与されています。

## 1. クライアントユーザーの接続フロー

### 1.1 接続申請時（Connection Request Creation）
管理者がシステムからクライアントユーザーに対して接続申請（`ConnectClient`）を作成したタイミング、または接続申請が存在する状態でユーザーが新規登録されたタイミングです。

*   **トリガー**:
    *   管理者による接続申請作成 (`client_user_detail` ビューでのトグル操作など)
    *   ユーザー新規登録時のシグナル (`apps.accounts.signals.check_connection_requests_on_user_creation`)
*   **実行される関数**:
    *   `grant_client_permissions_on_connection_request(email)`
    *   `check_and_grant_client_permissions_for_email(email)`
*   **付与される権限**:
    *   ユーザーは **`client` グループ** に追加されます。
    *   `client` グループには以下の権限が含まれていることが前提となります：
        *   `connect.view_connectclient` (接続申請の閲覧)
        *   `connect.change_connectclient` (接続申請の変更)
        *   `contract.confirm_clientcontract` (クライアント契約の確認権限)

### 1.2 接続承認時（Connection Approval）
クライアントユーザー本人がシステムにログインし、接続申請を「承認」したタイミングです。
**このタイミングでの新たな権限付与は行われません**（申請時点で `client` グループに追加済みのため）。

*   **トリガー**:
    *   `connect_client_approve` ビューの実行
*   **実行される関数**:
    *   なし（ステータス更新のみ）

### 1.3 接続申請取り消し時
接続申請が削除された際、**そのユーザーに対する接続申請がすべてなくなった場合**、ユーザーは **`client` グループから削除** されます。

*   **トリガー**:
    *   管理者による接続申請取り消し (`client_user_detail` ビューなど)
*   **実行される関数**:
    *   `remove_user_from_client_group_if_no_requests(email)`


---

## 2. スタッフの接続フロー

### 2.1 接続申請時（Connection Request Creation）
管理者がシステムからスタッフに対して接続申請（`ConnectStaff`）を作成したタイミング、または接続申請が存在する状態でユーザーが新規登録されたタイミングです。

*   **トリガー**:
    *   管理者による接続申請作成 (`staff_detail` ビューでのトグル操作など)
    *   ユーザー新規登録時のシグナル (`apps.accounts.signals.check_connection_requests_on_user_creation`)
*   **実行される関数**:
    *   `grant_permissions_on_connection_request(email)`
    *   `check_and_grant_permissions_for_email(email)`
*   **付与される権限**:
    *   `connect.view_connectstaff` (接続申請の閲覧)
    *   `connect.change_connectstaff` (接続申請の変更)

### 2.2 接続承認時（Connection Approval）
スタッフ本人がシステムにログインし、接続申請を「承認」したタイミングです（管理者による代理承認も可能）。
スタッフの場合、承認時に多くのプロフィール関連権限が付与されます。

*   **トリガー**:
    *   `connect_staff_approve` ビューの実行
*   **実行される関数**:
    *   `grant_permissions_on_connection_request(email)` (念のための再付与)
    *   `grant_profile_permissions(user)`
    *   `grant_staff_contract_confirmation_permission(user)`
*   **付与される権限**:
    *   **接続関連**:
        *   `connect.view_connectstaff`
        *   `connect.change_connectstaff`
    *   **契約関連**:
        *   `contract.confirm_staffcontract` (スタッフ契約の確認権限)
    *   **プロフィール関連（以下のモデルに対する全権限: view, add, change, delete）**:
        *   `profile.staffprofile` (基本プロフィール)
        *   `profile.staffprofilemynumber` (マイナンバー)
        *   `profile.staffprofilebank` (銀行口座)
        *   `profile.staffprofilecontact` (連絡先)
        *   `profile.staffprofileinternational` (外国籍情報)
        *   `profile.staffprofiledisability` (障害者情報)

---

## 3. その他の補足事項

### 3.1 ユーザー登録時の自動付与
`apps/accounts/signals.py` にて `User` モデルの `post_save` シグナルを監視しており、ユーザーが新規作成された瞬間に、そのメールアドレス宛の未承認・承認済みの接続申請（`ConnectStaff` または `ConnectClient`）が存在するか確認します。存在する場合、即座に上述の「接続申請時」の権限が付与されます。

### 3.2 グループ（Group）の利用について
現時点のコードベース（`apps/connect`, `apps/accounts`, `apps/staff`, `apps/client` 周辺）では、Django標準の `Group` モデルを使用した権限管理は行われていません。権限はすべて `user.user_permissions.add()` によって個別のユーザーに直接紐付けられています。

### 3.3 権限の剥奪（削除）について
*   **承認取り消し (`unapprove`)**:
    *   `connect_staff_unapprove` や `connect_client_unapprove` ビューでは、ステータスを未承認に戻す処理のみが行われており、**一度付与された権限（プロフィール編集権限や契約確認権限など）を削除する処理（`remove()`）は実装コード上には見当たりません。**
    *   したがって、一度承認して権限を得たユーザーは、その後承認を取り消されても、権限自体は保持し続ける可能性があります（要確認: 実装漏れか仕様か）。
