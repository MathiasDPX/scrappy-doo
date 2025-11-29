import os
from sqlalchemy import create_engine, Column, String, Text, TIMESTAMP, ARRAY, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv
from sqlalchemy.ext.mutable import MutableList

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
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
session = SessionLocal()


class Post(Base):
    __tablename__ = "posts"

    message_id = Column(String(128), primary_key=True, nullable=False)
    message = Column(Text, nullable=False)
    author = Column(String(64), nullable=False)
    timestamp = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    tags = Column(MutableList.as_mutable(ARRAY(String)), default=list)
    files = Column(MutableList.as_mutable(ARRAY(String)), default=list)

    __table_args__ = (
        UniqueConstraint('author', 'timestamp', name='uq_author_timestamp'),
    )

    # Instance methods
    def save(self):
        if session.query(Post).filter_by(message_id=self.message_id).first():
            return False
        
        # Check for existing author-timestamp combination
        if session.query(Post).filter_by(author=self.author, timestamp=self.timestamp).first():
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

    def set_files(self, files):
        """Set the files list for this post."""
        self.files = files
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

    @classmethod
    def save_batch(cls, posts):
        """Save multiple posts in a single transaction. Returns count of successfully saved posts."""
        existing_ids = {
            row[0] for row in session.query(cls.message_id)
            .filter(cls.message_id.in_([p.message_id for p in posts]))
            .all()
        }

        # Check for existing author-timestamp combinations
        from sqlalchemy import tuple_
        author_timestamp_pairs = [(p.author, p.timestamp) for p in posts]
        existing_author_timestamps = {
            (row[0], row[1]) for row in session.query(cls.author, cls.timestamp)
            .filter(tuple_(cls.author, cls.timestamp).in_(author_timestamp_pairs))
            .all()
        }

        new_posts = [
            p for p in posts 
            if p.message_id not in existing_ids 
            and (p.author, p.timestamp) not in existing_author_timestamps
        ]

        if new_posts:
            session.bulk_save_objects(new_posts)
            session.commit()

        return len(new_posts)


def init_db():
    """Creates tables if they do not exist."""
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()