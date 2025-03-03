"""remove unnecessary columns in processed_videos

Revision ID: 139c4b28a40a
Revises: 3c480c0c6574
Create Date: 2025-03-02 21:49:43.623811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '139c4b28a40a'
down_revision: Union[str, None] = '3c480c0c6574'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_processed_videos_video_id', table_name='processed_videos')
    op.drop_table('processed_videos')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('processed_videos',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('video_id', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('message_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('url', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('thumbnail_url', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('duration', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('processed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['message_id'], ['messages.id'], name='processed_videos_message_id_fkey', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='processed_videos_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='processed_videos_pkey')
    )
    op.create_index('ix_processed_videos_video_id', 'processed_videos', ['video_id'], unique=False)
    # ### end Alembic commands ###
