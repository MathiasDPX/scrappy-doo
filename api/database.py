import os
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func
from dotenv import load_dotenv
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import event

# Load environment variables
load_dotenv()

# Build database URL
DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Create SQLAlchemy engine with AUTOCOMMIT for read-only selects
engine = create_engine(DATABASE_URL, echo=False, isolation_level="AUTOCOMMIT")


@event.listens_for(engine, "connect")
def set_readonly(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    # Enforce read-only on the connection
    cursor.execute("SET default_transaction_read_only = on;")
    cursor.close()


Base = declarative_base()


class ReadOnlySession(Session):
    def add(self, instance, _warn=True):
        raise RuntimeError("Read-only session: add() is disabled.")

    def add_all(self, instances, _warn=True):
        raise RuntimeError("Read-only session: add_all() is disabled.")

    def delete(self, instance):
        raise RuntimeError("Read-only session: delete() is disabled.")

    def merge(self, instance, load=True, options=None):
        raise RuntimeError("Read-only session: merge() is disabled.")

    def flush(self, objects=None):
        if self.new or self.dirty or self.deleted:
            raise RuntimeError("Read-only session: flush() is disabled.")
        return

    def commit(self):
        raise RuntimeError("Read-only session: commit() is disabled.")

    def bulk_save_objects(
        self, objects, return_defaults=False, update_changed_only=True
    ):
        raise RuntimeError("Read-only session: bulk_save_objects() is disabled.")

    def bulk_insert_mappings(self, mapper, mappings, render_nulls=False):
        raise RuntimeError("Read-only session: bulk_insert_mappings() is disabled.")

    def bulk_update_mappings(self, mapper, mappings):
        raise RuntimeError("Read-only session: bulk_update_mappings() is disabled.")


SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=ReadOnlySession,
    autoflush=False,
)
session = SessionLocal()


class Post(Base):
    __tablename__ = "posts"

    message_id = Column(String(128), primary_key=True, nullable=False)
    message = Column(Text, nullable=False)
    author = Column(String(64), nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    tags = Column(MutableList.as_mutable(PG_ARRAY(String)), default=list)
    files = Column(MutableList.as_mutable(PG_ARRAY(String)), default=list)

    __table_args__ = (
        UniqueConstraint("author", "timestamp", name="uq_author_timestamp"),
    )

    # Class methods
    @classmethod
    def get_by_id(cls, id_):
        return session.query(cls).filter_by(message_id=id_).first()

    @classmethod
    def get_by_author(cls, author, limit=50, offset=0):
        return session.query(cls).filter_by(author=author).order_by(cls.timestamp.desc()).limit(limit).offset(offset).all()

    @classmethod
    def get_latests(cls, limit=50):
        return (
            session.query(cls)
            .order_by(cls.timestamp.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_by_tag(cls, tag, limit=50, offset=0):
        limit = min(limit, 100)
        return (
            session.query(cls)
            .filter(cls.tags.contains([tag]))
            .order_by(cls.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def asdict(self):
        return {
            "content": self.message,
            "message_id": self.message_id,
            "tags": self.tags,
            "timestamp": int(self.timestamp.timestamp()),
            "files": self.files
        }
