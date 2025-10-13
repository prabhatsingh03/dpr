import sqlite3
import json
import os

def init_database():
    """Initialize the SQLite database with constants from the HTML form"""
    
    # Create database
    conn = sqlite3.connect('dpr_database.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        manager TEXT NOT NULL,
        project_manager_client TEXT NOT NULL,
        client TEXT NOT NULL,
        contractor TEXT NOT NULL,
        report_id_fragment TEXT NOT NULL,
        target_completion TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS report_preparers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        designation TEXT NOT NULL,
        project_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_code) REFERENCES projects (code),
        UNIQUE(name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contractors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contractor_name TEXT NOT NULL,
        project_code TEXT,
        contact_person TEXT,
        contact_details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_code) REFERENCES projects (code),
        UNIQUE(project_code, contractor_name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS site_managers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        designation TEXT NOT NULL,
        project_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_code) REFERENCES projects (code),
        UNIQUE(name)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Old contractors table removed - now using project-specific contractors table above
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS manpower_designations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        designation TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment_descriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT NOT NULL,
        section_id TEXT NOT NULL,
        section_name TEXT NOT NULL,
        area TEXT,
        unit TEXT,
        total_qty_planned INTEGER DEFAULT 0,
        order_index INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_code, section_id),
        FOREIGN KEY (project_code) REFERENCES projects (code)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS project_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT NOT NULL,
        section_id INTEGER NOT NULL,
        activity_description TEXT NOT NULL,
        area TEXT,
        unit TEXT NOT NULL,
        total_qty_planned INTEGER NOT NULL,
        order_index INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_code) REFERENCES projects (code),
        FOREIGN KEY (section_id) REFERENCES project_sections (id),
        UNIQUE(project_code, section_id, activity_description)
    )
    ''')
    
    # Legacy activity tables removed - now using project_activities and project_sections
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_progress_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT NOT NULL,
        report_date TEXT NOT NULL,
        activity_description TEXT NOT NULL,
        planned_today INTEGER DEFAULT 0,
        achieved_today INTEGER DEFAULT 0,
        planned_cumulative INTEGER DEFAULT 0,
        achieved_cumulative INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project_code, report_date, activity_description)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS submitted_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_number TEXT UNIQUE NOT NULL,
        project_code TEXT NOT NULL,
        report_date TEXT NOT NULL,
        project_name TEXT,
        prepared_by TEXT,
        checked_by TEXT,
        approved_by TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        report_data TEXT, -- JSON string of the complete form data
        UNIQUE(project_code, report_date),
        FOREIGN KEY (project_code) REFERENCES projects (code)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS app_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE NOT NULL,
        setting_value TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Insert initial data
    
    # Projects data
    projects_data = [
        ('I-30059', '5th Evaporator', 'Biswa Ranjan Dash', 'Harihar Panigrahi', 'PPL', 'SIMON India', 'I-30059', '2025-11-30'),
        ('I-2501F001', 'Sulphur Melting & Filtration Facility', 'Biswa Ranjan Dash', 'Bishnu Prasad Mohanty', 'PPL', 'SIMON India', 'I-2501F001', '2026-01-21'),
        ('I-2501F002', '23MW Power Plant TG-4, PPL', 'Biswa Ranjan Dash', 'Bishnu Prasad Mohanty', 'PPL', 'SIMON India', 'I-2501F002', ''),
        ('I-2503F002', '8000T Phosphoric Acid Tank, MCFL', 'Biswa Ranjan Dash', 'Shailesh', 'MCFL', 'SIMON India', 'I-2503F002', '')
    ]
    
    for project in projects_data:
        cursor.execute('''
        INSERT OR IGNORE INTO projects 
        (code, name, manager, project_manager_client, client, contractor, report_id_fragment, target_completion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', project)
    
    # Report Preparers data (People who can prepare reports)
    report_preparers_data = [
        ('Saravanakumar B', 'Senior Engineer QA/QC (Civil)', 'I-30059'),
        # Add more preparers as needed
    ]
    
    for preparer in report_preparers_data:
        cursor.execute('INSERT OR IGNORE INTO report_preparers (name, designation, project_code) VALUES (?, ?, ?)', preparer)
    
    # Contractors data (Initiated by Contractor) - Project Specific
    contractors_data = [
        # I-30059 5th Evaporator Project Contractors
        ('RRPL', 'I-30059', '', ''),
        ('CHEMIST', 'I-30059', '', ''),
        ('KRUPANJAL', 'I-30059', '', ''),
        ('BBGC', 'I-30059', '', ''),
        ('FRIENDS', 'I-30059', '', ''),
        ('RK ENGG', 'I-30059', '', ''),
        ('SIMAL', 'I-30059', '', ''),
        ('M SQUARE', 'I-30059', '', ''),
        ('GUMI', 'I-30059', '', ''),
        ('SAMANTARAY', 'I-30059', '', ''),
        
        # I-2501F001 Project Contractor
        ('PIPL', 'I-2501F001', '', ''),
        
        # Add more project-specific contractors as needed
    ]
    
    for contractor in contractors_data:
        cursor.execute('INSERT OR IGNORE INTO contractors (contractor_name, project_code, contact_person, contact_details) VALUES (?, ?, ?, ?)', contractor)
    
    # Site Managers data (People who can verify reports)
    site_managers_data = [
        ('Biswaranjan Dash', 'Project Manager', 'I-30059'),
        ('Anupam Naik', 'Lead - Civil', 'I-30059'),
        # Add more site managers as needed
    ]
    
    for manager in site_managers_data:
        cursor.execute('INSERT OR IGNORE INTO site_managers (name, designation, project_code) VALUES (?, ?, ?)', manager)
    
    # Departments data
    departments_data = [
        'Civil Team', 'Mechanical Team', 'Electrical Team', 
        'Safety Department', 'Logistics', 'Admin'
    ]
    
    for dept in departments_data:
        cursor.execute('INSERT OR IGNORE INTO departments (name) VALUES (?)', (dept,))
    
    # Old contractors data removed - now using project-specific contractors above
    
    # Manpower designations
    manpower_designations_data = [
        'Foreman', 'Fitter', 'Welder', 'Gas cutter', 'Grinder', 'Rigger',
        'Mechanical Helper', 'Farana Operator', 'Scaffolder', 'Mason', 'Bar bender',
        'Carpenter', 'Civil helper', 'Excavator Operator', 'Store keeper',
        'Electrician', 'Safety officer', 'Engg (Civil)', 'Civil Supervisor',
        'Mechanical Supervisor', 'Engg (Mech)', 'Labour Supervisor', 'Helper',
        'Mechanical Engineer', 'Safety Supervisor', 'Blaster', 'Painter',
        'Supervisor', 'Electrical Engineer', 'Truck Operator'
    ]
    
    for designation in manpower_designations_data:
        cursor.execute('INSERT OR IGNORE INTO manpower_designations (designation) VALUES (?)', (designation,))
    
    # Equipment descriptions
    equipment_descriptions_data = [
        'Farana crane', 'Welding machine', '100 MT crane', 'Cutting machine',
        'Excavator', 'Barbending and cutting machine', 'Vibrator', 'Dewatering pump',
        'Blasting machine', 'Concrete Mixer', 'DMC'
    ]
    
    for equipment in equipment_descriptions_data:
        cursor.execute('INSERT OR IGNORE INTO equipment_descriptions (description) VALUES (?)', (equipment,))
    
    # Legacy activity tables removed - now using project_activities and project_sections
    
    # Project-specific sections and activities for I-30059 (5th Evaporator)
    project_sections_data = [
        ('I-30059', 'concrete', 'Concrete', '5th Evaporator Building', 'M3', 609),
        ('I-30059', 'steel', 'Structure Steel works', '5th Evaporator Building', 'MT', 356),
        ('I-30059', 'ctBasin', 'CT Basin', 'Cooling Tower', 'M3', 305),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack', 'IBR Piperack', 'M3', 120),
        
        # Project-specific sections for I-2501F001 (Sulphur Melting & Filtration Facility)
        ('I-2501F001', 'concrete', 'Concrete', 'SM&FU', 'M3', 2469)
    ]
    
    for section in project_sections_data:
        cursor.execute('''
        INSERT OR IGNORE INTO project_sections 
        (project_code, section_id, section_name, area, unit, total_qty_planned)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', section)
    
    # Project-specific activities for I-30059 (5th Evaporator)
    project_activities_data = [
        # Concrete activities
        ('I-30059', 'concrete', 'Grade Slab Soling Work', '5th Evaporator Building', 'CUM', 48),
        ('I-30059', 'concrete', 'Grade Slab PCC Work', '5th Evaporator Building', 'CUM', 24),
        ('I-30059', 'concrete', 'Grade Slab Reinforcement Work', '5th Evaporator Building', 'MT', 38),
        ('I-30059', 'concrete', 'Grade Slab RCC Work', '5th Evaporator Building', 'CUM', 110),
        ('I-30059', 'concrete', 'Equipment and Pump foundation RCC Work', '5th Evaporator Building', 'CUM', 100),
        ('I-30059', 'concrete', 'Scaffolding laying work for Structural erection', '5th Evaporator Building', 'CUM', 1500),
        
        # Structure Steel works activities
        ('I-30059', 'steel', 'Structural Steel Fabrication Works', '5th Evaporator Building', 'MT', 356),
        ('I-30059', 'steel', 'Structural Steel Blasting and Painting Works', '5th Evaporator Building', 'MT', 356),
        ('I-30059', 'steel', 'Structural Steel Erection Works', '5th Evaporator Building', 'MT', 356),
        ('I-30059', 'steel', 'Equipment Erection Works', '5th Evaporator Building', 'MT', 200),
        
        # CT Basin activities
        ('I-30059', 'ctBasin', 'CT Basin Excavation Works', 'Cooling Tower', 'CUM', 950),
        ('I-30059', 'ctBasin', 'CT Basin PCC Works', 'Cooling Tower', 'CUM', 25),
        ('I-30059', 'ctBasin', 'CT Basin Pile Chipping Work', 'Cooling Tower', 'No.', 34),
        ('I-30059', 'ctBasin', 'CT Basin wall and pedestal reinforcement work', 'Cooling Tower', 'MT', 28),
        ('I-30059', 'ctBasin', 'CT Basin brickwork', 'Cooling Tower', 'CUM', 35),
        ('I-30059', 'ctBasin', 'CT Basin RCC work', 'Cooling Tower', 'CUM', 305),
        ('I-30059', 'ctBasin', 'CT Basin Wall Shuttering work', 'Cooling Tower', 'SQM', 550),
        ('I-30059', 'ctBasin', 'CT Basin Wall Deshuttering work', 'Cooling Tower', 'SQM', 500),
        
        # IBR Pipe Rack activities
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack Raft Excavation Work', 'IBR Piperack', 'CUM', 250),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack Raft Reinforcement Making Work', 'IBR Piperack', 'CUM', 15),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack Raft Reinforcement Laying Work', 'IBR Piperack', 'CUM', 15),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack RCC Work', 'IBR Piperack', 'CUM', 75),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack shuttering making work', 'IBR Piperack', 'SQM', 250),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack shuttering fixing work', 'IBR Piperack', 'SQM', 250),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack PCC Work', 'IBR Piperack', 'CUM', 30),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack Soiling Work', 'IBR Piperack', 'CUM', 50),
        ('I-30059', 'ibrPiperack', 'IBR Pipe Rack Grade Slab RCC Work', 'IBR Piperack', 'CUM', 35),
        ('I-30059', 'ibrPiperack', 'RCC Road dismantling work', 'IBR Piperack', 'CUM', 20),
        
        # I-2501F001 activities - Concrete section only
        ('I-2501F001', 'concrete', 'Pile Reinforcement Making Work', 'SM&FU', 'MT', 45),
        ('I-2501F001', 'concrete', 'Pile RCC Work', 'SM&FU', 'CUM', 565),
        ('I-2501F001', 'concrete', 'Pile Cap Excavation Work', 'SM&FU', 'CUM', 1500),
        ('I-2501F001', 'concrete', 'Pile Cap PCC Work', 'SM&FU', 'CUM', 90),
        ('I-2501F001', 'concrete', 'Pile Chipping Work', 'SM&FU', 'No', 97),
        ('I-2501F001', 'concrete', 'Pile PIT Test Work', 'SM&FU', 'No', 97),
        ('I-2501F001', 'concrete', 'Reinforcement Making Work', 'SM&FU', 'MT', 75)
    ]
    
    for activity in project_activities_data:
        # Get the database ID for the section
        section_db_id = cursor.execute('''
            SELECT id FROM project_sections 
            WHERE project_code = ? AND section_id = ?
        ''', (activity[0], activity[1])).fetchone()
        
        if section_db_id:
            cursor.execute('''
            INSERT OR IGNORE INTO project_activities 
            (project_code, section_id, activity_description, area, unit, total_qty_planned)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (activity[0], section_db_id[0], activity[2], activity[3], activity[4], activity[5]))
    
    # App settings
    app_settings_data = [
        ('app_title', 'Daily Progress Report', 'Application title displayed on the form'),
        ('company_logo', 'https://simonindia.com/assets/images/logo.png', 'Company logo URL'),
        ('admin_session_timeout', '3600', 'Admin session timeout in seconds'),
        ('default_admin_username', 'admin@simonindia.ai', 'Default admin username'),
        ('default_admin_password', 'Simon@54321', 'Default admin password (change immediately)')
    ]
    
    for setting in app_settings_data:
        cursor.execute('INSERT OR IGNORE INTO app_settings (setting_key, setting_value, description) VALUES (?, ?, ?)', setting)
    
    # Create default admin user (password: Simon@54321)
    import hashlib
    default_password = 'Simon@54321'
    password_hash = hashlib.sha256(default_password.encode()).hexdigest()
    
    cursor.execute('''
    INSERT OR IGNORE INTO admin_users (username, password_hash, email) 
    VALUES (?, ?, ?)
    ''', ('admin@simonindia.ai', password_hash, 'admin@simonindia.ai'))
    
    conn.commit()
    conn.close()
    
    print("Database initialized successfully!")
    print("Default admin credentials:")
    print("Username: admin@simonindia.ai")
    print("Password: Simon@54321")
    print("Please change the default password after first login.")

if __name__ == '__main__':
    init_database()
