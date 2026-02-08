import mysql.connector
import json
import os
from mysql.connector import errorcode
from config.database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize the MySQL database with schema and initial data"""
    
    conn = None
    cursor = None
    try:
        # Create database if not exists
        # Create database if not exists
        db_name = os.getenv("DB_NAME", os.getenv("MYSQL_DATABASE", "dpr_database"))
        db_user = os.getenv("DB_USER", os.getenv("MYSQL_USER", "root"))
        db_password = os.getenv("DB_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))
        db_host = os.getenv("DB_HOST", os.getenv("MYSQL_HOST", "localhost"))
        db_port = int(os.getenv("DB_PORT", os.getenv("MYSQL_PORT", 3306)))

        # Connect without database selected to create it
        try:
            conn = mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                port=db_port
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} DEFAULT CHARACTER SET utf8mb4")
            print(f"Database '{db_name}' created or already exists.")
            cursor.close()
            conn.close()
        except mysql.connector.Error as err:
            print(f"Error creating database: {err}")
            return

        # Now connect to the database using the config module (which uses the pool)
        # Note: The pool in config/database.py will use the env vars we just used.
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Disable foreign key checks temporarily to avoid issues during creation
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Create tables
        
        # Projects
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            manager VARCHAR(255) NOT NULL,
            project_manager_client VARCHAR(255) NOT NULL,
            client VARCHAR(255) NOT NULL,
            contractor VARCHAR(255) NOT NULL,
            report_id_fragment VARCHAR(50) NOT NULL,
            target_completion VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_project_code (code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Report Preparers
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS report_preparers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            designation VARCHAR(255) NOT NULL,
            project_code VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_code) REFERENCES projects (code) ON UPDATE CASCADE ON DELETE SET NULL,
            UNIQUE KEY unique_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Contractors
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contractors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            contractor_name VARCHAR(255) NOT NULL,
            project_code VARCHAR(50),
            contact_person VARCHAR(255),
            contact_details VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_code) REFERENCES projects (code) ON UPDATE CASCADE ON DELETE SET NULL,
            UNIQUE KEY unique_contractor (project_code, contractor_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Site Managers
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_managers (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            designation VARCHAR(255) NOT NULL,
            project_code VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_code) REFERENCES projects (code) ON UPDATE CASCADE ON DELETE SET NULL,
            UNIQUE KEY unique_manager_name (name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Departments
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Manpower Designations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS manpower_designations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            designation VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Equipment Descriptions
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS equipment_descriptions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            description VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Project Sections
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_sections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_code VARCHAR(50) NOT NULL,
            section_id VARCHAR(50) NOT NULL,
            section_name VARCHAR(255) NOT NULL,
            area VARCHAR(100),
            unit VARCHAR(50),
            total_qty_planned INT DEFAULT 0,
            order_index INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_section (project_code, section_id),
            FOREIGN KEY (project_code) REFERENCES projects (code) ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Project Activities
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_activities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_code VARCHAR(50) NOT NULL,
            section_id INT NOT NULL,
            activity_description VARCHAR(500) NOT NULL,
            area VARCHAR(100),
            unit VARCHAR(50) NOT NULL,
            total_qty_planned INT NOT NULL,
            order_index INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_code) REFERENCES projects (code) ON UPDATE CASCADE ON DELETE CASCADE,
            FOREIGN KEY (section_id) REFERENCES project_sections (id) ON UPDATE CASCADE ON DELETE CASCADE,
            UNIQUE KEY unique_activity (project_code, section_id, activity_description)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Admin Users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Daily Progress Reports
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_progress_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_code VARCHAR(50) NOT NULL,
            report_date VARCHAR(20) NOT NULL,
            activity_description VARCHAR(500) NOT NULL,
            planned_today INT DEFAULT 0,
            achieved_today INT DEFAULT 0,
            planned_cumulative INT DEFAULT 0,
            achieved_cumulative INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_report_entry (project_code, report_date, activity_description),
            INDEX idx_report_date (report_date),
            INDEX idx_project_date (project_code, report_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Submitted Reports
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS submitted_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            report_number VARCHAR(100) UNIQUE NOT NULL,
            project_code VARCHAR(50) NOT NULL,
            report_date VARCHAR(20) NOT NULL,
            project_name VARCHAR(255),
            prepared_by VARCHAR(255),
            checked_by VARCHAR(255),
            approved_by VARCHAR(255),
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            report_data LONGTEXT, -- JSON string of the complete form data
            UNIQUE KEY unique_submitted_report (project_code, report_date),
            FOREIGN KEY (project_code) REFERENCES projects (code) ON UPDATE CASCADE ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # App Settings
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')
        
        # Re-enable foreign key checks
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
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
            INSERT IGNORE INTO projects 
            (code, name, manager, project_manager_client, client, contractor, report_id_fragment, target_completion)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', project)
        
        # Report Preparers data
        report_preparers_data = [
            ('Saravanakumar B', 'Senior Engineer QA/QC (Civil)', 'I-30059'),
        ]
        
        for preparer in report_preparers_data:
            cursor.execute('INSERT IGNORE INTO report_preparers (name, designation, project_code) VALUES (%s, %s, %s)', preparer)
        
        # Contractors data
        contractors_data = [
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
            ('PIPL', 'I-2501F001', '', ''),
        ]
        
        for contractor in contractors_data:
            cursor.execute('INSERT IGNORE INTO contractors (contractor_name, project_code, contact_person, contact_details) VALUES (%s, %s, %s, %s)', contractor)
        
        # Site Managers data
        site_managers_data = [
            ('Biswaranjan Dash', 'Project Manager', 'I-30059'),
            ('Anupam Naik', 'Lead - Civil', 'I-30059'),
        ]
        
        for manager in site_managers_data:
            cursor.execute('INSERT IGNORE INTO site_managers (name, designation, project_code) VALUES (%s, %s, %s)', manager)
        
        # Departments data
        departments_data = [
            'Civil Team', 'Mechanical Team', 'Electrical Team', 
            'Safety Department', 'Logistics', 'Admin'
        ]
        
        for dept in departments_data:
            cursor.execute('INSERT IGNORE INTO departments (name) VALUES (%s)', (dept,))
        
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
            cursor.execute('INSERT IGNORE INTO manpower_designations (designation) VALUES (%s)', (designation,))
        
        # Equipment descriptions
        equipment_descriptions_data = [
            'Farana crane', 'Welding machine', '100 MT crane', 'Cutting machine',
            'Excavator', 'Barbending and cutting machine', 'Vibrator', 'Dewatering pump',
            'Blasting machine', 'Concrete Mixer', 'DMC'
        ]
        
        for equipment in equipment_descriptions_data:
            cursor.execute('INSERT IGNORE INTO equipment_descriptions (description) VALUES (%s)', (equipment,))
        
        # Project-specific sections
        project_sections_data = [
            ('I-30059', 'concrete', 'Concrete', '5th Evaporator Building', 'M3', 609),
            ('I-30059', 'steel', 'Structure Steel works', '5th Evaporator Building', 'MT', 356),
            ('I-30059', 'ctBasin', 'CT Basin', 'Cooling Tower', 'M3', 305),
            ('I-30059', 'ibrPiperack', 'IBR Pipe Rack', 'IBR Piperack', 'M3', 120),
            ('I-2501F001', 'concrete', 'Concrete', 'SM&FU', 'M3', 2469)
        ]
        
        for section in project_sections_data:
            cursor.execute('''
            INSERT IGNORE INTO project_sections 
            (project_code, section_id, section_name, area, unit, total_qty_planned)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''', section)
        
        # Project-specific activities
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
            
            # I-2501F001 activities
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
            cursor.execute('''
                SELECT id FROM project_sections 
                WHERE project_code = %s AND section_id = %s
            ''', (activity[0], activity[1]))
            section_db_id = cursor.fetchone()
            
            if section_db_id:
                cursor.execute('''
                INSERT IGNORE INTO project_activities 
                (project_code, section_id, activity_description, area, unit, total_qty_planned)
                VALUES (%s, %s, %s, %s, %s, %s)
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
            cursor.execute('INSERT IGNORE INTO app_settings (setting_key, setting_value, description) VALUES (%s, %s, %s)', setting)
        
        # Create default admin user
        import hashlib
        default_password = 'Simon@54321'
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()
        
        cursor.execute('''
        INSERT IGNORE INTO admin_users (username, password_hash, email) 
        VALUES (%s, %s, %s)
        ''', ('admin@simonindia.ai', password_hash, 'admin@simonindia.ai'))
        
        conn.commit()
        print("MySQL database initialized successfully with schema and default data!")
        
    except mysql.connector.Error as err:
        print(f"Error initializing database: {err}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    init_database()
