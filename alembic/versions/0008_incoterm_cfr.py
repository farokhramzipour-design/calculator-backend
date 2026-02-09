from __future__ import annotations

from alembic import op

revision = "0008_incoterm_cfr"
down_revision = "0007_countries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE incoterm ADD VALUE IF NOT EXISTS 'CFR'")


def downgrade() -> None:
    # Postgres doesn't support removing enum values easily; no-op
    pass
