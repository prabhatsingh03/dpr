"""
Script to delete a specific report by project code and date.
Requested Use Case: Delete 2026-02-03 Dated Report For Project Code I-2501F001

Usage: python delete_report_by_date.py [project_code] [date]
Example: python delete_report_by_date.py I-2501F001 2026-02-03
"""

import sqlite3
import sys

def delete_report(project_code, report_date):
    """Delete submitted report and daily progress entries for a specific date and project."""
    
    conn = sqlite3.connect('dpr_database.db')
    cursor = conn.cursor()
    
    try:
        # Check for submitted report
        cursor.execute('''
            SELECT id, report_number, report_date, project_name 
            FROM submitted_reports 
            WHERE project_code = ? AND report_date = ?
        ''', (project_code, report_date))
        
        submitted_report = cursor.fetchone()
        
        # Check for daily progress entries
        cursor.execute('''
            SELECT COUNT(*) 
            FROM daily_progress_reports 
            WHERE project_code = ? AND report_date = ?
        ''', (project_code, report_date))
        
        daily_entry_count = cursor.fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"Delete Report Request")
        print(f"Project Code: {project_code}")
        print(f"Report Date : {report_date}")
        print(f"{'='*60}")
        
        if not submitted_report and daily_entry_count == 0:
            print(f"\n❌ No reports found for project '{project_code}' on date '{report_date}'.")
            conn.close()
            return

        if submitted_report:
            print(f"\nFound Submitted Report:")
            print(f"  ID: {submitted_report[0]}")
            print(f"  Report Number: {submitted_report[1]}")
            print(f"  Date: {submitted_report[2]}")
            print(f"  Project Name: {submitted_report[3]}")
        else:
            print(f"\n(No entry in 'submitted_reports' table found for this date)")
            
        print(f"\nFound Daily Progress Entries: {daily_entry_count}")
        
        # Confirmation
        print("\n⚠️  WARNING: This action cannot be undone!")
        confirm_msg = f"DELETE {project_code} {report_date}"
        print(f"To confirm, type exactly: {confirm_msg}")
        confirmation = input("Confirmation: ")
        
        if confirmation != confirm_msg:
            print("\n❌ Deletion cancelled. Input did not match.")
            conn.close()
            return
            
        # Perform Deletion
        deleted_submitted = 0
        if submitted_report:
            cursor.execute('''
                DELETE FROM submitted_reports 
                WHERE project_code = ? AND report_date = ?
            ''', (project_code, report_date))
            deleted_submitted = cursor.rowcount
            
        cursor.execute('''
            DELETE FROM daily_progress_reports 
            WHERE project_code = ? AND report_date = ?
        ''', (project_code, report_date))
        deleted_daily = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Deletion successful!")
        print(f"   - Submitted reports deleted: {deleted_submitted}")
        print(f"   - Daily progress entries deleted: {deleted_daily}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        p_code = sys.argv[1]
        r_date = sys.argv[2]
    else:
        # Default/Interactive mode or Help
        print("\nArgument mode: python delete_report_by_date.py <project_code> <YYYY-MM-DD>")
        print("Running in interactive mode...\n")
        
        # Pre-fill for the requested use case if no args provided, or ask user?
        # The user specifically asked for "I-2501F001" and "2026-02-03".
        # Let's verify if they want to run the specific case or generic.
        # I'll default to the specific case if they just run it, but prompt to confirm.
        
        default_code = "I-2501F001"
        default_date = "2026-02-03"
        
        print(f"Defaulting to requested use case:")
        print(f"  Project: {default_code}")
        print(f"  Date   : {default_date}")
        
        use_default = input(f"Use these defaults? (y/n): ").lower()
        
        if use_default == 'y' or use_default == '':
            p_code = default_code
            r_date = default_date
        else:
            p_code = input("Enter Project Code: ").strip()
            r_date = input("Enter Report Date (YYYY-MM-DD): ").strip()

    if p_code and r_date:
        delete_report(p_code, r_date)
    else:
        print("Invalid input.")
