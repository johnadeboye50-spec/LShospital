"""fix missing password reset columns

Revision ID: 8b9e6f1a2c4d
Revises: 5f24f8acde9f
Create Date: 2026-06-24 02:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b9e6f1a2c4d'
down_revision = '5f24f8acde9f'
branch_labels = None
depends_on = None


def _has_column(inspector, table_name, column_name):
    return any(column['name'] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, 'patient', 'password_reset_token'):
        with op.batch_alter_table('patient', schema=None) as batch_op:
            batch_op.add_column(sa.Column('password_reset_token', sa.String(length=255), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_column(inspector, 'patient', 'password_reset_expires_at'):
        with op.batch_alter_table('patient', schema=None) as batch_op:
            batch_op.add_column(sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_column(inspector, 'doctor', 'password_reset_token'):
        with op.batch_alter_table('doctor', schema=None) as batch_op:
            batch_op.add_column(sa.Column('password_reset_token', sa.String(length=255), nullable=True))

    inspector = sa.inspect(bind)
    if not _has_column(inspector, 'doctor', 'password_reset_expires_at'):
        with op.batch_alter_table('doctor', schema=None) as batch_op:
            batch_op.add_column(sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, 'patient', 'password_reset_expires_at'):
        with op.batch_alter_table('patient', schema=None) as batch_op:
            batch_op.drop_column('password_reset_expires_at')

    inspector = sa.inspect(bind)
    if _has_column(inspector, 'patient', 'password_reset_token'):
        with op.batch_alter_table('patient', schema=None) as batch_op:
            batch_op.drop_column('password_reset_token')

    inspector = sa.inspect(bind)
    if _has_column(inspector, 'doctor', 'password_reset_expires_at'):
        with op.batch_alter_table('doctor', schema=None) as batch_op:
            batch_op.drop_column('password_reset_expires_at')

    inspector = sa.inspect(bind)
    if _has_column(inspector, 'doctor', 'password_reset_token'):
        with op.batch_alter_table('doctor', schema=None) as batch_op:
            batch_op.drop_column('password_reset_token')
