import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, TIMESTAMP, ARRAY, exists
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv
from sqlalchemy.ext.mutable import MutableList  # NEW

# Load environment variables
load_dotenv()

# Build database URL
DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False)

# ORM base class
Base = declarative_base()

# Create session factory
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)  # CHANGED
session = SessionLocal()


class Post(Base):
    __tablename__ = "posts"

    message_id = Column(String(128), primary_key=True, nullable=False)
    message = Column(Text, nullable=False)
    author = Column(String(64), nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    tags = Column(MutableList.as_mutable(ARRAY(String)), default=list)  # CHANGED

    # Instance methods
    def save(self):
        if session.query(Post).filter_by(message_id=self.message_id).first():
            return False

        session.add(self)
        session.commit()
        return True

    def delete(self):
        session.delete(self)
        session.commit()

    def set_tags(self, tags):
        self.tags = tags
        session.commit()

    # Class methods
    @classmethod
    def get_by_id(cls, id_):
        return session.query(cls).filter_by(message_id=id_).first()

    @classmethod
    def get_by_author(cls, author):
        return session.query(cls).filter_by(author=author).all()

    @classmethod
    def get_by_tag(cls, tag, limit=50):
        limit = min(limit, 100)
        return (
            session.query(cls)
            .filter(tag == func.any(cls.tags))
            .order_by(cls.timestamp.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def delete_by_id(cls, id_):
        obj = session.query(cls).filter_by(message_id=id_).first()
        if obj:
            session.delete(obj)
            session.commit()
            return True
        return False


def init_db():
    """Creates tables if they do not exist."""
    Base.metadata.create_all(engine)
