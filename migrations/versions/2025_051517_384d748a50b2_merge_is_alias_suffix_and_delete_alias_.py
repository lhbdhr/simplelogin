"""merge is_alias_suffix and delete alias to trash(v4.67.4)

Revision ID: 384d748a50b2
Revises: 48a8e90022d4, 87da368d282b
Create Date: 2025-05-15 17:38:09.217423

"""
import sqlalchemy_utils
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '384d748a50b2'
down_revision = ('48a8e90022d4', '87da368d282b')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
