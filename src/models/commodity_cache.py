"""Commodity cache model — preços scrapados do CEPEA."""

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Integer, Numeric, String, func

from src.models.base import Base


class CommodityCache(Base):
    __tablename__ = "commodity_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commodity = Column(String(50), unique=True, nullable=False, index=True)
    preco = Column(Numeric(10, 2), nullable=False)
    unidade = Column(String(50), nullable=False)
    fonte = Column(String(100), nullable=False)
    data_referencia = Column(Date, nullable=False)
    scraped_at = Column(DateTime, nullable=False, server_default=func.now())
