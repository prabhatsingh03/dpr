from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import hashlib
import os
import asyncio
from datetime import datetime, timedelta
import json
from config.database import get_db_connection
import mysql.connector

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')


# Notifications storage (JSON file) and helpers
NOTIFICATIONS_FILE = 'notifications.json'

def _load_notifications():
    try:
        if os.path.exists(NOTIFICATIONS_FILE):
            with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []
    except Exception:
        return []

def _save_notifications(items):
    try:
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)
    except Exception:
        pass

def _prune_notifications(hours: int = 48):
    items = _load_notifications()
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    def parse_dt(s):
        try:
            # stored as ISO with 'Z'
            if s.endswith('Z'):
                s = s[:-1]
            return datetime.fromisoformat(s)
        except Exception:
            return None
    filtered = []
    for it in items:
        created_at = parse_dt(it.get('created_at', ''))
        if created_at and created_at >= cutoff:
            filtered.append(it)
    if len(filtered) != len(items):
        _save_notifications(filtered)
    return filtered

def add_notification(message: str, payload: dict | None = None):
    items = _prune_notifications(48)
    notification = {
        'id': int(datetime.utcnow().timestamp() * 1000),
        'message': message,
        'created_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z',
        'payload': payload or {}
    }
    items.append(notification)
    # keep newest first for convenience
    items.sort(key=lambda x: x.get('id', 0), reverse=True)
    _save_notifications(items)
    return notification

@app.route('/')
def index():
    """Main form route"""
    return render_template('index.html')

@app.route('/api/projects')
def get_projects():
    """API endpoint to get all projects"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM projects ORDER BY code')
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    
    projects_list = []
    for project in projects:
        projects_list.append({
            'code': project['code'],
            'name': project['name'],
            'manager': project['manager'],
            'projectManagerClient': project['project_manager_client'],
            'client': project['client'],
            'contractor': project['contractor'],
            'reportIdFragment': project['report_id_fragment'],
            'targetCompletion': project['target_completion']
        })
    
    return jsonify(projects_list)

@app.route('/api/report-preparers')
def get_report_preparers():
    """API endpoint to get report preparers for a specific project"""
    project_code = request.args.get('project_code')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if project_code:
        cursor.execute('''
            SELECT name, designation FROM report_preparers 
            WHERE project_code = %s OR project_code IS NULL 
            ORDER BY name
        ''', (project_code,))
        preparers = cursor.fetchall()
    else:
        cursor.execute('SELECT name, designation FROM report_preparers ORDER BY name')
        preparers = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([{'name': p['name'], 'designation': p['designation']} for p in preparers])

@app.route('/api/site-managers')
def get_site_managers():
    """API endpoint to get site managers for a specific project"""
    project_code = request.args.get('project_code')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if project_code:
        cursor.execute('''
            SELECT name, designation FROM site_managers 
            WHERE project_code = %s OR project_code IS NULL 
            ORDER BY name
        ''', (project_code,))
        managers = cursor.fetchall()
    else:
        cursor.execute('SELECT name, designation FROM site_managers ORDER BY name')
        managers = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([{'name': m['name'], 'designation': m['designation']} for m in managers])

@app.route('/api/departments')
def get_departments():
    """API endpoint to get all departments"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT name FROM departments ORDER BY name')

    departments = cursor.fetchall()
    conn.close()
    
    return jsonify([dept['name'] for dept in departments])

@app.route('/api/contractors')
def get_contractors():
    """API endpoint to get contractors for a specific project"""
    project_code = request.args.get('project_code')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if project_code:
        cursor.execute('''
            SELECT contractor_name, contact_person, contact_details FROM contractors 
            WHERE project_code = %s OR project_code IS NULL 
            ORDER BY contractor_name
        ''', (project_code,))
        contractors = cursor.fetchall()
    else:
        cursor.execute('SELECT contractor_name, contact_person, contact_details FROM contractors ORDER BY contractor_name')
        contractors = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([{
        'name': c['contractor_name'], 
        'contact_person': c['contact_person'],
        'contact_details': c['contact_details']
    } for c in contractors])

@app.route('/api/manpower-designations')
def get_manpower_designations():
    """API endpoint to get all manpower designations"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT designation FROM manpower_designations ORDER BY designation')

    designations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify([designation['designation'] for designation in designations])

@app.route('/api/equipment-descriptions')
def get_equipment_descriptions():
    """API endpoint to get all equipment descriptions"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT description FROM equipment_descriptions ORDER BY description')

    equipment = cursor.fetchall()
    conn.close()
    
    return jsonify([equip['description'] for equip in equipment])

# Legacy activity endpoints removed - now using project-specific endpoints

