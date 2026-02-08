"""
Script to delete all submitted reports for a specific project.
This allows users to re-fill data for those dates.

Usage: python delete_project_reports.py [project_code]
Example: python delete_project_reports.py I-2501F001
"""

from config.database import get_db_connection
import sys

def delete_project_reports(project_code):
    """Delete all submitted reports and daily progress reports for a given project."""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, show what will be deleted
        cursor.execute('''
            SELECT id, report_number, report_date, project_name 
            FROM submitted_reports 
            WHERE project_code = %s
            ORDER BY report_date
        ''', (project_code,))
        
        submitted_reports = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM daily_progress_reports 
            WHERE project_code = %s
        ''', (project_code,))
        
        daily_report_count = cursor.fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"Project Code: {project_code}")
        print(f"{'='*60}")
        
        if not submitted_reports and daily_report_count == 0:
            print(f"No reports found for project '{project_code}'.")
            conn.close()
            return
        
        print(f"\nSubmitted Reports to be deleted: {len(submitted_reports)}")
        print("-" * 60)
        
        if submitted_reports:
            for report in submitted_reports:
                print(f"  ID: {report[0]}, Report#: {report[1]}, Date: {report[2]}")
        else:
            print("  (No submitted reports found)")
        
        print(f"\nDaily Progress Report entries to be deleted: {daily_report_count}")
        print("-" * 60)
        
        # Ask for confirmation
        print("\n⚠️  WARNING: This action cannot be undone!")
        confirmation = input(f"\nType 'DELETE {project_code}' to confirm deletion: ")
        
        if confirmation != f"DELETE {project_code}":
            print("\n❌ Deletion cancelled. No changes were made.")
            conn.close()
            return
        
        # Delete from submitted_reports table
        cursor.execute('''
            DELETE FROM submitted_reports 
            WHERE project_code = %s
        ''', (project_code,))
        deleted_submitted = cursor.rowcount
        
        # Delete from daily_progress_reports table
        cursor.execute('''
            DELETE FROM daily_progress_reports 
            WHERE project_code = %s
        ''', (project_code,))
        deleted_daily = cursor.rowcount
        
        conn.commit()
        
        print(f"\n✅ Deletion successful!")
        print(f"   - Submitted reports deleted: {deleted_submitted}")
        print(f"   - Daily progress entries deleted: {deleted_daily}")
        print(f"\nUsers can now fill data for this project again.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error occurred: {e}")
        raise
    finally:
        conn.close()


def list_all_projects():
    """List all projects and their report counts."""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.code, p.name, 
               (SELECT COUNT(*) FROM submitted_reports sr WHERE sr.project_code = p.code) as submitted_count,
               (SELECT COUNT(*) FROM daily_progress_reports dpr WHERE dpr.project_code = p.code) as daily_count
        FROM projects p
        ORDER BY p.code
    ''')
    
    projects = cursor.fetchall()
    
    print(f"\n{'='*80}")
    print(f"{'Project Code':<15} {'Project Name':<35} {'Submitted':<12} {'Daily Entries':<15}")
    print(f"{'='*80}")
    
    for project in projects:
        print(f"{project[0]:<15} {project[1]:<35} {project[2]:<12} {project[3]:<15}")
    
    print(f"{'='*80}")
    conn.close()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  PROJECT REPORTS DELETION UTILITY")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUsage: python delete_project_reports.py [project_code]")
        print("\nAvailable projects:")
        list_all_projects()
        print("\nExample: python delete_project_reports.py I-2501F001")
        sys.exit(1)
    
    project_code = sys.argv[1]
    
    # Verify project exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code, name FROM projects WHERE code = %s", (project_code,))
    project = cursor.fetchone()
    conn.close()
    
    if not project:
        print(f"\n❌ Error: Project '{project_code}' not found in database.")
        print("\nAvailable projects:")
        list_all_projects()
        sys.exit(1)
    
    print(f"\nProject found: {project[0]} - {project[1]}")
    delete_project_reports(project_code)
