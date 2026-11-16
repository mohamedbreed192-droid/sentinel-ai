"""Create analysis history."""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("analyses", sa.Column("id", sa.String(36), primary_key=True), sa.Column("repository", sa.String(200), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("report", sa.JSON(), nullable=True), sa.Column("error", sa.String(300), nullable=True))

def downgrade():
    op.drop_table("analyses")