@app.route('/api/project-sections')
def get_project_sections():
    """API endpoint to get sections for a specific project"""
    project_code = request.args.get('project_code')
    
    if not project_code:
        return jsonify({'error': 'project_code is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT * FROM project_sections 
        WHERE project_code = %s 
        ORDER BY section_name
    ''', (project_code,))
    sections = cursor.fetchall()
    cursor.close()
    conn.close()
    
    sections_list = []
    for section in sections:
        sections_list.append({
            'sectionId': section['section_id'],
            'sectionName': section['section_name'],
            'area': section['area'],
            'unit': section['unit'],
            'totalQtyPlanned': section['total_qty_planned']
        })
    
    return jsonify(sections_list)

@app.route('/api/project-activities')
def get_project_activities():
    """API endpoint to get activities for a specific project and section"""
    try:
        project_code = request.args.get('project_code')
        section_identifier = request.args.get('section_id')  # may be string identifier like "concrete" or numeric id

        if not project_code:
            return jsonify({'error': 'project_code is required'}), 400

        conn = get_db_connection()

        # Helper: map provided section identifier (string or numeric) to section DB id and canonical string id
        def resolve_section(project: str, raw_identifier: str):
            if raw_identifier is None:
                return None
            section_row = None
            # Try match by string section_id first
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT id, section_id FROM project_sections
                WHERE project_code = %s AND section_id = %s
            ''', (project, raw_identifier))
            section_row = cursor.fetchone()
            
            if section_row:
                cursor.close()
                return section_row
            
            # If not found, attempt to interpret as integer primary key
            try:
                int_id = int(raw_identifier)
                cursor.execute('''
                    SELECT id, section_id FROM project_sections
                    WHERE project_code = %s AND id = %s
                ''', (project, int_id))
                section_row = cursor.fetchone()
                cursor.close()
                return section_row
            except Exception:
                cursor.close()
                return None

        if section_identifier:
            # Resolve to DB id
            section_row = resolve_section(project_code, section_identifier)
            if not section_row:
                cursor.close()
                conn.close()
                return jsonify({'error': f'section "{section_identifier}" not found for project {project_code}'}), 404

            section_db_id = section_row['id']
            # Get activities for this section id
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT activity_description, area, unit, total_qty_planned
                FROM project_activities
                WHERE project_code = %s AND section_id = %s
                ORDER BY activity_description
            ''', (project_code, section_db_id))
            activities = cursor.fetchall()
            conn.close()

            activities_list = []
            for activity in activities:
                activities_list.append({
                    'description': activity['activity_description'],
                    'area': activity['area'] if activity['area'] else '',
                    'unit': activity['unit'],
                    'totalQty': activity['total_qty_planned']
                })
            return jsonify(activities_list)
        else:
            # Get all activities for the project, grouped by the canonical string section_id
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT ps.section_id AS section_identifier,
                       pa.activity_description, pa.area, pa.unit, pa.total_qty_planned
                FROM project_activities pa
                JOIN project_sections ps ON pa.section_id = ps.id
                WHERE pa.project_code = %s
                ORDER BY ps.section_id, pa.activity_description
            ''', (project_code,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            activities_by_section = {}
            for row in rows:
                sec_key = row['section_identifier']
                if sec_key not in activities_by_section:
                    activities_by_section[sec_key] = []
                activities_by_section[sec_key].append({
                    'description': row['activity_description'],
                    'area': row['area'] if row['area'] else '',
                    'unit': row['unit'],
                    'totalQty': row['total_qty_planned']
                })
            return jsonify(activities_by_section)
    except Exception as e:
        print(f"Error in project-activities API: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/add-project-section', methods=['POST'])
def api_add_project_section():
    """Add a new section for a project dynamically"""
    try:
        data = request.get_json()
        project_code = data.get('project_code')
        section_name = data.get('section_name')
        
        print(f"API received request to add section: '{section_name}' for project: '{project_code}'")
        
        if not project_code or not section_name:
            return jsonify({'error': 'project_code and section_name are required'}), 400
        
        conn = get_db_connection()
        
        # Generate section_id from section_name: remove spaces and convert to lowercase
        section_id = section_name.replace(' ', '').lower()
        
        # Check if section already exists (check both section_id and section_name)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT id FROM project_sections 
            WHERE project_code = %s AND (section_id = %s OR section_name = %s)
        ''', (project_code, section_id, section_name))
        existing_section = cursor.fetchone()
        
        if existing_section:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Section already exists', 'section_id': existing_section['id']}), 409
        
        # Get the next order index
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT MAX(order_index) as max_order FROM project_sections 
            WHERE project_code = %s
        ''', (project_code,))
        max_order = cursor.fetchone()
        
        next_order = (max_order['max_order'] or 0) + 1
        
        # Insert new section
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            INSERT INTO project_sections (project_code, section_id, section_name, order_index)
            VALUES (%s, %s, %s, %s)
        ''', (project_code, section_id, section_name, next_order))
        
        db_section_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'section_id': db_section_id,
            'section_identifier': section_id,
            'section_name': section_name,
            'order_index': next_order,
            'message': f'Section "{section_name}" added successfully'
        })
        
    except Exception as e:
        print(f"Error adding project section: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/add-project-activity', methods=['POST'])
def api_add_project_activity():
    """Add a new activity for a project section dynamically"""
    try:
        data = request.get_json()
        project_code = data.get('project_code')
        section_name = data.get('section_name')
        activity_description = data.get('activity_description')
        unit = data.get('unit', '')
        total_qty = data.get('total_qty', 0)
        
        if not project_code or not section_name or not activity_description:
            return jsonify({'error': 'project_code, section_name, and activity_description are required'}), 400
        
        conn = get_db_connection()
        
        # Get section ID - try both section_name and section_id fields
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT id, section_id FROM project_sections 
            WHERE project_code = %s AND (section_name = %s OR section_id = %s)
        ''', (project_code, section_name, section_name))
        section = cursor.fetchone()
        
        if not section:
            conn.close()
            return jsonify({'error': f'Section "{section_name}" not found for project {project_code}'}), 404
        
        # Use the database primary key ID for foreign key reference
        section_db_id = section['id']
        
        # Check if activity already exists in this section
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT id FROM project_activities 
            WHERE project_code = %s AND section_id = %s AND activity_description = %s
        ''', (project_code, section_db_id, activity_description))
        existing_activity = cursor.fetchone()
        
        if existing_activity:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Activity already exists', 'activity_id': existing_activity['id']}), 409
        
        # Get the next order index for this section
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT MAX(order_index) as max_order FROM project_activities 
            WHERE section_id = %s
        ''', (section_db_id,))
        max_order = cursor.fetchone()
        
        next_order = (max_order['max_order'] or 0) + 1
        
        # Insert new activity
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            INSERT INTO project_activities (project_code, section_id, activity_description, area, unit, total_qty_planned, order_index)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (project_code, section_db_id, activity_description, data.get('area', ''), unit, total_qty, next_order))
        
        activity_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'activity_id': activity_id,
            'section_id': section_db_id,
            'description': activity_description,
            'unit': unit,
            'total_qty': total_qty,
            'order_index': next_order,
            'message': f'Activity "{activity_description}" added successfully'
        })
        
    except Exception as e:
        print(f"Error adding project activity: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/update-project-activity', methods=['POST'])
def api_update_project_activity():
    """Update an existing activity for a project section dynamically"""
    try:
        data = request.get_json()
        project_code = data.get('project_code')
        section_name = data.get('section_name')
        activity_description = data.get('activity_description')
        area = data.get('area', '')
        unit = data.get('unit', '')
        total_qty = data.get('total_qty', 0)
        
        if not project_code or not section_name or not activity_description:
            return jsonify({'error': 'project_code, section_name, and activity_description are required'}), 400
        
        conn = get_db_connection()
        
        # Find the activity to update
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT pa.id FROM project_activities pa
            JOIN project_sections ps ON pa.section_id = ps.id
            WHERE pa.project_code = %s AND ps.section_name = %s AND pa.activity_description = %s
        ''', (project_code, section_name, activity_description))
        activity = cursor.fetchone()
        
        if not activity:
            conn.close()
            return jsonify({'error': f'Activity "{activity_description}" not found in section "{section_name}" for project {project_code}'}), 404
        
        # Update the activity
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE project_activities 
            SET area = %s, unit = %s, total_qty_planned = %s
            WHERE id = %s
        ''', (area, unit, total_qty, activity['id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'activity_id': activity['id'],
            'description': activity_description,
            'area': area,
            'unit': unit,
            'total_qty': total_qty,
            'message': f'Activity "{activity_description}" updated successfully'
        })
        
    except Exception as e:
        print(f"Error updating project activity: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# Admin Authentication Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login route"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Hash the password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            'SELECT * FROM admin_users WHERE username = %s AND password_hash = %s',
            (username, password_hash)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            session['admin_user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout route"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    session.pop('admin_user_id', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

def admin_required(f):
    """Decorator to require admin authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in to access the admin panel', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin Dashboard Routes
@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard route"""
    conn = get_db_connection()
    
    # Get counts for dashboard
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT COUNT(*) as count FROM projects')

    project_count = cursor.fetchone()['count']
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT COUNT(*) as count FROM report_preparers')

    preparers_count = cursor.fetchone()['count']
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT COUNT(*) as count FROM site_managers')

    managers_count = cursor.fetchone()['count']
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT COUNT(*) as count FROM departments')

    department_count = cursor.fetchone()['count']
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT COUNT(*) as count FROM contractors')

    contractor_count = cursor.fetchone()['count']
    
    cursor.close()
    conn.close()
    
    stats = {
        'projects': project_count,
        'report_preparers': preparers_count,
        'site_managers': managers_count,
        'departments': department_count,
        'contractors': contractor_count
    }
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/view-reports', methods=['GET'])
@admin_required
def admin_view_reports():
    """Admin page to view submitted reports with filters and print to PDF."""
    project_code = request.args.get('project_code', '').strip()
    report_date = request.args.get('report_date', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    projects = cursor.fetchall()

    reports = []
    if project_code or report_date:
        # Build dynamic where clause
        where = []
        params = []
        if project_code:
            where.append('sr.project_code = %s')
            params.append(project_code)
        if report_date:
            where.append('sr.report_date = %s')
            params.append(report_date)

        where_sql = ' WHERE ' + ' AND '.join(where) if where else ''
        query = f'''
            SELECT sr.*, p.name as project_name,
                   p.manager as project_manager_contractor,
                   p.project_manager_client as project_manager_client,
                   p.target_completion as target_completion,
                   p.client as project_client,
                   p.contractor as project_contractor
            FROM submitted_reports sr
            JOIN projects p ON sr.project_code = p.code
            {where_sql}
            ORDER BY sr.report_date DESC, sr.report_number DESC
        '''
        cursor = conn.cursor(dictionary=True)

        cursor.execute(query, tuple(params))

        reports = cursor.fetchall()

    conn.close()

    # Parse JSON report_data for display
    parsed_reports = []
    for r in reports:
        try:
            data = json.loads(r['report_data']) if r['report_data'] else {}
        except Exception:
            data = {}
        parsed_reports.append({
            'id': r['id'],
            'report_number': r['report_number'],
            'project_code': r['project_code'],
            'project_name': r['project_name'],
            'report_date': str(r['report_date']) if r['report_date'] else '',
            'prepared_by': (r['prepared_by'] or '') if 'prepared_by' in r.keys() else '',
            'checked_by': (r['checked_by'] or '') if 'checked_by' in r.keys() else '',
            'approved_by': (r['approved_by'] or '') if 'approved_by' in r.keys() else '',
            'submitted_at': r['submitted_at'],
            'project_manager_contractor': r['project_manager_contractor'] if 'project_manager_contractor' in r.keys() else '',
            'project_manager_client': r['project_manager_client'] if 'project_manager_client' in r.keys() else '',
            'target_completion': r['target_completion'] if 'target_completion' in r.keys() else '',
            'project_client': r['project_client'] if 'project_client' in r.keys() else '',
            'project_contractor': r['project_contractor'] if 'project_contractor' in r.keys() else '',
            'data': data
        })

    return render_template(
        'admin_view_reports.html', 
        projects=projects, 
        selected_project=project_code, 
        selected_date=report_date,
        reports=parsed_reports,
        show_admin_links=True
    )

# Public view of reports
@app.route('/view-reports', methods=['GET'])
def public_view_reports():
    """Public page to view submitted reports with filters and print to PDF."""
    project_code = request.args.get('project_code', '').strip()
    report_date = request.args.get('report_date', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    projects = cursor.fetchall()

    reports = []
    if project_code or report_date:
        where = []
        params = []
        if project_code:
            where.append('sr.project_code = %s')
            params.append(project_code)
        if report_date:
            where.append('sr.report_date = %s')
            params.append(report_date)
        where_sql = ' WHERE ' + ' AND '.join(where) if where else ''
        query = f'''
            SELECT sr.*, p.name as project_name,
                   p.manager as project_manager_contractor,
                   p.project_manager_client as project_manager_client,
                   p.target_completion as target_completion,
                   p.client as project_client,
                   p.contractor as project_contractor
            FROM submitted_reports sr
            JOIN projects p ON sr.project_code = p.code
            {where_sql}
            ORDER BY sr.report_date DESC, sr.report_number DESC
        '''
        cursor = conn.cursor(dictionary=True)

        cursor.execute(query, tuple(params))

        reports = cursor.fetchall()
    conn.close()

    parsed_reports = []
    for r in reports:
        try:
            data = json.loads(r['report_data']) if r['report_data'] else {}
        except Exception:
            data = {}
        parsed_reports.append({
            'id': r['id'],
            'report_number': r['report_number'],
            'project_code': r['project_code'],
            'project_name': r['project_name'],
            'report_date': str(r['report_date']) if r['report_date'] else '',
            'prepared_by': (r['prepared_by'] or '') if 'prepared_by' in r.keys() else '',
            'checked_by': (r['checked_by'] or '') if 'checked_by' in r.keys() else '',
            'approved_by': (r['approved_by'] or '') if 'approved_by' in r.keys() else '',
            'submitted_at': r['submitted_at'],
            'project_manager_contractor': r['project_manager_contractor'] if 'project_manager_contractor' in r.keys() else '',
            'project_manager_client': r['project_manager_client'] if 'project_manager_client' in r.keys() else '',
            'target_completion': r['target_completion'] if 'target_completion' in r.keys() else '',
            'project_client': r['project_client'] if 'project_client' in r.keys() else '',
            'project_contractor': r['project_contractor'] if 'project_contractor' in r.keys() else '',
            'data': data
        })

    return render_template(
        'admin_view_reports.html', 
        projects=projects, 
        selected_project=project_code, 
        selected_date=report_date,
        reports=parsed_reports,
        show_admin_links=False
    )

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get notifications within the last N hours (default 48). Also prunes expired items."""
    try:
        hours = int(request.args.get('hours', '48'))
    except Exception:
        hours = 48
    items = _prune_notifications(hours)
    # Sort newest first
    items = sorted(items, key=lambda x: x.get('id', 0), reverse=True)
    return jsonify({'notifications': items, 'count': len(items)})

@app.route('/admin/projects')
@admin_required
def admin_projects():
    """Admin projects management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM projects ORDER BY code')

    projects = cursor.fetchall()
    conn.close()
    
    return render_template('admin_projects.html', projects=projects)

@app.route('/admin/projects/add', methods=['POST'])
@admin_required
def add_project():
    """Add new project"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO projects (code, name, manager, project_manager_client, client, contractor, report_id_fragment, target_completion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['code'], data['name'], data['manager'], data['projectManagerClient'],
            data['client'], data['contractor'], data['reportIdFragment'], data['targetCompletion']
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Project added successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Project code already exists'})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/projects/update/<int:project_id>', methods=['POST'])
@admin_required
def update_project(project_id):
    """Update existing project"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE projects 
        SET code=%s, name=%s, manager=%s, project_manager_client=%s, client=%s, contractor=%s, report_id_fragment=%s, target_completion=%s
        WHERE id=%s
    ''', (
        data['code'], data['name'], data['manager'], data['projectManagerClient'],
        data['client'], data['contractor'], data['reportIdFragment'], data['targetCompletion'], project_id
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project updated successfully'})

@app.route('/admin/projects/delete/<int:project_id>', methods=['DELETE'])
@admin_required
def delete_project(project_id):
    """Delete project"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM projects WHERE id = %s', (project_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project deleted successfully'})

@app.route('/admin/staff')
@admin_required
def admin_staff():
    """Admin staff management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM staff ORDER BY name')

    staff = cursor.fetchall()
    conn.close()
    
    return render_template('admin_staff.html', staff=staff)

# Manpower Designation Management Routes
@app.route('/admin/manpower-designations')
@admin_required
def admin_manpower_designations():
    """Admin manpower designations management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM manpower_designations ORDER BY designation')

    designations = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_manpower_designations.html', designations=designations)

@app.route('/admin/manpower-designations/add', methods=['POST'])
@admin_required
def add_manpower_designation():
    """Add new manpower designation"""
    data = request.get_json()
    
    if not data or 'designation' not in data or not data['designation'].strip():
        return jsonify({'success': False, 'message': 'Designation name is required'})
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('INSERT INTO manpower_designations (designation) VALUES (%s)',
                    (data['designation'].strip(),))
        conn.commit()
        return jsonify({'success': True, 'message': 'Designation added successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Designation already exists'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        conn.close()

@app.route('/admin/manpower-designations/update/<int:id>', methods=['POST'])
@admin_required
def update_manpower_designation(id):
    """Update existing manpower designation"""
    data = request.get_json()
    
    if not data or 'designation' not in data or not data['designation'].strip():
        return jsonify({'success': False, 'message': 'Designation name is required'})
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('UPDATE manpower_designations SET designation=%s WHERE id=%s',
                    (data['designation'].strip(), id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Designation updated successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Designation already exists'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        conn.close()

@app.route('/admin/manpower-designations/delete/<int:id>', methods=['DELETE'])
@admin_required
def delete_manpower_designation(id):
    """Delete manpower designation"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('DELETE FROM manpower_designations WHERE id = %s', (id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Designation deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

# Equipment Description Management Routes
@app.route('/admin/equipment-descriptions')
@admin_required
def admin_equipment_descriptions():
    """Admin equipment descriptions management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM equipment_descriptions ORDER BY description')

    descriptions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_equipment_descriptions.html', descriptions=descriptions)

@app.route('/admin/equipment-descriptions/add', methods=['POST'])
@admin_required
def add_equipment_description():
    """Add new equipment description"""
    data = request.get_json()
    
    if not data or 'description' not in data or not data['description'].strip():
        return jsonify({'success': False, 'message': 'Description is required'})
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('INSERT INTO equipment_descriptions (description) VALUES (%s)',
                    (data['description'].strip(),))
        conn.commit()
        return jsonify({'success': True, 'message': 'Equipment description added successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Equipment description already exists'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        conn.close()

@app.route('/admin/equipment-descriptions/update/<int:id>', methods=['POST'])
@admin_required
def update_equipment_description(id):
    """Update existing equipment description"""
    data = request.get_json()
    
    if not data or 'description' not in data or not data['description'].strip():
        return jsonify({'success': False, 'message': 'Description is required'})
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('UPDATE equipment_descriptions SET description=%s WHERE id=%s',
                    (data['description'].strip(), id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Equipment description updated successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Equipment description already exists'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        conn.close()

@app.route('/admin/equipment-descriptions/delete/<int:id>', methods=['DELETE'])
@admin_required
def delete_equipment_description(id):
    """Delete equipment description"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('DELETE FROM equipment_descriptions WHERE id = %s', (id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Equipment description deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/staff/add', methods=['POST'])
@admin_required
def add_staff():
    """Add new staff member"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('INSERT INTO staff (name, designation) VALUES (%s, %s)', (data['name'], data['designation']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Staff member added successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Staff member name already exists'})
    finally:
        conn.close()

@app.route('/admin/staff/update/<int:staff_id>', methods=['POST'])
@admin_required
def update_staff(staff_id):
    """Update existing staff member"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('UPDATE staff SET name=%s, designation=%s WHERE id=%s', (data['name'], data['designation'], staff_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Staff member updated successfully'})

@app.route('/admin/staff/delete/<int:staff_id>', methods=['DELETE'])
@admin_required
def delete_staff(staff_id):
    """Delete staff member"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM staff WHERE id = %s', (staff_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Staff member deleted successfully'})

@app.route('/admin/departments')
@admin_required
def admin_departments():
    """Admin departments management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT * FROM departments ORDER BY name')

    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_departments.html', departments=departments)

@app.route('/admin/departments/add', methods=['POST'])
@admin_required
def add_department():
    """Add new department"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('INSERT INTO departments (name) VALUES (%s)', (data['name'],))
        conn.commit()
        return jsonify({'success': True, 'message': 'Department added successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Department name already exists'})
    finally:
        conn.close()

@app.route('/admin/departments/update/<int:dept_id>', methods=['POST'])
@admin_required
def update_department(dept_id):
    """Update existing department"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('UPDATE departments SET name=%s WHERE id=%s', (data['name'], dept_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Department updated successfully'})

@app.route('/admin/departments/delete/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    """Delete department"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM departments WHERE id = %s', (dept_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Department deleted successfully'})

# Old contractors admin routes removed - now using role-based contractors management

# Legacy activity admin routes removed - now using project-specific routes

# Admin routes for project-specific sections and activities
@app.route('/admin/project-sections')
@admin_required
def admin_project_sections():
    """Admin project sections management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT ps.*, p.name as project_name 
        FROM project_sections ps
        JOIN projects p ON ps.project_code = p.code
        ORDER BY ps.project_code, ps.section_name
    ''')
    sections = cursor.fetchall()
    
    cursor = conn.cursor(dictionary=True)

    
    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    
    projects = cursor.fetchall()
    conn.close()
    
    return render_template('admin_project_sections.html', sections=sections, projects=projects)

@app.route('/admin/project-sections/add', methods=['POST'])
@admin_required
def add_project_section():
    """Add new project section"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO project_sections (project_code, section_id, section_name, area, unit, total_qty_planned)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            data['projectCode'], data['sectionId'], data['sectionName'],
            data['area'], data['unit'], data['totalQtyPlanned']
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Project section added successfully'})
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Section already exists for this project'})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/project-sections/update/<int:section_id>', methods=['POST'])
@admin_required
def update_project_section(section_id):
    """Update existing project section"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE project_sections 
        SET section_id=%s, section_name=%s, area=%s, unit=%s, total_qty_planned=%s
        WHERE id=%s
    ''', (
        data['sectionId'], data['sectionName'], data['area'], 
        data['unit'], data['totalQtyPlanned'], section_id
    ))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project section updated successfully'})

@app.route('/admin/project-sections/delete/<int:section_id>', methods=['DELETE'])
@admin_required
def delete_project_section(section_id):
    """Delete project section"""
    conn = get_db_connection()
    # First delete associated activities
    cursor = conn.cursor()

    cursor.execute('DELETE FROM project_activities WHERE project_code = (SELECT project_code FROM project_sections WHERE id = %s) AND section_id = (SELECT section_id FROM project_sections WHERE id = %s)', (section_id, section_id))
    # Then delete section
    cursor = conn.cursor()

    cursor.execute('DELETE FROM project_sections WHERE id = %s', (section_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project section deleted successfully'})

@app.route('/admin/project-activities')
@admin_required
def admin_project_activities():
    """Admin project activities management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT pa.*, p.name as project_name, ps.section_name
        FROM project_activities pa
        JOIN projects p ON pa.project_code = p.code
        JOIN project_sections ps ON pa.section_id = ps.id
        ORDER BY pa.project_code, pa.section_id, pa.activity_description
    ''')
    activities = cursor.fetchall()
    
    cursor = conn.cursor(dictionary=True)

    
    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    
    projects = cursor.fetchall()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT id, project_code, section_id, section_name FROM project_sections ORDER BY project_code, section_name')

    sections_rows = cursor.fetchall()
    conn.close()
    
    # Convert Row objects to dictionaries for JSON serialization
    sections = []
    for section in sections_rows:
        sections.append({
            'id': section['id'],  # Add ID for correct foreign key reference
            'project_code': section['project_code'],
            'section_id': section['section_id'],
            'section_name': section['section_name']
        })
    
    return render_template('admin_project_activities.html', activities=activities, projects=projects, sections=sections)

@app.route('/admin/project-activities/add', methods=['POST'])
@admin_required
def add_project_activity():
    """Add new project activity"""
    data = request.get_json()
    
    conn = get_db_connection()
    
    # Get the next order index for this section
    max_order = None
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT MAX(order_index) as max_order FROM project_activities 
        WHERE section_id = %s
    ''', (data['sectionId'],))
    max_order = cursor.fetchone()
    
    next_order = (max_order['max_order'] or 0) + 1
    
    try:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO project_activities (project_code, section_id, activity_description, area, unit, total_qty_planned, order_index)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            data['projectCode'], data['sectionId'], data['activityDescription'],
            data['area'], data['unit'], data['totalQtyPlanned'], next_order
        ))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Project activity added successfully'})
    except mysql.connector.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': 'Activity already exists in this section'}), 409
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/admin/project-activities/update/<int:activity_id>', methods=['POST'])
@admin_required
def update_project_activity(activity_id):
    """Update existing project activity"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE project_activities 
        SET section_id=%s, activity_description=%s, area=%s, unit=%s, total_qty_planned=%s
        WHERE id=%s
    ''', (
        data['sectionId'], data['activityDescription'], data['area'],
        data['unit'], data['totalQtyPlanned'], activity_id
    ))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project activity updated successfully'})

@app.route('/admin/project-activities/delete/<int:activity_id>', methods=['DELETE'])
@admin_required
def delete_project_activity(activity_id):
    """Delete project activity"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM project_activities WHERE id = %s', (activity_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project activity deleted successfully'})

# Admin routes for role-based staff management
@app.route('/admin/report-preparers')
@admin_required
def admin_report_preparers():
    """Admin report preparers management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT rp.*, p.name as project_name 
        FROM report_preparers rp
        LEFT JOIN projects p ON rp.project_code = p.code
        ORDER BY rp.project_code, rp.name
    ''')
    preparers = cursor.fetchall()
    
    cursor = conn.cursor(dictionary=True)

    
    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    
    projects = cursor.fetchall()
    conn.close()
    
    return render_template('admin_report_preparers.html', preparers=preparers, projects=projects)

@app.route('/admin/contractors')
@admin_required
def admin_contractors():
    """Admin contractors management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT c.*, p.name as project_name 
        FROM contractors c
        LEFT JOIN projects p ON c.project_code = p.code
        ORDER BY c.project_code, c.contractor_name
    ''')
    contractors = cursor.fetchall()
    
    cursor = conn.cursor(dictionary=True)

    
    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_contractors.html', contractors=contractors, projects=projects)

@app.route('/admin/site-managers')
@admin_required
def admin_site_managers():
    """Admin site managers management"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT sm.*, p.name as project_name 
        FROM site_managers sm
        LEFT JOIN projects p ON sm.project_code = p.code
        ORDER BY sm.project_code, sm.name
    ''')
    managers = cursor.fetchall()
    
    cursor = conn.cursor(dictionary=True)

    
    cursor.execute('SELECT code, name FROM projects ORDER BY code')

    
    projects = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_site_managers.html', managers=managers, projects=projects)

# CRUD routes for role-based staff management
@app.route('/admin/report-preparers/add', methods=['POST'])
@admin_required
def add_report_preparer():
    """Add new report preparer"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Global unique by name
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT 1 FROM report_preparers WHERE name = %s', (data['name'],))

        existing = cursor.fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Report preparer name must be unique'}), 409
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO report_preparers (name, designation, project_code) 
            VALUES (%s, %s, %s)
        ''', (data['name'], data['designation'], data.get('project_code')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Report preparer added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/report-preparers/update/<int:preparer_id>', methods=['POST'])
@admin_required
def update_report_preparer(preparer_id):
    """Update existing report preparer"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Enforce unique name on update
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT 1 FROM report_preparers WHERE name = %s AND id <> %s', (data['name'], preparer_id))

        existing = cursor.fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Report preparer name must be unique'}), 409
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE report_preparers 
            SET name=%s, designation=%s, project_code=%s 
            WHERE id=%s
        ''', (data['name'], data['designation'], data.get('project_code'), preparer_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Report preparer updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/report-preparers/delete/<int:preparer_id>', methods=['DELETE'])
@admin_required
def delete_report_preparer(preparer_id):
    """Delete report preparer"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM report_preparers WHERE id = %s', (preparer_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Report preparer deleted successfully'})

@app.route('/admin/contractors/add', methods=['POST'])
@admin_required
def add_contractor():
    """Add new contractor"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Enforce unique contractor per project
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT 1 FROM contractors WHERE project_code = %s AND contractor_name = %s
        ''', (data.get('project_code'), data['contractor_name']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Contractor already exists for this project'}), 409
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO contractors (contractor_name, project_code, contact_person, contact_details) 
            VALUES (%s, %s, %s, %s)
        ''', (data['contractor_name'], data.get('project_code'), data.get('contact_person', ''), data.get('contact_details', '')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Contractor added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/contractors/update/<int:contractor_id>', methods=['POST'])
@admin_required
def update_contractor(contractor_id):
    """Update existing contractor"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        # Check uniqueness on update
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT 1 FROM contractors 
            WHERE project_code = %s AND contractor_name = %s AND id <> %s
        ''', (data.get('project_code'), data['contractor_name'], contractor_id))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Contractor already exists for this project'}), 409
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE contractors 
            SET contractor_name=%s, project_code=%s, contact_person=%s, contact_details=%s 
            WHERE id=%s
        ''', (data['contractor_name'], data.get('project_code'), data.get('contact_person', ''), data.get('contact_details', ''), contractor_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Contractor updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/contractors/delete/<int:contractor_id>', methods=['DELETE'])
@admin_required
def delete_contractor(contractor_id):
    """Delete contractor"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM contractors WHERE id = %s', (contractor_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Contractor deleted successfully'})

@app.route('/admin/site-managers/add', methods=['POST'])
@admin_required
def add_site_manager():
    """Add new site manager"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT 1 FROM site_managers WHERE name = %s', (data['name'],))

        existing = cursor.fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Site manager name must be unique'}), 409
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO site_managers (name, designation, project_code) 
            VALUES (%s, %s, %s)
        ''', (data['name'], data['designation'], data.get('project_code')))
        conn.commit()
        return jsonify({'success': True, 'message': 'Site manager added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/site-managers/update/<int:manager_id>', methods=['POST'])
@admin_required
def update_site_manager(manager_id):
    """Update existing site manager"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute('SELECT 1 FROM site_managers WHERE name = %s AND id <> %s', (data['name'], manager_id))

        existing = cursor.fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Site manager name must be unique'}), 409
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE site_managers 
            SET name=%s, designation=%s, project_code=%s 
            WHERE id=%s
        ''', (data['name'], data['designation'], data.get('project_code'), manager_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Site manager updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/admin/site-managers/delete/<int:manager_id>', methods=['DELETE'])
@admin_required
def delete_site_manager(manager_id):
    """Delete site manager"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM site_managers WHERE id = %s', (manager_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Site manager deleted successfully'})

# Report submission and validation routes
@app.route('/api/check-report-exists')
def check_report_exists():
    """Check if a report already exists for the given project and date"""
    project_code = request.args.get('project_code')
    report_date = request.args.get('report_date')
    
    if not project_code or not report_date:
        return jsonify({'error': 'project_code and report_date are required'}), 400
    
    conn = get_db_connection()
    
    # Check submitted reports table
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT report_number, submitted_at FROM submitted_reports 
        WHERE project_code = %s AND report_date = %s
    ''', (project_code, report_date))
    existing_report = cursor.fetchone()
    
    # Also check daily_progress_reports table for activity-level data
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT activity_description, planned_today, achieved_today, 
               planned_cumulative, achieved_cumulative
        FROM daily_progress_reports 
        WHERE project_code = %s AND report_date = %s
    ''', (project_code, report_date))
    existing_progress = cursor.fetchall()
    
    conn.close()
    
    if existing_report or existing_progress:
        # Convert progress data to dictionary
        progress_data = {}
        for row in existing_progress:
            progress_data[row['activity_description']] = {
                'planned_today': row['planned_today'],
                'achieved_today': row['achieved_today'],
                'planned_cumulative': row['planned_cumulative'],
                'achieved_cumulative': row['achieved_cumulative']
            }
        
        return jsonify({
            'exists': True,
            'report_number': existing_report['report_number'] if existing_report else None,
            'submitted_at': existing_report['submitted_at'] if existing_report else None,
            'progress_data': progress_data
        })
    else:
        return jsonify({'exists': False})

@app.route('/api/submit-report', methods=['POST'])
def submit_report():
    """Submit a complete daily progress report"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['reportNumber', 'projectCode', 'reportDate', 'projectName']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        conn = get_db_connection()
        
        # Check if report already exists
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT id FROM submitted_reports 
            WHERE project_code = %s AND report_date = %s
        ''', (data['projectCode'], data['reportDate']))
        existing_report = cursor.fetchone()
        
        # Build full payload for storage
        # 1) Pull activity-level data saved via daily_progress_reports (authoritative for activities)
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT dpr.activity_description,
                   dpr.planned_today,
                   dpr.achieved_today,
                   dpr.planned_cumulative,
                   dpr.achieved_cumulative,
                   ps.section_name,
                   pa.unit AS activity_unit,
                   pa.total_qty_planned AS total_qty_planned
            FROM daily_progress_reports dpr
            LEFT JOIN project_sections ps
              ON ps.id = dpr.section_id
            LEFT JOIN project_activities pa
              ON pa.project_code = dpr.project_code 
              AND pa.activity_description = dpr.activity_description
              AND pa.section_id = dpr.section_id
            WHERE dpr.project_code = %s AND dpr.report_date = %s
            ORDER BY ps.section_name, dpr.activity_description
        ''', (data['projectCode'], data['reportDate']))
        activities_rows = cursor.fetchall()
        activities_list = []
        for row in activities_rows:
            activities_list.append({
                'description': row['activity_description'],
                'sectionName': row['section_name'] or '',
                'unit': row['activity_unit'] or '',
                'total_qty': row['total_qty_planned'] if row['total_qty_planned'] is not None else '',
                'planned_today': row['planned_today'],
                'achieved_today': row['achieved_today'],
                'planned_cumulative': row['planned_cumulative'],
                'achieved_cumulative': row['achieved_cumulative']
            })

        # Fallback to activities provided by client if DPR table has none
        if not activities_list and isinstance(data.get('activities'), list):
            for a in data['activities']:
                activities_list.append({
                    'description': a.get('description', ''),
                    'sectionName': a.get('sectionName', ''),
                    'unit': a.get('unit', ''),
                    'total_qty': a.get('total_qty', ''),
                    'planned_today': a.get('planned_today', 0),
                    'achieved_today': a.get('achieved_today', 0),
                    'planned_cumulative': a.get('planned_cumulative', 0),
                    'achieved_cumulative': a.get('achieved_cumulative', 0)
                })

        # 2) Optional sections passed by client; if not provided, default sensibly
        manpower_list = data.get('manpower') or []
        equipment_list = data.get('equipment') or []
        remarks_text = data.get('remarks') or data.get('additionalNotes') or ''
        concerns_text = data.get('concerns') or data.get('concernAndIncidents') or ''
        incidents_text = data.get('incidents') or ''
        critical_issues_text = data.get('criticalIssues') or ''
        initiated_by_contractor = data.get('initiatedByContractor', '')
        verified_by = data.get('verifiedBy', '')
        mitigation_text = data.get('mitigation') or ''
        action_avoidance_text = data.get('actionAvoidance') or ''
        weather = data.get('weather') or {}
        critical_issues_details = data.get('criticalIssuesDetails') or []

        full_payload = {
            'reportNumber': data['reportNumber'],
            'projectCode': data['projectCode'],
            'reportDate': data['reportDate'],
            'projectName': data['projectName'],
            'preparedBy': data.get('preparedBy', ''),
            'checkedBy': data.get('checkedBy', ''),
            'approvedBy': data.get('approvedBy', ''),
            'initiatedByContractor': initiated_by_contractor,
            'verifiedBy': verified_by,
            # Header fields
            'projectManagerContractor': data.get('projectManagerContractor', ''),
            'projectManagerClient': data.get('projectManagerClient', ''),
            'targetCompletion': data.get('targetCompletion', ''),
            'client': data.get('client', ''),
            'contractor': data.get('contractor', ''),
            'subcontractorDeployed': data.get('subcontractorDeployed', ''),
            'weather': weather,
            'activities': activities_list,
            'manpower': manpower_list,
            'equipment': equipment_list,
            'remarks': remarks_text,
            'concerns': concerns_text,
            'mitigation': mitigation_text,
            'incidents': incidents_text,
            'actionAvoidance': action_avoidance_text,
            'criticalIssues': critical_issues_text,
            'criticalIssuesDetails': critical_issues_details
        }

        if existing_report:
            # Update existing report in-place with rebuilt payload
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE submitted_reports
                SET report_number = %s, project_code = %s, report_date = %s, project_name = %s,
                    prepared_by = ?, checked_by = ?, approved_by = ?, report_data = ?
                WHERE id = %s
            ''', (
                data['reportNumber'],
                data['projectCode'],
                data['reportDate'],
                data['projectName'],
                full_payload.get('preparedBy', ''),
                full_payload.get('checkedBy', ''),
                full_payload.get('approvedBy', ''),
                json.dumps(full_payload),
                existing_report['id']
            ))
        else:
            # Insert the report
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO submitted_reports 
                (report_number, project_code, report_date, project_name, prepared_by, checked_by, approved_by, report_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['reportNumber'],
                data['projectCode'],
                data['reportDate'],
                data['projectName'],
                full_payload.get('preparedBy', ''),
                full_payload.get('checkedBy', ''),
                full_payload.get('approvedBy', ''),
                json.dumps(full_payload)
            ))
        
        conn.commit()
        cursor.close()
        conn.close()

        # Add notification for this submission (visible for 48 hours)
        try:
            msg = f"Report {data['reportNumber']} submitted for project {data['projectCode']} on {data['reportDate']}"
            add_notification(msg, {
                'reportNumber': data['reportNumber'],
                'projectCode': data['projectCode'],
                'reportDate': data['reportDate'],
                'projectName': data.get('projectName', '')
            })
        except Exception:
            # Do not block submission on notification failure
            pass
        
        return jsonify({
            'success': True,
            'message': f'Report {data["reportNumber"]} saved',
            'report_number': data['reportNumber']
        })
        
    except mysql.connector.IntegrityError as e:
        if 'UNIQUE constraint failed: submitted_reports.report_number' in str(e):
            return jsonify({'error': 'This report number already exists'}), 409
        elif 'UNIQUE constraint failed: submitted_reports.project_code, submitted_reports.report_date' in str(e):
            return jsonify({'error': 'A report for this project and date already exists'}), 409
        else:
            return jsonify({'error': f'Database constraint error: {str(e)}'}), 400
    except Exception as e:
        print(f"Error submitting report: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

# Check admin login status for frontend
@app.route('/api/admin/status')
def admin_status():
    """Check if admin is logged in"""
    return jsonify({
        'logged_in': session.get('admin_logged_in', False),
        'username': session.get('admin_username', '')
    })

@app.route('/api/previous-day-progress')
def get_previous_day_progress():
    """Get previous day's progress for cumulative calculation"""
    project_code = request.args.get('project_code')
    current_date = request.args.get('current_date')  # Format: YYYY-MM-DD
    
    if not project_code or not current_date:
        return jsonify({'error': 'project_code and current_date are required'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT dpr.activity_description, dpr.section_id, dpr.planned_cumulative, dpr.achieved_cumulative, ps.section_name
            FROM daily_progress_reports dpr
            LEFT JOIN project_sections ps ON dpr.section_id = ps.id
            WHERE dpr.project_code = %s 
              AND dpr.report_date = (
                SELECT MAX(report_date)
                FROM daily_progress_reports dpr2
                WHERE dpr2.project_code = dpr.project_code
                  AND dpr2.activity_description = dpr.activity_description
                  AND dpr2.section_id = dpr.section_id
                  AND dpr2.report_date < %s
              )
        ''', (project_code, current_date))
        previous_reports = cursor.fetchall()
        conn.close()
        
        # Convert to dictionary for easy lookup
        previous_data = {}
        for report in previous_reports:
            key = f"{report['section_name']}|{report['activity_description']}" if report['section_name'] else report['activity_description']
            previous_data[key] = {
                'planned_cumulative': report['planned_cumulative'],
                'achieved_cumulative': report['achieved_cumulative']
            }
        
        return jsonify(previous_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-daily-progress', methods=['POST'])
def save_daily_progress():
    """Save daily progress report"""
    data = request.get_json()
    
    required_fields = ['project_code', 'report_date', 'activities']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        conn = get_db_connection()
        
        for activity in data['activities']:
            cursor = conn.cursor()

            # Lookup section_id
            section_id = 0
            section_name = activity.get('sectionName')
            if section_name:
                cursor.execute("SELECT id FROM project_sections WHERE project_code = %s AND section_name = %s", (data['project_code'], section_name))
                section_res = cursor.fetchone()
                if section_res:
                    section_id = section_res[0]

            cursor.execute('''
                REPLACE INTO daily_progress_reports 
                (project_code, report_date, section_id, activity_description, planned_today, achieved_today, planned_cumulative, achieved_cumulative)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['project_code'],
                data['report_date'],
                section_id,
                activity['description'],
                activity['planned_today'],
                activity['achieved_today'],
                activity['planned_cumulative'],
                activity['achieved_cumulative']
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Progress saved successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
