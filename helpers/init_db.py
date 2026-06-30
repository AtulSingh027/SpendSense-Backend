import sys
import os

# Add parent directory to path so we can run as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from configs.db_config import Base, engine, SessionLocal
from models.user import User
from models.category import Category
from models.sms_log import SMSLog
from models.transaction import Transaction
from models.monthly_summary import MonthlySummary
from models.weekly_summary import WeeklySummary


def init_db():
    print("Creating all tables in PostgreSQL...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

    db = SessionLocal()
    try:
        # Check if system categories already exist
        existing = db.query(Category).filter_by(is_system=True).count()
        if existing == 0:
            print("Seeding default categories...")
            system_categories = [
                Category(name="Food", is_system=True),
                Category(name="Travel", is_system=True),
                Category(name="Shopping", is_system=True),
                Category(name="Bills", is_system=True),
                Category(name="Entertainment", is_system=True),
                Category(name="Other", is_system=True),
            ]
            db.add_all(system_categories)
            db.commit()
            print("Default categories seeded successfully!")
        else:
            print("Default categories already present, skipping seed.")
    except Exception as e:
        print(f"Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
