"""Create messages table and change user id for phone number

Revision ID: bcb5f08257ee
Revises: f2286f334b57
Create Date: 2025-02-26 16:38:41.159494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcb5f08257ee'
down_revision: Union[str, None] = 'f2286f334b57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create jobfrequency enum first
    op.execute("""
        CREATE TYPE jobfrequency AS ENUM (
            'daily',
            'weekly',
            'monthly'
        )
    """)
    
    # Create jobstatus enum before using it
    op.execute("""
        CREATE TYPE jobstatus AS ENUM (
            'pending',
            'running',
            'completed',
            'failed',
            'deactivated'
        )
    """)
    
    # Now alter both columns
    op.alter_column('scheduled_jobs', 'frequency',
               existing_type=sa.VARCHAR(),
               type_=sa.Enum('daily', 'weekly', 'monthly', name='jobfrequency'),
               postgresql_using='frequency::jobfrequency',
               nullable=True)
    
    op.alter_column('scheduled_jobs', 'status',
               existing_type=sa.VARCHAR(),
               type_=sa.Enum('pending', 'running', 'completed', 'failed', 'deactivated', name='jobstatus'),
               postgresql_using='status::jobstatus',
               nullable=True)
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'email')
    # ### end Alembic commands ###


def downgrade() -> None:
    # Revert columns first
    op.alter_column('scheduled_jobs', 'status',
               existing_type=sa.Enum('pending', 'running', 'completed', 'failed', 'deactivated', name='jobstatus'),
               type_=sa.VARCHAR(),
               postgresql_using='status::text',
               nullable=True)
    
    op.alter_column('scheduled_jobs', 'frequency',
               existing_type=sa.Enum('daily', 'weekly', 'monthly', name='jobfrequency'),
               type_=sa.VARCHAR(),
               postgresql_using='frequency::text',
               nullable=True)
    
    # Then drop enums
    op.execute("DROP TYPE jobstatus")
    op.execute("DROP TYPE jobfrequency")
    op.add_column('users', sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    # ### end Alembic commands ###
