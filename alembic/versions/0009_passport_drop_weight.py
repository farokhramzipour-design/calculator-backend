from __future__ import annotations

from alembic import op

revision = "0009_passport_drop_weight"
down_revision = "0008_incoterm_cfr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("passport_items", "weight")


def downgrade() -> None:
    op.add_column("passport_items", op.sql.Column("weight", op.sql.sqltypes.Numeric(18, 4)))
