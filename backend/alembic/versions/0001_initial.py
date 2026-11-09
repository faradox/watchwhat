"""movies and who has seen them

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op

from app.db import UTCDateTime

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "movie",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tmdb_id", sa.Integer(), nullable=True),
        sa.Column("imdb_id", sa.String(16), nullable=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("original_title", sa.String(300), nullable=True),
        sa.Column("original_language", sa.String(8), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("runtime_min", sa.Integer(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("director", sa.String(200), nullable=True),
        sa.Column("cast", sa.JSON(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("poster_path", sa.String(200), nullable=True),
        sa.Column("trailer_youtube_key", sa.String(32), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("blurb", sa.Text(), nullable=True),
        sa.Column("moods", sa.JSON(), nullable=False),
        sa.Column("attention", sa.String(16), nullable=True),
        sa.Column("violence", sa.Integer(), nullable=True),
        sa.Column("scariness", sa.Integer(), nullable=True),
        sa.Column("heaviness", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("never_suggest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("added_by", sa.String(100), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.UniqueConstraint("tmdb_id", name="uq_movie_tmdb_id"),
    )
    op.create_table(
        "seen",
        sa.Column(
            "movie_id",
            sa.Integer(),
            sa.ForeignKey("movie.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_name", sa.String(100), primary_key=True),
        sa.Column("seen_at", UTCDateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("seen")
    op.drop_table("movie")
