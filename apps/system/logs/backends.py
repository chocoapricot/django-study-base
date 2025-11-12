from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.utils import timezone
from apps.common.constants import Constants
from .utils import log_mail, update_mail_log_status
import logging
import uuid

logger = logging.getLogger(__name__)

class LoggingEmailBackend:
    """メール送信ログ機能付きのベースバックエンド"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mail_logs = {}  # メールログのマッピング
    
    def send_messages(self, email_messages):
        """メッセージを送信し、ログを記録"""
        if not email_messages:
            return 0
        
        sent_count = 0
        
        for message in email_messages:
            try:
                # メール種別を推定
                mail_type = self._determine_mail_type(message.subject, message.body)
                
                # メッセージIDを生成
                message_id = str(uuid.uuid4())
                
                # 受信者ごとにログを作成
                for to_email in message.to:
                    mail_log = log_mail(
                        to_email=to_email,
                        subject=message.subject,
                        body=message.body,
                        mail_type=mail_type,
                        from_email=message.from_email,
                        status=Constants.MAIL_STATUS.PENDING,
                        backend=self.__class__.__name__,
                        message_id=message_id
                    )
                    self.mail_logs[id(message)] = mail_log
                
                # 実際のメール送信
                if self._send_message(message):
                    # 送信成功
                    if id(message) in self.mail_logs:
                        update_mail_log_status(
                            self.mail_logs[id(message)].id, 
                            Constants.MAIL_STATUS.SENT
                        )
                    sent_count += 1
                else:
                    # 送信失敗
                    if id(message) in self.mail_logs:
                        update_mail_log_status(
                            self.mail_logs[id(message)].id, 
                            Constants.MAIL_STATUS.FAILED,
                            error_message='メール送信に失敗しました'
                        )
                        
            except Exception as e:
                logger.error(f"メール送信エラー: {e}")
                # エラー時のログ更新
                if id(message) in self.mail_logs:
                    update_mail_log_status(
                        self.mail_logs[id(message)].id, 
                        Constants.MAIL_STATUS.FAILED,
                        error_message=str(e)
                    )
        
        return sent_count
    
    def _send_message(self, message):
        """実際のメール送信処理（サブクラスで実装）"""
        raise NotImplementedError("サブクラスで実装してください")
    
    def _determine_mail_type(self, subject, body):
        """件名と本文からメール種別を推定"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        if 'パスワードリセット' in subject or 'password reset' in subject_lower:
            return Constants.MAIL_TYPE.PASSWORD_RESET
        elif 'サインアップ' in subject or 'signup' in subject_lower or '確認' in subject:
            return Constants.MAIL_TYPE.SIGNUP
        elif 'パスワード変更' in subject or 'password change' in subject_lower:
            return Constants.MAIL_TYPE.PASSWORD_CHANGE
        else:
            return Constants.MAIL_TYPE.GENERAL

class LoggingConsoleEmailBackend(LoggingEmailBackend, ConsoleEmailBackend):
    """ログ機能付きコンソールメールバックエンド"""
    
    def _send_message(self, message):
        """コンソールにメッセージを出力"""
        try:
            # 親クラスのwrite_messageメソッドを使用
            self.write_message(message)
            return True
        except Exception as e:
            logger.error(f"コンソール出力エラー: {e}")
            return False

class LoggingSMTPEmailBackend(LoggingEmailBackend, SMTPEmailBackend):
    """ログ機能付きSMTPメールバックエンド"""
    
    def _send_message(self, message):
        """SMTPでメッセージを送信"""
        try:
            # 親クラスのsend_messagesメソッドを使用
            return super(SMTPEmailBackend, self).send_messages([message]) > 0
        except Exception as e:
            logger.error(f"SMTP送信エラー: {e}")
            return False