from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import sqlite3
import hashlib
import os
import asyncio
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

DATABASE = 'dpr_database.db'

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_if_not_exists():
    """Initialize database if it doesn't exist"""
    if not os.path.exists(DATABASE):
        import init_database
        init_database.init_database()

# Initialize database on startup
init_db_if_not_exists()

@app.route('/')
def index():
    """Main form route"""
    return render_template('index.html')

@app.route('/api/projects')
def get_projects():
    """API endpoint to get all projects"""
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects ORDER BY code').fetchall()
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
    if project_code:
        preparers = conn.execute('''
            SELECT name, designation FROM report_preparers 
            WHERE project_code = ? OR project_code IS NULL 
            ORDER BY name
        ''', (project_code,)).fetchall()
    else:
        preparers = conn.execute('SELECT name, designation FROM report_preparers ORDER BY name').fetchall()
    conn.close()
    
    return jsonify([{'name': p['name'], 'designation': p['designation']} for p in preparers])

@app.route('/api/site-managers')
def get_site_managers():
    """API endpoint to get site managers for a specific project"""
    project_code = request.args.get('project_code')
    
    conn = get_db_connection()
    if project_code:
        managers = conn.execute('''
            SELECT name, designation FROM site_managers 
            WHERE project_code = ? OR project_code IS NULL 
            ORDER BY name
        ''', (project_code,)).fetchall()
    else:
        managers = conn.execute('SELECT name, designation FROM site_managers ORDER BY name').fetchall()
    conn.close()
    
    return jsonify([{'name': m['name'], 'designation': m['designation']} for m in managers])

@app.route('/api/departments')
def get_departments():
    """API endpoint to get all departments"""
    conn = get_db_connection()
    departments = conn.execute('SELECT name FROM departments ORDER BY name').fetchall()
    conn.close()
    
    return jsonify([dept['name'] for dept in departments])

@app.route('/api/contractors')
def get_contractors():
    """API endpoint to get contractors for a specific project"""
    project_code = request.args.get('project_code')
    
    conn = get_db_connection()
    if project_code:
        contractors = conn.execute('''
            SELECT contractor_name, contact_person, contact_details FROM contractors 
            WHERE project_code = ? OR project_code IS NULL 
            ORDER BY contractor_name
        ''', (project_code,)).fetchall()
    else:
        contractors = conn.execute('SELECT contractor_name, contact_person, contact_details FROM contractors ORDER BY contractor_name').fetchall()
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
    designations = conn.execute('SELECT designation FROM manpower_designations ORDER BY designation').fetchall()
    conn.close()
    
    return jsonify([designation['designation'] for designation in designations])

