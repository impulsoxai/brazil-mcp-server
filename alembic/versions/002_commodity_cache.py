"""commodity_cache table

Revision ID: 002_commodity_cache
Revises: 9bf7445cfb65
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "002_commodity_cache"
down_revision = "9bf7445cfb65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commodity_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("commodity", sa.String(50), nullable=False, unique=True),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("unidade", sa.String(50), nullable=False),
        sa.Column("fonte", sa.String(100), nullable=False),
        sa.Column("data_referencia", sa.Date(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_commodity_cache_commodity", "commodity_cache", ["commodity"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_commodity_cache_commodity", table_name="commodity_cache")
    op.drop_table("commodity_cache")
