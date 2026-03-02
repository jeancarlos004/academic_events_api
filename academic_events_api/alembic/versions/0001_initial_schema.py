"""Initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('nombre', sa.String(100), nullable=False),
        sa.Column('email', sa.String(150), unique=True, index=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('rol', sa.String(20), nullable=False, server_default='usuario'),
    )

    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('titulo', sa.String(200), nullable=False),
        sa.Column('descripcion', sa.String(1000), nullable=True),
        sa.Column('fecha', sa.Date(), nullable=False),
        sa.Column('hora', sa.String(10), nullable=False),
        sa.Column('lugar', sa.String(200), nullable=False),
        sa.Column('cupos', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(50), nullable=False),
        sa.Column('estado', sa.String(20), nullable=False, server_default='activo'),
    )

    op.create_table(
        'registrations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evento_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fecha_inscripcion', sa.DateTime(), nullable=False),
        sa.Column('asistencia', sa.Boolean(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('registrations')
    op.drop_table('events')
    op.drop_table('users')
