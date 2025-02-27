"""Fix enum value handling in messages and scheduler tables

Revision ID: f74561835a79
Revises: a46468622121
Create Date: 2025-02-26 22:00:05.402683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f74561835a79'
down_revision: Union[str, None] = 'a46468622121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('messages', 'user_id',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('messages', 'direction',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('messages', 'body',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('messages', 'status',
               existing_type=postgresql.ENUM('received', 'sent', 'delivered', 'read', 'failed', name='message_status'),
               nullable=False)
    op.create_index(op.f('ix_messages_direction'), 'messages', ['direction'], unique=False)
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'email')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.drop_index(op.f('ix_messages_direction'), table_name='messages')
    op.alter_column('messages', 'status',
               existing_type=postgresql.ENUM('received', 'sent', 'delivered', 'read', 'failed', name='message_status'),
               nullable=True)
    op.alter_column('messages', 'body',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('messages', 'direction',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.alter_column('messages', 'user_id',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###
