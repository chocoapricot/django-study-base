# 接続プロセスにおける権限（パーミッション）付与のタイミング

Djangoアプリケーション内での調査結果に基づき、クライアントおよびスタッフの接続プロセスにおける権限付与のタイミングと内容をまとめました。
現状の実装では、Djangoの「グループ（Group）」機能を使用して権限管理が行われています。

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
    *   `client` グループには以下の権限が含まれています：
        *   `connect.view_connectclient` (接続申請の閲覧)
        *   `connect.change_connectclient` (接続申請の変更)

### 1.2 接続承認時（Connection Approval）
クライアントユーザー本人がシステムにログインし、接続申請を「承認」したタイミングです。

*   **トリガー**:
    *   `connect_client_approve` ビューの実行
*   **実行される関数**:
    *   `grant_client_connected_permissions(user)`
*   **付与される権限**:
    *   ユーザーは **`client_connected` グループ** に追加されます。
    *   `client_connected` グループには以下の権限が含まれています：
        *   `contract.confirm_clientcontract` (クライアント契約の確認権限)

### 1.3 接続申請取り消し時
接続申請が削除された際、**そのユーザーに対する接続申請がすべてなくなった場合**、ユーザーは **`client` および `client_connected` グループから削除** されます。

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
    *   ユーザーは **`staff` グループ** に追加されます。
    *   `staff` グループには以下の権限が含まれています：
        *   `connect.view_connectstaff` (接続申請の閲覧)
        *   `connect.change_connectstaff` (接続申請の変更)

### 2.2 接続承認時（Connection Approval）
スタッフ本人がシステムにログインし、接続申請を「承認」したタイミングです（管理者による代理承認も可能）。

*   **トリガー**:
    *   `connect_staff_approve` ビューの実行
*   **実行される関数**:
    *   `grant_staff_connected_permissions(user)`
*   **付与される権限**:
    *   ユーザーは **`staff_connected` グループ** に追加されます。
    *   `staff_connected` グループには以下の権限が含まれています：
        *   `contract.confirm_staffcontract` (スタッフ契約の確認権限)
        *   `contract.view_staffcontract` (スタッフ契約の閲覧)
        *   `profile.*` (プロフィール関連の各種権限)
        *   `kintai.*` (勤怠関連の各種権限)

---

## 3. その他の補足事項

### 3.1 初期セットアップ時
初期化時に `_sample_data\users.csv` からユーザーを読み込む際は、即座にシステムを利用できるように以下のグループが付与されます。
*   スタッフ： **`staff` および `staff_connected` 両グループ**
*   クライアント： **`client` および `client_connected` 両グループ**

### 3.2 ユーザー登録時の自動付与
`apps/accounts/signals.py` にて `User` モデルの `post_save` シグナルを監視しており、ユーザーが新規作成された瞬間に、そのメールアドレス宛の接続申請（`ConnectStaff` または `ConnectClient`）が存在するか確認します。
*   スタッフの場合：あてはまるメールアドレスの接続申請があれば、`staff` グループを付与します。さらに、その申請が既に「承認済み」であれば `staff_connected` グループも付与します。
*   クライアントの場合：あてはまるメールアドレスの接続申請があれば、`client` グループを付与します。さらに、その申請が既に「承認済み」であれば `client_connected` グループも付与します。

### 3.3 権限の剥奪（削除）について
*   **承認取り消し (`unapprove`)**:
    *   `connect_staff_unapprove` や `connect_client_unapprove` ビューでは、ステータスを未承認に戻す処理が行われますが、**グループからの脱退処理は現状行われません。**
    *   これは、一度システムを利用したユーザーが、再接続の際にスムーズに操作を継続できるようにするため、また複数の会社と接続している可能性があるためです。
