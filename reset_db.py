from app.database import Base, engine
from init_db import init_db


def reset_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped.")
    init_db()


if __name__ == "__main__":
    reset_db()
