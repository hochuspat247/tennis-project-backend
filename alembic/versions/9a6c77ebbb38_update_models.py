"""Update models

Revision ID: 9a6c77ebbb38
Revises: d63bfb2a903f
Create Date: 2025-04-10 23:11:32.239437
"""

from alembic import op
import sqlalchemy as sa

revision = "9a6c77ebbb38"
down_revision = "d63bfb2a903f"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Обновление таблицы users
    op.add_column('users', sa.Column('first_name', sa.String(), nullable=False))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=False))
    op.add_column('users', sa.Column('birth_date', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(), nullable=False))
    op.add_column('users', sa.Column('photo', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_code', sa.String(), nullable=True))
    op.drop_column('users', 'full_name')  # Удаляем старое поле full_name
    op.create_unique_constraint('uq_users_phone', 'users', ['phone'])

    # Обновление таблицы bookings
    op.add_column('bookings', sa.Column('price', sa.Integer(), nullable=False))
    op.alter_column('bookings', 'status', server_default='active')

def downgrade() -> None:
    # Откат изменений для таблицы users
    op.drop_column('users', 'verification_code')
    op.drop_column('users', 'photo')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'birth_date')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=False))
    op.drop_constraint('uq_users_phone', 'users', type_='unique')

    # Откат изменений для таблицы bookings
    op.drop_column('bookings', 'price')
    op.alter_column('bookings', 'status', server_default='pending')