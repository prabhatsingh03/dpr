import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    try:
        # Connect to DB
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "dpr_database"),
            port=int(os.getenv("MYSQL_PORT", 3306))
        )
        cursor = conn.cursor()

        print("Connected to database...")

        # 1. Add section_id column if not exists
        try:
            # Check if column exists
            cursor.execute("SELECT section_id FROM daily_progress_reports LIMIT 1")
            cursor.fetchall() # Consume result
            print("Column 'section_id' already exists.")
        except mysql.connector.Error:
            print("Adding 'section_id' column...")
            cursor.execute("ALTER TABLE daily_progress_reports ADD COLUMN section_id INT DEFAULT 0 AFTER report_date")
        
        # 2. Update unique index
        # First check if the old unique index exists and drop it
        try:
            cursor.execute("SHOW INDEX FROM daily_progress_reports WHERE Key_name = 'unique_report_entry'")
            results = cursor.fetchall()
            if results:
                print("Dropping old unique index...")
                cursor.execute("ALTER TABLE daily_progress_reports DROP INDEX unique_report_entry")
        except mysql.connector.Error as err:
            print(f"Error checking/dropping index: {err}")

        # Add new unique index
        print("Adding new unique index with section_id...")
        try:
             cursor.execute("ALTER TABLE daily_progress_reports ADD UNIQUE KEY unique_report_entry (project_code, report_date, section_id, activity_description)")
             print("New unique index added.")
        except mysql.connector.Error as err:
            print(f"Error adding new index (might already be correct): {err}")

        conn.commit()
        print("Migration completed successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
