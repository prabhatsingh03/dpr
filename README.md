# Daily Progress Report (DPR) Management System

A Flask-based web application for managing Daily Progress Reports with dynamic data management through an admin interface.

## Features

- **Dynamic Form Management**: All constants (projects, staff, departments, contractors, activities) are stored in SQLite database
- **Admin Authentication**: Secure login system for administrators
- **Admin Dashboard**: Complete interface to manage all form data
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: Changes in admin panel reflect immediately in the main form

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database

Run the database initialization script to create tables and populate with initial data:

```bash
python init_database.py
```

This will create `dpr_database.db` with all the constants from the original HTML form.

### 3. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

**⚠️ Important**: Change the default password immediately after first login for security.

## Application Structure

```
dpr/
├── app.py                 # Main Flask application
├── init_database.py       # Database initialization script
├── requirements.txt       # Python dependencies
├── dpr_database.db       # SQLite database (created after initialization)
├── templates/            # HTML templates
│   ├── index.html        # Main DPR form
│   ├── admin_login.html  # Admin login page
│   ├── admin_dashboard.html # Admin dashboard
│   ├── admin_projects.html  # Project management
│   ├── admin_staff.html     # Staff management
│   ├── admin_departments.html # Department management
│   ├── admin_contractors.html # Contractor management
│   └── admin_activities.html  # Activity management
└── README.md             # This file
```

## Usage

### Main Form
1. Visit `http://localhost:5000` to access the DPR form
2. All dropdowns and options are dynamically loaded from the database
3. Admin login button is available in the top-right navbar

### Admin Panel
1. Click "Admin Login" in the navbar or visit `http://localhost:5000/admin/login`
2. Login with admin credentials
3. Navigate through different management sections:
   - **Projects**: Manage project codes, names, managers, clients, etc.
   - **Staff**: Manage staff members and their designations
   - **Departments**: Manage department names
   - **Contractors**: Manage contractor names
   - **Activities**: Manage work activities by category

### Admin Features
- **Add**: Create new entries in any category
- **Edit**: Modify existing entries
- **Delete**: Remove entries (with confirmation)
- **Real-time Updates**: Changes reflect immediately in the main form

## Database Schema

The application uses SQLite with the following main tables:
- `projects` - Project information
- `staff` - Staff members and designations
- `departments` - Department names
- `contractors` - Contractor names
- `manpower_designations` - Available manpower roles
- `equipment_descriptions` - Equipment types
- `activity_categories` - Work categories (Concrete, Steel, etc.)
- `activities` - Specific activities within categories
- `admin_users` - Admin authentication
- `app_settings` - Application configuration

## Security Notes

1. **Change Default Password**: The default admin password should be changed immediately
2. **Environment Variables**: In production, set `SECRET_KEY` environment variable
3. **Database Security**: Ensure database file has appropriate permissions
4. **HTTPS**: Use HTTPS in production environments

## API Endpoints

The application provides REST API endpoints for data access:
- `GET /api/projects` - Get all projects
- `GET /api/staff` - Get all staff members
- `GET /api/departments` - Get all departments
- `GET /api/contractors` - Get all contractors
- `GET /api/manpower-designations` - Get manpower roles
- `GET /api/equipment-descriptions` - Get equipment types
- `GET /api/activities` - Get all activities by category
- `GET /api/admin/status` - Check admin login status

## Troubleshooting

### Database Issues
- If database doesn't exist, run `python init_database.py`
- If data is missing, delete `dpr_database.db` and re-run initialization

### Login Issues
- Ensure you're using correct credentials: `admin` / `admin123`
- Clear browser cookies if session issues occur

### Form Not Loading Data
- Check browser console for JavaScript errors
- Verify Flask app is running and APIs are accessible
- Ensure database has been initialized

## Development

To modify the application:
1. **Add New Fields**: Update database schema in `init_database.py`
2. **New Admin Sections**: Create new routes in `app.py` and corresponding templates
3. **Frontend Changes**: Modify templates in the `templates/` directory

## License

This project is for internal use by SIMON India Limited.

