"""тест

Revision ID: ed0d3944bd99
Revises: ae07edc2bfb3
Create Date: 2025-07-14 17:42:01.069192

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed0d3944bd99'
down_revision: Union[str, Sequence[str], None] = 'ae07edc2bfb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'promo_activations', type_='foreignkey')
    op.drop_constraint(None, 'promo_activations', type_='foreignkey')
    op.add_column('promo_codes', sa.Column('currency', sa.String(), nullable=True))
    op.add_column('promo_codes', sa.Column('is_one_time', sa.Boolean(), nullable=True))
    op.add_column('promo_codes', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
    op.add_column('promo_codes', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('promo_codes', sa.Column('comment', sa.String(), nullable=True))
    op.drop_column('promo_codes', 'is_active')
    op.create_foreign_key(None, 'users', 'users', ['referrer_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.add_column('promo_codes', sa.Column('is_active', sa.INTEGER(), nullable=True))
    op.drop_column('promo_codes', 'comment')
    op.drop_column('promo_codes', 'expires_at')
    op.drop_column('promo_codes', 'created_at')
    op.drop_column('promo_codes', 'is_one_time')
    op.drop_column('promo_codes', 'currency')
    op.create_foreign_key(None, 'promo_activations', 'promo_codes', ['promo_id'], ['id'])
    op.create_foreign_key(None, 'promo_activations', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###
