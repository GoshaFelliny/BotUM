from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('teachers', sa.Column('survey_completed', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('users', 'is_active')


upgrade()