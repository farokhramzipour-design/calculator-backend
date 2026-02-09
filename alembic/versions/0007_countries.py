from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_countries"
down_revision = "0006_passport_license"
branch_labels = None
depends_on = None


COUNTRIES = [
    ("EU", "Austria", "AT"),
    ("EU", "Belgium", "BE"),
    ("EU", "Bulgaria", "BG"),
    ("EU", "Croatia", "HR"),
    ("EU", "Cyprus", "CY"),
    ("EU", "Czechia", "CZ"),
    ("EU", "Denmark", "DK"),
    ("EU", "Estonia", "EE"),
    ("EU", "Finland", "FI"),
    ("EU", "France", "FR"),
    ("EU", "Germany", "DE"),
    ("EU", "Greece", "GR"),
    ("EU", "Hungary", "HU"),
    ("EU", "Ireland", "IE"),
    ("EU", "Italy", "IT"),
    ("EU", "Latvia", "LV"),
    ("EU", "Lithuania", "LT"),
    ("EU", "Luxembourg", "LU"),
    ("EU", "Malta", "MT"),
    ("EU", "Netherlands", "NL"),
    ("EU", "Poland", "PL"),
    ("EU", "Portugal", "PT"),
    ("EU", "Romania", "RO"),
    ("EU", "Slovakia", "SK"),
    ("EU", "Slovenia", "SI"),
    ("EU", "Spain", "ES"),
    ("EU", "Sweden", "SE"),
    ("EEA_non_EU", "Iceland", "IS"),
    ("EEA_non_EU", "Liechtenstein", "LI"),
    ("EEA_non_EU", "Norway", "NO"),
    ("Non_EU_Europe", "Albania", "AL"),
    ("Non_EU_Europe", "Andorra", "AD"),
    ("Non_EU_Europe", "Armenia", "AM"),
    ("Non_EU_Europe", "Azerbaijan", "AZ"),
    ("Non_EU_Europe", "Belarus", "BY"),
    ("Non_EU_Europe", "Bosnia and Herzegovina", "BA"),
    ("Non_EU_Europe", "Georgia", "GE"),
    ("Non_EU_Europe", "Kosovo", "XK"),
    ("Non_EU_Europe", "Moldova", "MD"),
    ("Non_EU_Europe", "Monaco", "MC"),
    ("Non_EU_Europe", "Montenegro", "ME"),
    ("Non_EU_Europe", "North Macedonia", "MK"),
    ("Non_EU_Europe", "San Marino", "SM"),
    ("Non_EU_Europe", "Serbia", "RS"),
    ("Non_EU_Europe", "Switzerland", "CH"),
    ("Non_EU_Europe", "Turkey", "TR"),
    ("Non_EU_Europe", "Ukraine", "UA"),
    ("Non_EU_Europe", "United Kingdom", "GB"),
    ("Non_EU_Europe", "Vatican City", "VA"),
]


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=2), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
    )

    countries_table = sa.table(
        "countries",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("region", sa.String),
    )
    values = []
    for region, name, code in COUNTRIES:
        safe_name = name.replace("'", "''")
        values.append("(gen_random_uuid(), '%s', '%s', '%s')" % (code, safe_name, region))
    insert_sql = "INSERT INTO countries (id, code, name, region) VALUES " + ", ".join(values)
    op.execute(insert_sql)


def downgrade() -> None:
    op.drop_table("countries")
