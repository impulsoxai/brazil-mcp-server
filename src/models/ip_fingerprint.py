"""IpFingerprint ORM model."""

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class IpFingerprint(Base):
    __tablename__ = "ip_fingerprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip_address: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_ip_address", "ip_address"),
        Index("idx_ip_created", "ip_address", "created_at"),
    )
