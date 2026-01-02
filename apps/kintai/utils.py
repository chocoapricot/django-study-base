from datetime import datetime, timedelta
from apps.common.constants import Constants
import math


def round_time(dt, unit_minutes, method):
    """
    時刻を指定された単位と方法で丸める
    
    Args:
        dt (datetime): 丸める対象の時刻
        unit_minutes (int): 丸め単位（分）
        method (str): 丸め方法 ('round', 'floor', 'ceil')
    
    Returns:
        datetime: 丸められた時刻
    """
    if not dt:
        return dt

    # 1分単位、または未設定の場合は秒を切り捨てる
    if unit_minutes <= 1:
        return dt.replace(second=0, microsecond=0)
    
    # 分単位での現在の分数を取得
    current_minutes = dt.minute
    current_seconds = dt.second
    current_microseconds = dt.microsecond
    
    # 秒・マイクロ秒を分に換算（より正確な計算のため）
    total_minutes_decimal = current_minutes + (current_seconds / 60.0) + (current_microseconds / 60000000.0)
    
    # 丸め処理
    if method == Constants.TIME_ROUNDING_METHOD.ROUND:
        # 四捨五入（0.5の場合は切り上げ）
        quotient = total_minutes_decimal / unit_minutes
        rounded_minutes = math.floor(quotient + 0.5) * unit_minutes
    elif method == Constants.TIME_ROUNDING_METHOD.FLOOR:
        # 切り捨て
        rounded_minutes = math.floor(total_minutes_decimal / unit_minutes) * unit_minutes
    elif method == Constants.TIME_ROUNDING_METHOD.CEIL:
        # 切り上げ
        rounded_minutes = math.ceil(total_minutes_decimal / unit_minutes) * unit_minutes
    else:
        # 不明な方法の場合はそのまま返す
        return dt
    
    # 60分を超える場合の処理
    extra_hours = 0
    if rounded_minutes >= 60:
        extra_hours = int(rounded_minutes // 60)
        rounded_minutes = int(rounded_minutes % 60)
    else:
        rounded_minutes = int(rounded_minutes)
    
    # 新しい時刻を作成
    new_dt = dt.replace(minute=rounded_minutes, second=0, microsecond=0)
    
    # 時間の調整
    if extra_hours > 0:
        new_dt = new_dt + timedelta(hours=extra_hours)
    
    return new_dt


def apply_time_rounding(start_time, end_time, time_rounding_config):
    """
    勤怠打刻に時間丸め設定を適用する
    
    Args:
        start_time (datetime): 開始時刻
        end_time (datetime): 終了時刻
        time_rounding_config (TimeRounding): 時間丸め設定
    
    Returns:
        tuple: (rounded_start_time, rounded_end_time)
    """
    rounded_start_time = start_time
    rounded_end_time = end_time
    
    if not time_rounding_config:
        # 設定がない場合は元の時刻をそのまま返す
        return rounded_start_time, rounded_end_time
    
    # 開始時刻の丸め
    if start_time:
        rounded_start_time = round_time(
            start_time,
            time_rounding_config.start_time_unit,
            time_rounding_config.start_time_method
        )
    
    # 終了時刻の丸め
    if end_time:
        rounded_end_time = round_time(
            end_time,
            time_rounding_config.end_time_unit,
            time_rounding_config.end_time_method
        )
    
    return rounded_start_time, rounded_end_time


def apply_break_time_rounding(break_start, break_end, time_rounding_config):
    """
    休憩時間に時間丸め設定を適用する
    
    Args:
        break_start (datetime): 休憩開始時刻
        break_end (datetime): 休憩終了時刻
        time_rounding_config (TimeRounding): 時間丸め設定
    
    Returns:
        tuple: (rounded_break_start, rounded_break_end)
    """
    rounded_break_start = break_start
    rounded_break_end = break_end
    
    if not time_rounding_config or not time_rounding_config.break_input:
        # 設定がない場合や休憩入力が無効な場合は元の時刻をそのまま返す
        return rounded_break_start, rounded_break_end
    
    # 休憩開始時刻の丸め
    if break_start:
        rounded_break_start = round_time(
            break_start,
            time_rounding_config.break_start_unit,
            time_rounding_config.break_start_method
        )
    
    # 休憩終了時刻の丸め
    if break_end:
        rounded_break_end = round_time(
            break_end,
            time_rounding_config.break_end_unit,
            time_rounding_config.break_end_method
        )
    
    return rounded_break_start, rounded_break_end