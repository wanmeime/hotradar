"""平台爬虫基类"""
from abc import abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class HotItem:
    """热点数据项"""
    platform: str        # 平台标识: weibo, douyin, zhihu, xiaohongshu
    title: str           # 标题
    rank: int            # 排名
    heat: str            # 热度值
    url: str             # 跳转链接
    fetched_at: str      # 抓取时间 ISO8601
    raw_data: dict = None  # 原始数据（保留扩展）


class BaseSpider:
    """爬虫基类"""

    name = ""
    platform = ""

    def __init__(self, logger):
        self.logger = logger

    @abstractmethod
    def fetch(self) -> List[HotItem]:
        """抓取热点列表，子类必须实现"""
        pass
