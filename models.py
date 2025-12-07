from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    TIMESTAMP,
    ForeignKey,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, BYTEA
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Track(Base):
    __tablename__ = "tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    title = Column(Text, nullable=True)
    audio_url = Column(Text, nullable=True)
    audio_blob = Column(BYTEA, nullable=True)
    uploaded_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    duration_seconds = Column(Integer, nullable=True)
    sample_rate = Column(Integer, nullable=True)
    checksum_sha256 = Column(Text, nullable=True, unique=True)

    __table_args__ = (
        CheckConstraint(
            "(audio_url IS NOT NULL) OR (audio_blob IS NOT NULL)",
            name="tracks_audio_presence",
        ),
    )

    analyses = relationship("Analysis", back_populates="track", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    method = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default=text("'pending'"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    summary = Column(JSONB, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "method IN ('chromaprint','hpcp','dtw','lyrics','music_identification','similarity_detection','other')",
            name="analyses_method_check",
        ),
        CheckConstraint(
            "status IN ('pending','processing','running','completed','succeeded','failed')",
            name="analyses_status_check",
        ),
        Index("idx_analyses_track_id", "track_id"),
        Index("idx_analyses_track_method", "track_id", "method"),
    )

    track = relationship("Track", back_populates="analyses")
    artifacts = relationship("Artifact", back_populates="analysis", cascade="all, delete-orphan")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    artifact_type = Column(Text, nullable=False)
    content_type = Column(Text, nullable=True)
    data_json = Column(JSONB, nullable=True)
    data_blob = Column(BYTEA, nullable=True)
    data_url = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('chromaprint','hpcp','dtw_matrix','dtw_path','plot_image','feature_json','music_matches','other')",
            name="artifacts_type_check",
        ),
        CheckConstraint(
            "(data_json IS NOT NULL) OR (data_blob IS NOT NULL) OR (data_url IS NOT NULL)",
            name="artifacts_data_presence",
        ),
        Index("idx_artifacts_analysis_id", "analysis_id"),
    )

    analysis = relationship("Analysis", back_populates="artifacts")
