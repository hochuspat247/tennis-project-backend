"""Initial migration

Revision ID: d63bfb2a903f
Revises: 
Create Date: 2025-04-10 15:53:18.022106
"""

from alembic import op
import sqlalchemy as sa

revision = "d63bfb2a903f"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Создание таблицы users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='player'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

    # Создание таблицы courts
    op.create_table(
        'courts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_courts_id', 'courts', ['id'], unique=False)

    # Создание таблицы bookings
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('court_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.ForeignKeyConstraint(['court_id'], ['courts.id'], name='bookings_court_id_fkey'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='bookings_user_id_fkey'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_bookings_id', 'bookings', ['id'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_bookings_id', table_name='bookings')
    op.drop_table('bookings')
    op.drop_index('ix_courts_id', table_name='courts')
    op.drop_table('courts')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')