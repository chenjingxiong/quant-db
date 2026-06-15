# -*- coding: utf-8 -*-
"""
pytdx 数据源适配器

通达信数据源是目前国内最常用的免费行情数据源之一
"""
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

try:
    from pytdx.hq import TdxHq_API
    from pytdx.params import TDXParams
    PYTDX_AVAILABLE = True
except ImportError:
    PYTDX_AVAILABLE = False
    TDXParams = None
    TdxHq_API = None
    logger.warning("pytdx not installed, install with: pip install pytdx")

from .base import BaseAdapter, Quote, Bar, Tick
from ..utils.async_helper import get_event_loop


class PytdxAdapter(BaseAdapter):
    """
    pytdx 通达信数据源适配器

    支持功能:
    - 股票实时行情
    - 期货实时行情
    - K线数据
    - 股票列表
    """

    # 通达信市场代码映射
    MARKET_SH = 1  # 上海
    MARKET_SZ = 0  # 深圳

    # K线周期映射
    INTERVAL_MAP = {
        "1min": 9,    # 1分钟
        "5min": 0,    # 5分钟
        "15min": 1,   # 15分钟
        "30min": 2,   # 30分钟
        "60min": 3,   # 60分钟
        "1h": 3,      # 1小时
        "1day": 5,    # 日K
        "1week": 6,   # 周K
        "1month": 7,  # 月K
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        if not PYTDX_AVAILABLE:
            raise ImportError("pytdx is not installed")

        # 配置
        self.hosts = self.config.get("hosts", ["119.147.212.81"])
        self.port = self.config.get("port", 7709)
        self.time_out = self.config.get("timeout", 5)

        # 连接状态
        self.api: Optional["TdxHq_API"] = None
        self.current_host = None
        self.current_market_id = 0

    async def connect(self) -> bool:
        """连接通达信服务器"""
        try:
            if self.api:
                await self.disconnect()

            self.api = TdxHq_API(raise_exception=True)

            # 尝试连接可用的服务器
            for host in self.hosts:
                try:
                    # 在线程池中执行同步连接
                    result = await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: self.api.connect(host, self.port, time_out=self.time_out)
                    )

                    if result:
                        self.current_host = host
                        self.is_connected = True
                        logger.info(f"{self.name}: connected to {host}:{self.port}")
                        return True

                except Exception as e:
                    logger.debug(f"{self.name}: failed to connect {host} - {e}")
                    continue

            logger.error(f"{self.name}: all connection attempts failed")
            self.is_connected = False
            return False

        except Exception as e:
            logger.error(f"{self.name}: connect error - {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """断开连接"""
        try:
            if self.api:
                await asyncio.get_running_loop().run_in_executor(None, self.api.disconnect)
                self.api = None
            self.is_connected = False
            logger.info(f"{self.name}: disconnected")
        except Exception as e:
            logger.error(f"{self.name}: disconnect error - {e}")

    def _ensure_connected(self):
        """确保已连接"""
        if not self.is_connected or not self.api:
            raise ConnectionError(f"{self.name}: not connected")

    async def _reconnect_if_needed(self) -> bool:
        """检测断线并自动重连

        pytdx 的 TCP 连接长时间空闲会断开，但 is_connected 标志不会自动更新。
        本方法在每次调用前验证连接，失败则尝试重连。
        """
        if not self.is_connected or not self.api:
            return await self.connect()

        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_count(1)
            )
            if result is None or result <= 0:
                logger.warning(f"{self.name}: connection seems dead, reconnecting")
                self.is_connected = False
                return await self.connect()
            return True
        except Exception as e:
            logger.warning(f"{self.name}: connection lost ({e}), reconnecting")
            self.is_connected = False
            return await self.connect()

    # 指数代码市场映射
    INDEX_MARKET_MAP = {
        "000001": (1, "SH"),   # 上证指数
        "000300": (1, "SH"),   # 沪深300
        "000016": (1, "SH"),   # 上证50
        "000905": (1, "SH"),   # 中证500
        "000852": (1, "SH"),   # 中证1000
        "399001": (0, "SZ"),   # 深证成指
        "399006": (0, "SZ"),   # 创业板指
    }

    def _parse_symbol(self, symbol: str) -> tuple:
        """
        解析股票代码

        Args:
            symbol: 股票代码，如 000001, 600000, sh000001, sz000001

        Returns:
            (market, code): (市场代码, 股票代码)
        """
        symbol = symbol.upper().strip()

        # 处理带市场前缀的代码
        if symbol.startswith("SH"):
            return self.MARKET_SH, symbol[2:]
        elif symbol.startswith("SZ"):
            return self.MARKET_SZ, symbol[2:]

        # 根据代码前缀判断市场
        if symbol.startswith("6"):
            return self.MARKET_SH, symbol
        elif symbol.startswith(("0", "3")):
            return self.MARKET_SZ, symbol
        else:
            # 默认深圳
            return self.MARKET_SZ, symbol

    async def get_stock_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取股票实时行情"""
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            # 转换为通达信格式
            tdx_symbols = []
            for symbol in symbols:
                market, code = self._parse_symbol(symbol)
                tdx_symbols.append((market, code))

            # 分批查询（通达信一次最多800只）
            batch_size = 800
            all_quotes = []

            loop = get_event_loop()

            for i in range(0, len(tdx_symbols), batch_size):
                batch = tdx_symbols[i:i + batch_size]
                data = await loop.run_in_executor(
                    None,
                    lambda: self.api.get_security_quotes(batch)
                )
                all_quotes.extend(data or [])

            # 转换为Quote格式
            quotes = []
            now = datetime.now()

            for item in all_quotes:
                try:
                    code = item["code"]
                    market = "SH" if item["market"] == self.MARKET_SH else "SZ"
                    symbol = f"{market}{code}"

                    price = float(item.get("price", 0))
                    last_close = float(item.get("last_close", 0))
                    open_price = float(item.get("open", 0))
                    high_price = float(item.get("high", 0))
                    low_price = float(item.get("low", 0))
                    vol = float(item.get("vol", 0))
                    amt = float(item.get("amount", 0))

                    change = price - last_close if price > 0 and last_close > 0 else None
                    change_pct = (change / last_close * 100) if change is not None and last_close > 0 else None

                    quotes.append(Quote(
                        symbol=symbol,
                        ts=now,
                        open=open_price if open_price > 0 else None,
                        high=high_price if high_price > 0 else None,
                        low=low_price if low_price > 0 else None,
                        close=price if price > 0 else None,
                        pre_close=last_close if last_close > 0 else None,
                        volume=vol if vol > 0 else None,
                        amount=amt if amt > 0 else None,
                        change=change,
                        change_percent=change_pct,
                        extra={
                            "bid1": float(item["bid1"]) if item.get("bid1", 0) > 0 else None,
                            "bid_vol1": float(item["bid_vol1"]) if item.get("bid_vol1", 0) > 0 else None,
                            "ask1": float(item["ask1"]) if item.get("ask1", 0) > 0 else None,
                            "ask_vol1": float(item["ask_vol1"]) if item.get("ask_vol1", 0) > 0 else None,
                        }
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse quote error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(quotes)} stock quotes")
            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_stock_quotes error - {e}")
            return []

    async def get_futures_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取期货实时行情"""
        # pytdx也支持期货行情，使用类似的接口
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            # 期货市场代码
            MARKET_CFFEX = 47  # 中金所
            MARKET_SHFE = 48   # 上期所
            MARKET_DCE = 49    # 大商所
            MARKET_CZCE = 50   # 郑商所

            # 根据代码判断期货交易所
            def get_future_market(symbol: str) -> int:
                s = symbol.upper()
                if s.startswith(("IF", "IH", "IC", "IM", "T", "TF", "TS", "TL")):
                    return MARKET_CFFEX
                elif s.startswith(("AU", "AG", "CU", "AL", "ZN", "PB", "NI", "SN", "RB", "HC", "SS", "WR", "SP")):
                    return MARKET_SHFE
                elif s.startswith(("I", "JM", "J", "A", "B", "M", "Y", "P", "L", "PP", "V", "EB", "EG", "PG")):
                    return MARKET_DCE
                elif s.startswith(("SR", "CF", "TA", "MA", "RM", "OI", "ZC", "FG", "UR", "SA", "AP", "CJ", "PK", "SF", "SM")):
                    return MARKET_CZCE
                return MARKET_CFFEX  # 默认

            # 转换格式
            tdx_symbols = [(get_future_market(s), s) for s in symbols]

            loop = get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_quotes(tdx_symbols)
            )

            quotes = []
            now = datetime.now()

            for item in data or []:
                try:
                    price = float(item.get("price", 0))
                    last_close = float(item.get("last_close", 0))
                    open_price = float(item.get("open", 0))
                    high_price = float(item.get("high", 0))
                    low_price = float(item.get("low", 0))
                    vol = float(item.get("vol", 0))
                    amt = float(item.get("amount", 0))

                    change = price - last_close if price > 0 and last_close > 0 else None
                    change_pct = (change / last_close * 100) if change is not None and last_close > 0 else None

                    quotes.append(Quote(
                        symbol=item["code"],
                        ts=now,
                        open=open_price if open_price > 0 else None,
                        high=high_price if high_price > 0 else None,
                        low=low_price if low_price > 0 else None,
                        close=price if price > 0 else None,
                        volume=vol if vol > 0 else None,
                        amount=amt if amt > 0 else None,
                        change=change,
                        change_percent=change_pct,
                        extra={}
                    ))
                except Exception:
                    continue

            logger.debug(f"{self.name}: got {len(quotes)} futures quotes")
            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_futures_quotes error - {e}")
            return []

    async def get_stock_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取股票K线数据"""
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            # 解析周期
            kline_type = self.INTERVAL_MAP.get(interval)
            if kline_type is None:
                logger.warning(f"{self.name}: unsupported interval {interval}")
                return []

            market, code = self._parse_symbol(symbol)

            loop = get_event_loop()

            # 获取K线数据
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_bars(
                    kline_type,
                    market,
                    code,
                    start=0,
                    count=limit
                )
            )

            bars = []
            for item in (data or []):
                try:
                    # 解析时间 (pytdx datetime格式可能是 "2024-01-01" 或 "2024-01-01 15:00")
                    dt_str = str(item["datetime"])
                    if len(dt_str) <= 10:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

                    # 时间范围过滤
                    if start_time and dt < start_time:
                        continue
                    if end_time and dt > end_time:
                        continue

                    bars.append(Bar(
                        symbol=symbol,
                        interval=interval,
                        ts=dt,
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                        volume=float(item["vol"]),
                        amount=float(item.get("amount", 0))
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse bar error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(bars)} bars for {symbol}")
            return bars

        except Exception as e:
            logger.error(f"{self.name}: get_stock_bars error - {e}")
            return []

    async def get_futures_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取期货K线数据"""
        # 期货K线获取逻辑与股票类似
        return await self.get_stock_bars(symbol, interval, start_time, end_time, limit)

    async def get_stock_ticks(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Tick]:
        """获取股票逐笔成交"""
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            market, code = self._parse_symbol(symbol)

            loop = get_event_loop()

            # 获取历史分笔成交
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_history_transaction_data(
                    market,
                    code,
                    start=0,
                    count=limit
                )
            )

            ticks = []
            for item in data or []:
                try:
                    dt = datetime.strptime(item["date"], "%Y-%m-%d %H:%M:%S")

                    if start_time and dt < start_time:
                        continue
                    if end_time and dt > end_time:
                        continue

                    # 判断买卖方向
                    direction = "B" if item["buyorsell"] == 1 else "S"

                    ticks.append(Tick(
                        symbol=symbol,
                        ts=dt,
                        price=float(item["price"]),
                        volume=float(item["vol"]),
                        amount=float(item["amount"]),
                        direction=direction
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse tick error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(ticks)} ticks for {symbol}")
            return ticks

        except Exception as e:
            logger.error(f"{self.name}: get_stock_ticks error - {e}")
            return []

    async def get_all_stock_list(self) -> List[Dict[str, Any]]:
        """获取所有股票列表（分页获取全部，部分服务器首页返回空需要跳过）"""
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            loop = get_event_loop()

            all_stocks = []
            for market, market_name in [(self.MARKET_SH, "SH"), (self.MARKET_SZ, "SZ")]:
                # 先获取总数量，确定遍历上限
                try:
                    total_count = await loop.run_in_executor(
                        None, lambda m=market: self.api.get_security_count(m)
                    )
                except Exception:
                    total_count = 50000  # fallback upper bound
                page_size = 1000
                start = 0
                empty_pages = 0
                while start < total_count and empty_pages < 3:
                    items = await loop.run_in_executor(
                        None,
                        lambda s=start, m=market: self.api.get_security_list(m, s)
                    )
                    if not items:
                        empty_pages += 1
                        start += page_size
                        continue
                    empty_pages = 0
                    for item in items:
                        code = item.get("code", "")
                        if market_name == "SH" and code.startswith("6"):
                            all_stocks.append({
                                "symbol": f"SH{code}",
                                "code": code,
                                "name": item.get("name", ""),
                                "market": "SH"
                            })
                        elif market_name == "SZ" and (code.startswith("0") or code.startswith("3") or code.startswith("2")):
                            all_stocks.append({
                                "symbol": f"SZ{code}",
                                "code": code,
                                "name": item.get("name", ""),
                                "market": "SZ"
                            })
                    start += page_size

            if all_stocks:
                logger.info(f"{self.name}: got {len(all_stocks)} stocks")
                return all_stocks

            return self._fallback_stock_list()

        except Exception as e:
            logger.error(f"{self.name}: get_all_stock_list error - {e}")
            return self._fallback_stock_list()

    def _fallback_stock_list(self) -> List[Dict[str, Any]]:
        """后备股票列表（沪深300成分股）"""
        logger.info(f"{self.name}: using fallback stock list")
        symbols = [
            ("600000", "浦发银行", "SH"), ("600030", "中信证券", "SH"),
            ("600036", "招商银行", "SH"), ("600104", "上汽集团", "SH"),
            ("600111", "北方稀土", "SH"), ("600276", "恒瑞医药", "SH"),
            ("600309", "万华化学", "SH"), ("600519", "贵州茅台", "SH"),
            ("600585", "海螺水泥", "SH"), ("600809", "山西汾酒", "SH"),
            ("600887", "伊利股份", "SH"), ("600900", "长江电力", "SH"),
            ("601012", "隆基绿能", "SH"), ("601088", "中国神华", "SH"),
            ("601166", "兴业银行", "SH"), ("601288", "农业银行", "SH"),
            ("601318", "中国平安", "SH"), ("601398", "工商银行", "SH"),
            ("601668", "中国建筑", "SH"), ("601888", "中国中免", "SH"),
            ("601899", "紫金矿业", "SH"), ("601985", "中国核电", "SH"),
            ("603259", "药明康德", "SH"), ("603288", "海天味业", "SH"),
            ("000001", "平安银行", "SZ"), ("000002", "万科A", "SZ"),
            ("000063", "中兴通讯", "SZ"), ("000333", "美的集团", "SZ"),
            ("000568", "泸州老窖", "SZ"), ("000651", "格力电器", "SZ"),
            ("000725", "京东方A", "SZ"), ("000858", "五粮液", "SZ"),
            ("002142", "宁波银行", "SZ"), ("002230", "科大讯飞", "SZ"),
            ("002415", "海康威视", "SZ"), ("002460", "赣锋锂业", "SZ"),
            ("002475", "立讯精密", "SZ"), ("002594", "比亚迪", "SZ"),
            ("002714", "牧原股份", "SZ"), ("300015", "爱尔眼科", "SZ"),
            ("300059", "东方财富", "SZ"), ("300124", "汇川技术", "SZ"),
            ("300274", "阳光电源", "SZ"), ("300498", "温氏股份", "SZ"),
            ("300750", "宁德时代", "SZ"), ("300760", "迈瑞医疗", "SZ"),
        ]
        return [{"symbol": f"{m}{c}", "code": c, "name": n, "market": m}
                for c, n, m in symbols]

    async def get_all_futures_list(self) -> List[Dict[str, Any]]:
        """获取所有期货合约列表"""
        # pytdx获取期货合约列表的方法类似
        # 这里简化返回
        return []

    async def get_index_bars(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Bar]:
        """获取指数K线数据"""
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            kline_type = self.INTERVAL_MAP.get(interval)
            if kline_type is None:
                logger.warning(f"{self.name}: unsupported interval {interval}")
                return []

            # 指数使用专用的市场映射
            code = symbol.upper().replace("SH", "").replace("SZ", "")
            if code in self.INDEX_MARKET_MAP:
                market, _ = self.INDEX_MARKET_MAP[code]
            elif code.startswith("399"):
                market = self.MARKET_SZ
            else:
                market = self.MARKET_SH

            loop = get_event_loop()

            # 指数必须用 get_index_bars，不能用 get_security_bars（后者返回损坏数据）
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_index_bars(
                    kline_type,
                    market,
                    code,
                    start=0,
                    count=limit
                )
            )

            bars = []
            for item in (data or []):
                try:
                    dt_str = str(item["datetime"])
                    # 验证日期合理性，跳过损坏数据
                    if len(dt_str) <= 10:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                    if dt.year < 1990 or dt.year > 2030:
                        continue

                    if start_time and dt < start_time:
                        continue
                    if end_time and dt > end_time:
                        continue

                    bars.append(Bar(
                        symbol=symbol,
                        interval=interval,
                        ts=dt,
                        open=float(item["open"]),
                        high=float(item["high"]),
                        low=float(item["low"]),
                        close=float(item["close"]),
                        volume=float(item["vol"]),
                        amount=float(item.get("amount", 0))
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse index bar error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(bars)} index bars for {symbol}")
            return bars

        except Exception as e:
            logger.error(f"{self.name}: get_index_bars error - {e}")
            return []

    async def get_index_quotes(self, symbols: List[str]) -> List[Quote]:
        """获取指数实时行情"""
        try:
            if not await self._reconnect_if_needed():
                raise ConnectionError(f"{self.name}: failed to reconnect")

            # 指数代码映射: 上证指数(1,000001), 深证成指(0,399001)等
            INDEX_MARKET_MAP = {
                "000001": (1, "SH"),   # 上证指数
                "000300": (1, "SH"),   # 沪深300
                "000905": (1, "SH"),   # 中证500
                "000852": (1, "SH"),   # 中证1000
                "399001": (0, "SZ"),   # 深证成指
                "399006": (0, "SZ"),   # 创业板指
            }

            tdx_symbols = []
            code_market_map = {}
            for symbol in symbols:
                code = symbol.upper().replace("SH", "").replace("SZ", "")
                if code in INDEX_MARKET_MAP:
                    mkt, mkt_str = INDEX_MARKET_MAP[code]
                elif code.startswith("399"):
                    mkt, mkt_str = 0, "SZ"
                else:
                    mkt, mkt_str = 1, "SH"
                tdx_symbols.append((mkt, code))
                code_market_map[code] = mkt_str

            loop = get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.api.get_security_quotes(tdx_symbols)
            )

            quotes = []
            now = datetime.now()

            for item in data or []:
                try:
                    code = item["code"]
                    market = code_market_map.get(code, "SH")

                    price = float(item.get("price", 0))
                    last_close = float(item.get("last_close", 0))
                    change = price - last_close if price > 0 and last_close > 0 else None
                    change_pct = (change / last_close * 100) if change is not None and last_close > 0 else None

                    quotes.append(Quote(
                        symbol=f"{market}{code}",
                        ts=now,
                        open=float(item.get("open", 0)) or None,
                        high=float(item.get("high", 0)) or None,
                        low=float(item.get("low", 0)) or None,
                        close=price if price > 0 else None,
                        pre_close=last_close if last_close > 0 else None,
                        volume=float(item.get("vol", 0)) or None,
                        amount=float(item.get("amount", 0)) or None,
                        change=change,
                        change_percent=change_pct,
                    ))
                except Exception as e:
                    logger.warning(f"{self.name}: parse index quote error - {e}")
                    continue

            logger.debug(f"{self.name}: got {len(quotes)} index quotes")
            return quotes

        except Exception as e:
            logger.error(f"{self.name}: get_index_quotes error - {e}")
            return []