@app.route('/api/equipment-descriptions')
def get_equipment_descriptions():
    """API endpoint to get all equipment descriptions"""
    conn = get_db_connection()
    equipment = conn.execute('SELECT description FROM equipment_descriptions ORDER BY description').fetchall()
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
    sections = conn.execute('''
        SELECT * FROM project_sections 
        WHERE project_code = ? 
        ORDER BY section_name
    ''', (project_code,)).fetchall()
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
            section_row = conn.execute('''
                SELECT id, section_id FROM project_sections
                WHERE project_code = ? AND section_id = ?
            ''', (project, raw_identifier)).fetchone()
            if section_row:
                return section_row
            # If not found, attempt to interpret as integer primary key
            try:
                int_id = int(raw_identifier)
                section_row = conn.execute('''
                    SELECT id, section_id FROM project_sections
                    WHERE project_code = ? AND id = ?
                ''', (project, int_id)).fetchone()
                return section_row
            except Exception:
                return None

        if section_identifier:
            # Resolve to DB id
            section_row = resolve_section(project_code, section_identifier)
            if not section_row:
                conn.close()
                return jsonify({'error': f'section "{section_identifier}" not found for project {project_code}'}), 404

            section_db_id = section_row['id']
            # Get activities for this section id
            activities = conn.execute('''
                SELECT activity_description, area, unit, total_qty_planned
                FROM project_activities
                WHERE project_code = ? AND section_id = ?
                ORDER BY activity_description
            ''', (project_code, section_db_id)).fetchall()
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
            rows = conn.execute('''
                SELECT ps.section_id AS section_identifier,
                       pa.activity_description, pa.area, pa.unit, pa.total_qty_planned
                FROM project_activities pa
                JOIN project_sections ps ON pa.section_id = ps.id
                WHERE pa.project_code = ?
                ORDER BY ps.section_id, pa.activity_description
            ''', (project_code,)).fetchall()
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
        existing_section = conn.execute('''
            SELECT id FROM project_sections 
            WHERE project_code = ? AND (section_id = ? OR section_name = ?)
        ''', (project_code, section_id, section_name)).fetchone()
        
        if existing_section:
            conn.close()
            return jsonify({'error': 'Section already exists', 'section_id': existing_section['id']}), 409
        
        # Get the next order index
        max_order = conn.execute('''
            SELECT MAX(order_index) as max_order FROM project_sections 
            WHERE project_code = ?
        ''', (project_code,)).fetchone()
        
        next_order = (max_order['max_order'] or 0) + 1
        
        # Insert new section
        cursor = conn.execute('''
            INSERT INTO project_sections (project_code, section_id, section_name, order_index)
            VALUES (?, ?, ?, ?)
        ''', (project_code, section_id, section_name, next_order))
        
        db_section_id = cursor.lastrowid
        conn.commit()
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
        section = conn.execute('''
            SELECT id, section_id FROM project_sections 
            WHERE project_code = ? AND (section_name = ? OR section_id = ?)
        ''', (project_code, section_name, section_name)).fetchone()
        
        if not section:
            conn.close()
            return jsonify({'error': f'Section "{section_name}" not found for project {project_code}'}), 404
        
        # Use the database primary key ID for foreign key reference
        section_db_id = section['id']
        
        # Check if activity already exists in this section
        existing_activity = conn.execute('''
            SELECT id FROM project_activities 
            WHERE project_code = ? AND section_id = ? AND activity_description = ?
        ''', (project_code, section_db_id, activity_description)).fetchone()
        
        if existing_activity:
            conn.close()
            return jsonify({'error': 'Activity already exists', 'activity_id': existing_activity['id']}), 409
        
        # Get the next order index for this section
        max_order = conn.execute('''
            SELECT MAX(order_index) as max_order FROM project_activities 
            WHERE section_id = ?
        ''', (section_db_id,)).fetchone()
        
        next_order = (max_order['max_order'] or 0) + 1
        
        # Insert new activity
        cursor = conn.execute('''
            INSERT INTO project_activities (project_code, section_id, activity_description, area, unit, total_qty_planned, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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
        activity = conn.execute('''
            SELECT pa.id FROM project_activities pa
            JOIN project_sections ps ON pa.section_id = ps.id
            WHERE pa.project_code = ? AND ps.section_name = ? AND pa.activity_description = ?
        ''', (project_code, section_name, activity_description)).fetchone()
        
        if not activity:
            conn.close()
            return jsonify({'error': f'Activity "{activity_description}" not found in section "{section_name}" for project {project_code}'}), 404
        
        # Update the activity
        conn.execute('''
            UPDATE project_activities 
            SET area = ?, unit = ?, total_qty_planned = ?
            WHERE id = ?
        ''', (area, unit, total_qty, activity['id']))
        
        conn.commit()
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
        user = conn.execute(
            'SELECT * FROM admin_users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        ).fetchone()
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
    project_count = conn.execute('SELECT COUNT(*) as count FROM projects').fetchone()['count']
    preparers_count = conn.execute('SELECT COUNT(*) as count FROM report_preparers').fetchone()['count']
    managers_count = conn.execute('SELECT COUNT(*) as count FROM site_managers').fetchone()['count']
    department_count = conn.execute('SELECT COUNT(*) as count FROM departments').fetchone()['count']
    contractor_count = conn.execute('SELECT COUNT(*) as count FROM contractors').fetchone()['count']
    
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
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()

    reports = []
    if project_code or report_date:
        # Build dynamic where clause
        where = []
        params = []
        if project_code:
            where.append('sr.project_code = ?')
            params.append(project_code)
        if report_date:
            where.append('sr.report_date = ?')
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
        reports = conn.execute(query, tuple(params)).fetchall()

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
            'report_date': r['report_date'],
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
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()

    reports = []
    if project_code or report_date:
        where = []
        params = []
        if project_code:
            where.append('sr.project_code = ?')
            params.append(project_code)
        if report_date:
            where.append('sr.report_date = ?')
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
        reports = conn.execute(query, tuple(params)).fetchall()
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
            'report_date': r['report_date'],
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

@app.route('/admin/projects')
@admin_required
def admin_projects():
    """Admin projects management"""
    conn = get_db_connection()
    projects = conn.execute('SELECT * FROM projects ORDER BY code').fetchall()
    conn.close()
    
    return render_template('admin_projects.html', projects=projects)

@app.route('/admin/projects/add', methods=['POST'])
@admin_required
def add_project():
    """Add new project"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO projects (code, name, manager, project_manager_client, client, contractor, report_id_fragment, target_completion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['code'], data['name'], data['manager'], data['projectManagerClient'],
            data['client'], data['contractor'], data['reportIdFragment'], data['targetCompletion']
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Project added successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Project code already exists'})
    finally:
        conn.close()

@app.route('/admin/projects/update/<int:project_id>', methods=['POST'])
@admin_required
def update_project(project_id):
    """Update existing project"""
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE projects 
        SET code=?, name=?, manager=?, project_manager_client=?, client=?, contractor=?, report_id_fragment=?, target_completion=?
        WHERE id=?
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
    conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project deleted successfully'})

@app.route('/admin/staff')
@admin_required
def admin_staff():
    """Admin staff management"""
    conn = get_db_connection()
    staff = conn.execute('SELECT * FROM staff ORDER BY name').fetchall()
    conn.close()
    
    return render_template('admin_staff.html', staff=staff)

@app.route('/admin/staff/add', methods=['POST'])
@admin_required
def add_staff():
    """Add new staff member"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO staff (name, designation) VALUES (?, ?)', (data['name'], data['designation']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Staff member added successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Staff member name already exists'})
    finally:
        conn.close()

@app.route('/admin/staff/update/<int:staff_id>', methods=['POST'])
@admin_required
def update_staff(staff_id):
    """Update existing staff member"""
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute('UPDATE staff SET name=?, designation=? WHERE id=?', (data['name'], data['designation'], staff_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Staff member updated successfully'})

@app.route('/admin/staff/delete/<int:staff_id>', methods=['DELETE'])
@admin_required
def delete_staff(staff_id):
    """Delete staff member"""
    conn = get_db_connection()
    conn.execute('DELETE FROM staff WHERE id = ?', (staff_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Staff member deleted successfully'})

@app.route('/admin/departments')
@admin_required
def admin_departments():
    """Admin departments management"""
    conn = get_db_connection()
    departments = conn.execute('SELECT * FROM departments ORDER BY name').fetchall()
    conn.close()
    
    return render_template('admin_departments.html', departments=departments)

@app.route('/admin/departments/add', methods=['POST'])
@admin_required
def add_department():
    """Add new department"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO departments (name) VALUES (?)', (data['name'],))
        conn.commit()
        return jsonify({'success': True, 'message': 'Department added successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Department name already exists'})
    finally:
        conn.close()

@app.route('/admin/departments/update/<int:dept_id>', methods=['POST'])
@admin_required
def update_department(dept_id):
    """Update existing department"""
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute('UPDATE departments SET name=? WHERE id=?', (data['name'], dept_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Department updated successfully'})

@app.route('/admin/departments/delete/<int:dept_id>', methods=['DELETE'])
@admin_required
def delete_department(dept_id):
    """Delete department"""
    conn = get_db_connection()
    conn.execute('DELETE FROM departments WHERE id = ?', (dept_id,))
    conn.commit()
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
    sections = conn.execute('''
        SELECT ps.*, p.name as project_name 
        FROM project_sections ps
        JOIN projects p ON ps.project_code = p.code
        ORDER BY ps.project_code, ps.section_name
    ''').fetchall()
    
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()
    conn.close()
    
    return render_template('admin_project_sections.html', sections=sections, projects=projects)

@app.route('/admin/project-sections/add', methods=['POST'])
@admin_required
def add_project_section():
    """Add new project section"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO project_sections (project_code, section_id, section_name, area, unit, total_qty_planned)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['projectCode'], data['sectionId'], data['sectionName'],
            data['area'], data['unit'], data['totalQtyPlanned']
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Project section added successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Section already exists for this project'})
    finally:
        conn.close()

@app.route('/admin/project-sections/update/<int:section_id>', methods=['POST'])
@admin_required
def update_project_section(section_id):
    """Update existing project section"""
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE project_sections 
        SET section_id=?, section_name=?, area=?, unit=?, total_qty_planned=?
        WHERE id=?
    ''', (
        data['sectionId'], data['sectionName'], data['area'], 
        data['unit'], data['totalQtyPlanned'], section_id
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project section updated successfully'})

@app.route('/admin/project-sections/delete/<int:section_id>', methods=['DELETE'])
@admin_required
def delete_project_section(section_id):
    """Delete project section"""
    conn = get_db_connection()
    # First delete associated activities
    conn.execute('DELETE FROM project_activities WHERE project_code = (SELECT project_code FROM project_sections WHERE id = ?) AND section_id = (SELECT section_id FROM project_sections WHERE id = ?)', (section_id, section_id))
    # Then delete section
    conn.execute('DELETE FROM project_sections WHERE id = ?', (section_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project section deleted successfully'})

@app.route('/admin/project-activities')
@admin_required
def admin_project_activities():
    """Admin project activities management"""
    conn = get_db_connection()
    activities = conn.execute('''
        SELECT pa.*, p.name as project_name, ps.section_name
        FROM project_activities pa
        JOIN projects p ON pa.project_code = p.code
        JOIN project_sections ps ON pa.section_id = ps.id
        ORDER BY pa.project_code, pa.section_id, pa.activity_description
    ''').fetchall()
    
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()
    sections_rows = conn.execute('SELECT project_code, section_id, section_name FROM project_sections ORDER BY project_code, section_name').fetchall()
    conn.close()
    
    # Convert Row objects to dictionaries for JSON serialization
    sections = []
    for section in sections_rows:
        sections.append({
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
    max_order = conn.execute('''
        SELECT MAX(order_index) as max_order FROM project_activities 
        WHERE section_id = ?
    ''', (data['sectionId'],)).fetchone()
    
    next_order = (max_order['max_order'] or 0) + 1
    
    conn.execute('''
        INSERT INTO project_activities (project_code, section_id, activity_description, area, unit, total_qty_planned, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['projectCode'], data['sectionId'], data['activityDescription'],
        data['area'], data['unit'], data['totalQtyPlanned'], next_order
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project activity added successfully'})

@app.route('/admin/project-activities/update/<int:activity_id>', methods=['POST'])
@admin_required
def update_project_activity(activity_id):
    """Update existing project activity"""
    data = request.get_json()
    
    conn = get_db_connection()
    conn.execute('''
        UPDATE project_activities 
        SET section_id=?, activity_description=?, area=?, unit=?, total_qty_planned=?
        WHERE id=?
    ''', (
        data['sectionId'], data['activityDescription'], data['area'],
        data['unit'], data['totalQtyPlanned'], activity_id
    ))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project activity updated successfully'})

@app.route('/admin/project-activities/delete/<int:activity_id>', methods=['DELETE'])
@admin_required
def delete_project_activity(activity_id):
    """Delete project activity"""
    conn = get_db_connection()
    conn.execute('DELETE FROM project_activities WHERE id = ?', (activity_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Project activity deleted successfully'})

# Admin routes for role-based staff management
@app.route('/admin/report-preparers')
@admin_required
def admin_report_preparers():
    """Admin report preparers management"""
    conn = get_db_connection()
    preparers = conn.execute('''
        SELECT rp.*, p.name as project_name 
        FROM report_preparers rp
        LEFT JOIN projects p ON rp.project_code = p.code
        ORDER BY rp.project_code, rp.name
    ''').fetchall()
    
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()
    conn.close()
    
    return render_template('admin_report_preparers.html', preparers=preparers, projects=projects)

@app.route('/admin/contractors')
@admin_required
def admin_contractors():
    """Admin contractors management"""
    conn = get_db_connection()
    contractors = conn.execute('''
        SELECT c.*, p.name as project_name 
        FROM contractors c
        LEFT JOIN projects p ON c.project_code = p.code
        ORDER BY c.project_code, c.contractor_name
    ''').fetchall()
    
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()
    conn.close()
    
    return render_template('admin_contractors.html', contractors=contractors, projects=projects)

@app.route('/admin/site-managers')
@admin_required
def admin_site_managers():
    """Admin site managers management"""
    conn = get_db_connection()
    managers = conn.execute('''
        SELECT sm.*, p.name as project_name 
        FROM site_managers sm
        LEFT JOIN projects p ON sm.project_code = p.code
        ORDER BY sm.project_code, sm.name
    ''').fetchall()
    
    projects = conn.execute('SELECT code, name FROM projects ORDER BY code').fetchall()
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
        existing = conn.execute('SELECT 1 FROM report_preparers WHERE name = ?', (data['name'],)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Report preparer name must be unique'}), 409
        conn.execute('''
            INSERT INTO report_preparers (name, designation, project_code) 
            VALUES (?, ?, ?)
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
        existing = conn.execute('SELECT 1 FROM report_preparers WHERE name = ? AND id <> ?', (data['name'], preparer_id)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Report preparer name must be unique'}), 409
        conn.execute('''
            UPDATE report_preparers 
            SET name=?, designation=?, project_code=? 
            WHERE id=?
        ''', (data['name'], data['designation'], data.get('project_code'), preparer_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Report preparer updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/report-preparers/delete/<int:preparer_id>', methods=['DELETE'])
@admin_required
def delete_report_preparer(preparer_id):
    """Delete report preparer"""
    conn = get_db_connection()
    conn.execute('DELETE FROM report_preparers WHERE id = ?', (preparer_id,))
    conn.commit()
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
        existing = conn.execute('''
            SELECT 1 FROM contractors WHERE project_code = ? AND contractor_name = ?
        ''', (data.get('project_code'), data['contractor_name'])).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Contractor already exists for this project'}), 409
        conn.execute('''
            INSERT INTO contractors (contractor_name, project_code, contact_person, contact_details) 
            VALUES (?, ?, ?, ?)
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
        existing = conn.execute('''
            SELECT 1 FROM contractors 
            WHERE project_code = ? AND contractor_name = ? AND id <> ?
        ''', (data.get('project_code'), data['contractor_name'], contractor_id)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Contractor already exists for this project'}), 409
        conn.execute('''
            UPDATE contractors 
            SET contractor_name=?, project_code=?, contact_person=?, contact_details=? 
            WHERE id=?
        ''', (data['contractor_name'], data.get('project_code'), data.get('contact_person', ''), data.get('contact_details', ''), contractor_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Contractor updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/contractors/delete/<int:contractor_id>', methods=['DELETE'])
@admin_required
def delete_contractor(contractor_id):
    """Delete contractor"""
    conn = get_db_connection()
    conn.execute('DELETE FROM contractors WHERE id = ?', (contractor_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Contractor deleted successfully'})

@app.route('/admin/site-managers/add', methods=['POST'])
@admin_required
def add_site_manager():
    """Add new site manager"""
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT 1 FROM site_managers WHERE name = ?', (data['name'],)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Site manager name must be unique'}), 409
        conn.execute('''
            INSERT INTO site_managers (name, designation, project_code) 
            VALUES (?, ?, ?)
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
        existing = conn.execute('SELECT 1 FROM site_managers WHERE name = ? AND id <> ?', (data['name'], manager_id)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Site manager name must be unique'}), 409
        conn.execute('''
            UPDATE site_managers 
            SET name=?, designation=?, project_code=? 
            WHERE id=?
        ''', (data['name'], data['designation'], data.get('project_code'), manager_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Site manager updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/admin/site-managers/delete/<int:manager_id>', methods=['DELETE'])
@admin_required
def delete_site_manager(manager_id):
    """Delete site manager"""
    conn = get_db_connection()
    conn.execute('DELETE FROM site_managers WHERE id = ?', (manager_id,))
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
    existing_report = conn.execute('''
        SELECT report_number, submitted_at FROM submitted_reports 
        WHERE project_code = ? AND report_date = ?
    ''', (project_code, report_date)).fetchone()
    
    # Also check daily_progress_reports table for activity-level data
    existing_progress = conn.execute('''
        SELECT activity_description, planned_today, achieved_today, 
               planned_cumulative, achieved_cumulative
        FROM daily_progress_reports 
        WHERE project_code = ? AND report_date = ?
    ''', (project_code, report_date)).fetchall()
    
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
        existing_report = conn.execute('''
            SELECT id FROM submitted_reports 
            WHERE project_code = ? AND report_date = ?
        ''', (data['projectCode'], data['reportDate'])).fetchone()
        
        # Build full payload for storage
        # 1) Pull activity-level data saved via daily_progress_reports (authoritative for activities)
        activities_rows = conn.execute('''
            SELECT dpr.activity_description,
                   dpr.planned_today,
                   dpr.achieved_today,
                   dpr.planned_cumulative,
                   dpr.achieved_cumulative,
                   ps.section_name,
                   pa.unit AS activity_unit,
                   pa.total_qty_planned AS total_qty_planned
            FROM daily_progress_reports dpr
            LEFT JOIN project_activities pa
              ON pa.project_code = dpr.project_code AND pa.activity_description = dpr.activity_description
            LEFT JOIN project_sections ps
              ON ps.id = pa.section_id
            WHERE dpr.project_code = ? AND dpr.report_date = ?
            ORDER BY ps.section_name, dpr.activity_description
        ''', (data['projectCode'], data['reportDate'])).fetchall()
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
            conn.execute('''
                UPDATE submitted_reports
                SET report_number = ?, project_code = ?, report_date = ?, project_name = ?,
                    prepared_by = ?, checked_by = ?, approved_by = ?, report_data = ?
                WHERE id = ?
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
            conn.execute('''
                INSERT INTO submitted_reports 
                (report_number, project_code, report_date, project_name, prepared_by, checked_by, approved_by, report_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Report {data["reportNumber"]} saved',
            'report_number': data['reportNumber']
        })
        
    except sqlite3.IntegrityError as e:
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
        # Parse current date and get previous date
        from datetime import datetime, timedelta
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        previous_dt = current_dt - timedelta(days=1)
        previous_date = previous_dt.strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        previous_reports = conn.execute('''
            SELECT activity_description, planned_cumulative, achieved_cumulative
            FROM daily_progress_reports
            WHERE project_code = ? AND report_date = ?
        ''', (project_code, previous_date)).fetchall()
        conn.close()
        
        # Convert to dictionary for easy lookup
        previous_data = {}
        for report in previous_reports:
            previous_data[report['activity_description']] = {
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
            conn.execute('''
                INSERT OR REPLACE INTO daily_progress_reports 
                (project_code, report_date, activity_description, planned_today, achieved_today, planned_cumulative, achieved_cumulative)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['project_code'],
                data['report_date'],
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
