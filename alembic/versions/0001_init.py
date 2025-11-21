from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'identity_checks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('deepfake_score', sa.Float, default=0.0),
        sa.Column('liveness_status', sa.String(32), default='PASS'),
        sa.Column('overall_result', sa.String(32), default='VERIFIED'),
        sa.Column('latency_ms', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'official_apps',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('package_name', sa.String(255)),
        sa.Column('sha256_hash', sa.String(64)),
        sa.Column('publisher', sa.String(255)),
        sa.Column('google_play_link', sa.Text),
        sa.Column('last_verified', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint('uq_official_apps_package_name', 'official_apps', ['package_name'])

    op.create_table(
        'suspicious_apps',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('package_name', sa.String(255)),
        sa.Column('publisher', sa.String(255)),
        sa.Column('google_play_link', sa.Text),
        sa.Column('confidence', sa.Float, default=0.8),
    )

    op.create_table(
        'grievances',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('complaint_id', sa.String(64), unique=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('text', sa.Text),
        sa.Column('category', sa.String(64), default='other'),
        sa.Column('urgency', sa.String(16), default='MEDIUM'),
        sa.Column('status', sa.String(32), default='RECEIVED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table('grievances')
    op.drop_table('suspicious_apps')
    op.drop_constraint('uq_official_apps_package_name', 'official_apps', type_='unique')
    op.drop_table('official_apps')
    op.drop_table('identity_checks')
    op.drop_table('users')
