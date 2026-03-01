"""Example: Data Migration Input
Feed this to: cat examples/inputs/migration-example.py | greybeard analyze --pack data-migrations
"""

# Alembic migration: add subscription_tier to users table
# Generated: 2024-03-01

import sqlalchemy as sa
from alembic import op

revision = "0047_add_subscription_tier"
down_revision = "0046_add_reptile_photos"


def upgrade():
    # Add column as NOT NULL with no default — will lock table during backfill
    op.add_column("users", sa.Column("subscription_tier", sa.String(), nullable=False))

    # Backfill all existing users to 'free'
    op.execute("UPDATE users SET subscription_tier = 'free'")

    # Add index after backfill
    op.create_index("ix_users_subscription_tier", "users", ["subscription_tier"])

    # Add foreign key to new subscription_limits table
    op.create_foreign_key(
        "fk_users_subscription_tier",
        "users",
        "subscription_limits",
        ["subscription_tier"],
        ["tier_name"],
    )


def downgrade():
    op.drop_column("users", "subscription_tier")
