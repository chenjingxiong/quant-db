# -*- coding: utf-8 -*-
"""
辅助函数
"""
from datetime import datetime, time


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化时间戳"""
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    return str(dt)


def parse_symbol(symbol: str) -> tuple:
    """
    解析股票/期货代码

    Args:
        symbol: 代码字符串

    Returns:
        (市场, 代码)
    """
    symbol = symbol.upper().strip()

    # 处理带前缀的代码
    if symbol.startswith("SH"):
        return "SH", symbol[2:]
    elif symbol.startswith("SZ"):
        return "SZ", symbol[2:]

    # 根据代码判断市场
    if symbol.startswith("6"):
        return "SH", symbol
    elif symbol.startswith(("0", "3")):
        return "SZ", symbol
    else:
        # 默认深圳
        return "SZ", symbol


def is_trading_time(dt: datetime = None) -> bool:
    """
    判断是否在交易时间内

    Args:
        dt: 时间戳，默认为当前时间

    Returns:
        是否在交易时间
    """
    if dt is None:
        dt = datetime.now()

    # 获取时间和星期
    current_time = dt.time()
    weekday = dt.weekday()

    # 周末不交易
    if weekday >= 5:
        return False

    # 交易时间段
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)

    # 判断是否在交易时间
    if morning_start <= current_time <= morning_end:
        return True
    if afternoon_start <= current_time <= afternoon_end:
        return True

    return False


def get_next_trading_time(dt: datetime = None) -> datetime:
    """
    获取下一个交易时间

    Args:
        dt: 当前时间

    Returns:
        下一个交易时间
    """
    if dt is None:
        dt = datetime.now()

    # 如果是周末，移动到下周一9:30
    if dt.weekday() >= 5:
        days_to_monday = 7 - dt.weekday()
        next_time = dt.replace(hour=9, minute=30, second=0, microsecond=0)
        return next_time + datetime.timedelta(days=days_to_monday)

    current_time = dt.time()

    # 下午收盘后，移动到第二天9:30
    if current_time >= time(15, 0):
        next_time = dt.replace(hour=9, minute=30, second=0, microsecond=0)
        return next_time + datetime.timedelta(days=1)

    # 午休时间，移动到13:00
    if time(11, 30) <= current_time < time(13, 0):
        return dt.replace(hour=13, minute=0, second=0, microsecond=0)

    # 早上开盘前，移动到9:30
    if current_time < time(9, 30):
        return dt.replace(hour=9, minute=30, second=0, microsecond=0)

    return dt
