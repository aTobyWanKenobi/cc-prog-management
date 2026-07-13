import os
import sys

from sqlalchemy import create_engine, text

# Add the project root to sys.path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SQLALCHEMY_DATABASE_URL


def migrate():
    print(f"Connecting to {SQLALCHEMY_DATABASE_URL}...")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

    with engine.connect() as conn:
        print("Checking if old table exists...")
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='pattuglie';"))
        if not result.fetchone():
            print("Table 'pattuglie' does not exist. Nothing to do.")
            return

        print("Creating temporary table pattuglie_new...")
        conn.execute(
            text("""
            CREATE TABLE pattuglie_new (
                id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                capo_pattuglia VARCHAR NOT NULL,
                unita_id INTEGER NOT NULL,
                current_score INTEGER NOT NULL,
                PRIMARY KEY (id),
                FOREIGN KEY(unita_id) REFERENCES unita (id),
                CONSTRAINT uq_pattuglia_name_unita UNIQUE (name, unita_id)
            )
        """)
        )

        print("Copying data from pattuglie to pattuglie_new...")
        conn.execute(
            text("""
            INSERT INTO pattuglie_new (id, name, capo_pattuglia, unita_id, current_score)
            SELECT id, name, capo_pattuglia, unita_id, current_score FROM pattuglie
        """)
        )

        print("Dropping old pattuglie table...")
        # Since completions uses Foreign Keys, PRAGMA foreign_keys=OFF is usually default in sqlite during such ops,
        # but just in case, we are in an environment where we can just drop it.
        # SQLAlchemy sqlite by default has FK pragmas off unless specified.
        conn.execute(text("PRAGMA foreign_keys=OFF;"))
        conn.execute(text("DROP TABLE pattuglie;"))

        print("Renaming pattuglie_new to pattuglie...")
        conn.execute(text("ALTER TABLE pattuglie_new RENAME TO pattuglie;"))

        print("Creating indexes...")
        conn.execute(text("CREATE INDEX ix_pattuglie_id ON pattuglie (id);"))
        conn.execute(text("CREATE INDEX ix_pattuglie_name ON pattuglie (name);"))

        conn.commit()
        print("Migration complete!")


if __name__ == "__main__":
    migrate()
