"""create cases and consultations

Revision ID: 0001
Revises:
Create Date: 2026-11-21

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
        sa.UniqueConstraint("label", name=op.f("uq_cases_label")),
    )
    op.create_table(
        "consultations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("derived", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fired_rules", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("rules_version", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["cases.id"], name=op.f("fk_consultations_case_id_cases")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consultations")),
    )
    op.create_index(op.f("ix_consultations_case_id"), "consultations", ["case_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_consultations_case_id"), table_name="consultations")
    op.drop_table("consultations")
    op.drop_table("cases")
