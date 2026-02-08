import sqlite3
import mysql.connector
import os
import sys
import json
from config.database import get_db_connection

SQLITE_DB = 'dpr_database.db'

def get_sqlite_connection():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: SQLite database '{SQLITE_DB}' not found.")
        sys.exit(1)
    return sqlite3.connect(SQLITE_DB)

def migrate_table(sqlite_conn, mysql_conn, table_name, columns, batch_size=100):
    print(f"Migrating table: {table_name}...")
    sqlite_cursor = sqlite_conn.cursor()
    mysql_cursor = mysql_conn.cursor()
    
    # Read from SQLite
    try:
        sqlite_cursor.execute(f"SELECT {', '.join(columns)} FROM {table_name}")
        rows = sqlite_cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"  Skipping {table_name}: {e} (maybe table doesn't exist in SQLite)")
        return

    if not rows:
        print(f"  No data in {table_name}.")
        return

    print(f"  Found {len(rows)} rows. Inserting into MySQL...")
    
    # Prepare MySQL insert query
    placeholders = ', '.join(['%s'] * len(columns))
    query = f"INSERT IGNORE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    
    # Batch insert
    count = 0
    batch = []
    
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            try:
                mysql_cursor.executemany(query, batch)
                mysql_conn.commit()
                count += len(batch)
                batch = []
            except mysql.connector.Error as err:
                print(f"  Error inserting batch: {err}")
                mysql_conn.rollback()
    
    if batch:
        try:
            mysql_cursor.executemany(query, batch)
            mysql_conn.commit()
            count += len(batch)
        except mysql.connector.Error as err:
            print(f"  Error inserting final batch: {err}")
            mysql_conn.rollback()
            
    print(f"  Migrated {count} rows for {table_name}.")

def migrate():
    print("Starting migration from SQLite to MySQL...")
    
    sqlite_conn = get_sqlite_connection()
    try:
        mysql_conn = get_db_connection()
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return

    # Disable FK checks
    cursor = mysql_conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    mysql_conn.commit()
    cursor.close()

    try:
        # Define tables and columns to migrate. Order matters for FKs (though check is disabled, good practice)
        
        # 1. Projects (Independent)
        migrate_table(sqlite_conn, mysql_conn, 'projects', 
                      ['code', 'name', 'manager', 'project_manager_client', 'client', 'contractor', 'report_id_fragment', 'target_completion'])
        
        # 2. Departments (Independent)
        migrate_table(sqlite_conn, mysql_conn, 'departments', ['name'])
        
        # 3. Manpower Designations (Independent)
        migrate_table(sqlite_conn, mysql_conn, 'manpower_designations', ['designation'])
        
        # 4. Equipment Descriptions (Independent)
        migrate_table(sqlite_conn, mysql_conn, 'equipment_descriptions', ['description'])
        
        # 5. App Settings (Independent)
        migrate_table(sqlite_conn, mysql_conn, 'app_settings', ['setting_key', 'setting_value', 'description'])
        
        # 6. Admin Users (Independent)
        migrate_table(sqlite_conn, mysql_conn, 'admin_users', ['username', 'password_hash', 'email'])
        
        # 7. Report Preparers (Depends on Projects)
        migrate_table(sqlite_conn, mysql_conn, 'report_preparers', ['name', 'designation', 'project_code'])
        
        # 8. Contractors (Depends on Projects)
        migrate_table(sqlite_conn, mysql_conn, 'contractors', ['contractor_name', 'project_code', 'contact_person', 'contact_details'])
        
        # 9. Site Managers (Depends on Projects)
        migrate_table(sqlite_conn, mysql_conn, 'site_managers', ['name', 'designation', 'project_code'])
        
        # 10. Project Sections (Depends on Projects)
        migrate_table(sqlite_conn, mysql_conn, 'project_sections', 
                      ['project_code', 'section_id', 'section_name', 'area', 'unit', 'total_qty_planned', 'order_index'])
        
        # 11. Project Activities (Depends on Projects and Sections)
        # We need to map section_id (integer FK) correctly.
        # In SQLite, project_activities might have section_id as integer referencing project_sections.id
        # BUT wait, init_database.py creates project_activities with section_id INTEGER.
        # And inserts using section_db_id.
        # So we can just copy the integer ID if we preserve IDs?
        # BUT we are using AUTO_INCREMENT in insert (NULL id).
        # We did NOT include 'id' in the column list above.
        # MySQL will generate NEW IDs.
        # THIS BREAKS FOREIGN KEYS referencing IDs (like project_activities.section_id -> project_sections.id).
        # We MUST migrate IDs for tables that are referenced by ID.
        
        # Tables referenced by ID: project_sections (referenced by project_activities.section_id)
        # So for project_sections, we MUST include 'id'.
        
        print("Re-migrating project_sections with ID preservation...")
        # Truncate to avoid dupes/conflicts since we just inserted without ID
        cursor = mysql_conn.cursor()
        cursor.execute("TRUNCATE TABLE project_activities") 
        cursor.execute("TRUNCATE TABLE project_sections")
        mysql_conn.commit()
        cursor.close()
        
        migrate_table(sqlite_conn, mysql_conn, 'project_sections', 
                      ['id', 'project_code', 'section_id', 'section_name', 'area', 'unit', 'total_qty_planned', 'order_index'])
        
        # Now migrate Project Activities (which uses section_id FK)
        migrate_table(sqlite_conn, mysql_conn, 'project_activities',
                      ['id', 'project_code', 'section_id', 'activity_description', 'area', 'unit', 'total_qty_planned', 'order_index'])

        # 12. Daily Progress Reports
        migrate_table(sqlite_conn, mysql_conn, 'daily_progress_reports',
                      ['project_code', 'report_date', 'activity_description', 'planned_today', 'achieved_today', 'planned_cumulative', 'achieved_cumulative'])
        
        # 13. Submitted Reports
        migrate_table(sqlite_conn, mysql_conn, 'submitted_reports',
                      ['report_number', 'project_code', 'report_date', 'project_name', 'prepared_by', 'checked_by', 'approved_by', 'submitted_at', 'report_data'])
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nMigration failed: {e}")
    finally:
        # Re-enable FK checks
        cursor = mysql_conn.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        mysql_conn.commit()
        cursor.close()
        
        sqlite_conn.close()
        mysql_conn.close()

if __name__ == '__main__':
    migrate()
