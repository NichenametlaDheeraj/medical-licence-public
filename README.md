# Medical Agency Drug Licence Document Automation System

A full-stack web application designed for medical agencies, pharmaceutical retailers, wholesalers, and regulatory consultants to manage drug licence applications, maintain audit records, export structured data to Excel, and automatically generate official application PDF documents based on Indian Drug Regulatory standards (Form 20, Form 21, Form 20B, Form 21B, Building Owner Declarations, Pharmacist Declarations, and Appointment Letters).

---

## Key Features

1. **Dashboard & Application Analytics**
   - Summary statistics (Total Applications, Draft, Ready for Review, Generated Documents).
   - Real-time search across applicant name, business name, application number, or mobile number.
   - Multi-parameter filtering by constitution (Proprietorship, Partnership, LLP, Pvt Ltd), licence type (Retail, Wholesale, Both), and status.
   - Application management: Create, View, Edit, Duplicate, Archive, PDF generation, and Excel export.

2. **Streamlined Single-Page Application Form**
   - **Unified One-Page Experience**: All form sections are laid out on a single, continuous page without separate step pagination or wizard jumping. Quick anchor navigation pills allow 1-click smooth scrolling between sections.
   - **Section 1: Application Details** - Auto-generated application number (`MED-YYYY-NNNN`), application date, category (New, Renewal, Amendment), licence type (Retail, Wholesale, Both), and auto-checked licence forms (Form 20, 21, 20B, 21B).
   - **Section 2: Business Information** - Streamlined essential details: Firm name, trading name, business constitution, mobile, email, PAN, complete business address, district, and PIN code.
   - **Section 3: Business Constitution & Member Details** - Dynamic conditional sections:
     - *Proprietorship*: Full legal name, father/husband name, mobile, PAN, ID document, and residential address.
     - *Partnership*: Dedicated **Number of Partners / Members** input (minimum 2) with automated two-way synchronization, dynamic partner cards with Add/Remove controls, partner particulars (Legal Name, Father/Husband, Role, Mobile, PAN, Aadhaar/ID Document, Designated Partner & Authorized Signatory flags), and partnership deed date/registration.
     - *LLP / Private Limited*: Company/LLP name, CIN/LLPIN, registered office, and authorized signatory.
     - *Other*: Custom constitution description and details.
   - **Section 4: Premises & Storage Details** - Ownership type (Owned/Rented), premises name, area in sq. meters, storage facilities (refrigerator, AC), shop address, plan upload, and inline landlord details when rented.
   - **Section 5: Registered Pharmacist(s)** - Dynamic pharmacist cards with Add/Remove controls, qualifications (B.Pharm/D.Pharm), council registration number, validity date, mobile, and address.
   - **Section 6: Statutory Declarations** - Compact compliance table with pre-configured standard compliant answers (DCA compliance, rules understood, no convictions, no cancellations) and inline disclosure toggles.
   - **Sticky Action Bar** - Always-visible bottom action bar with "Save Application", "Save Draft", and "Cancel". Fully eliminates the payment step.

3. **ReportLab Automated PDF Document Generation**
   - Clean, professional document layout reproducing the provided draft template without hardcoded sample data:
     - **Document 1**: Drug Licence Application Form (Form 20 & Form 21 for Retail, Form 20B & 21B for Wholesale).
     - **Document 2**: Declaration of Building Owner (with photo box, attestation markers, and premises details).
     - **Document 3**: Declaration of Proprietor / Registered Pharmacist (with 15-row declaration grid, photo box, and verification).
     - **Document 4**: Appointment / Acceptance Letter.
   - Separate PDF generated for each application, organized by application ID in `generated_documents/<app_id>/`.
   - Outdated status tracking: Editing an application automatically flags prior documents as `outdated`.

4. **Multi-Sheet OpenPyXL Excel Export**
   - Professional styling with Navy headers, alternating grey rows, and auto-adjusted column widths.
   - **8 Sheets**:
     1. `Applications` (Core metadata, dates, licence forms, statuses)
     2. `Business Details` (Firm names, PANs, addresses, proprietor/corporate info)
     3. `Partners` (Numbered partner roster, designations, contacts)
     4. `Pharmacists` (Registration details, councils, validity, employment)
     5. `Premises` (Area, storage facilities, ownership, lease terms)
     6. `Building Owners` (Ownership documentation and landlord contacts)
     7. `Declarations` (Question keys, yes/no responses, detailed disclosures)
     8. `Payments` (Challans, amounts, statuses, and banks)

5. **Security & Data Integrity**
   - Flask-WTF CSRF protection enabled on all forms and action endpoints.
   - Secure file uploads with extension verification and per-application isolated directories.
   - Password hashing via Werkzeug security (`pbkdf2:sha256`).
   - SQLite relational database (`medical_agency.db`) via SQLAlchemy ORM with foreign key cascades and audit history logging.

---

## Technology Stack

- **Backend**: Python 3.10+, Flask 3.x
- **Database**: SQLite (`medical_agency.db` via SQLAlchemy 2.x ORM)
- **Authentication**: Flask-Login
- **Security & Forms**: Flask-WTF, WTForms
- **Excel Engine**: openpyxl
- **PDF Engine**: ReportLab
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Bootstrap Icons, Google Fonts (Inter)

---

## Installation & Setup

### 1. Clone or Open Workspace
```bash
cd e:\django\medical
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` (already configured by default):
```env
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///medical_agency.db
UPLOAD_FOLDER=uploads
GENERATED_FOLDER=generated_documents
MAX_CONTENT_LENGTH=10485760
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@medicalagency.com
```

### 4. Run the Development Server
```bash
python run.py
```
The application will start on: `http://localhost:5000`

---

## User Roles & Role-Based Access Control (RBAC)

The system enforces strict permission boundaries between **Administrator** and **Staff / Operator**:

| Feature / Action | Administrator (`admin`) | Staff / Operator (`staff`) |
| :--- | :---: | :---: |
| **Create & Edit Applications** | Allowed | Allowed |
| **Upload Certificates & Plans** | Allowed | Allowed |
| **Duplicate Applications** | Allowed | Allowed |
| **Export Data to Excel (Single & All)** | Allowed | Allowed |
| **Preview Documents** | Allowed | Allowed |
| **Generate Official PDFs** | Allowed | Hidden & Restricted |
| **Approve Applications** | Allowed | Hidden & Restricted |
| **Archive Applications** | Allowed | Hidden & Restricted |
| **Permanent Delete Applications** | Allowed | Hidden & Restricted |
| **User Management (`/admin/users`)** | Allowed | Hidden & Blocked |
| **System-wide Audit Logs (`/admin/audit-logs`)** | Allowed | Hidden & Blocked |
| **System Configuration (`/admin/system-info`)** | Allowed | Hidden & Blocked |

### Default Credentials

| Role | Username | Password | Email | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` | `admin@medicalagency.com` | Full administrative access, user management, audit logs, PDF generation & official approvals |
| **Staff / Operator** | `user` | `user123` | `user@medicalagency.com` | Standard operator for data entry and application draft management |

Both accounts are automatically seeded into the database on startup.

---

## Running Automated Tests

Run the built-in test suite:
```bash
python -m unittest tests/test_app.py -v
```

All 10 test cases verify:
1. `test_01_users_seeded`: Admin and user (staff) accounts exist with correct roles.
2. `test_02_application_crud`: Create, retrieve, and update applications.
3. `test_03_pdf_generation`: ReportLab PDF generation for all 4 document types.
4. `test_04_excel_export`: 8-sheet Excel workbook export with openpyxl.
5. `test_05_unauthenticated_redirect`: Unauthenticated access redirects to login.
6. `test_06_login_and_dashboard_access`: Login and dashboard metrics display.
7. `test_07_rbac_staff_restricted_from_admin`: Staff user blocked from `/admin/*`, archive, delete, and PDF generation.
8. `test_08_rbac_admin_full_access`: Admin user has full access to all admin tools.
9. `test_09_partnership_multiple_members_no_payment`: Partnership firm creation with 3 partners, member details, roles, flags, and complete omission of payment.
10. `test_10_rbac_staff_ui_separation`: Confirms staff UI does not render admin navigation, approve, archive, delete, or audit buttons.

---

## Project Structure

```
medical/
├── app/
│   ├── admin/                   # Admin user management & audit routes
│   ├── auth/                    # Authentication routes & handlers
│   ├── dashboard/               # Dashboard index & search/filter
│   ├── applications/            # Multi-step wizard (6 steps) & CRUD routes
│   ├── exports/                 # Excel export routes
│   ├── pdf_generator/           # PDF generation & preview routes
│   ├── models/                  # SQLAlchemy ORM models (11 models)
│   ├── services/
│   │   ├── application_service.py # Core business & sync logic
│   │   ├── excel_service.py     # 8-sheet openpyxl exporter
│   │   └── pdf_service.py       # ReportLab PDF document generator
│   ├── static/
│   │   ├── css/main.css         # Modern Navy/Green UI styling
│   │   └── js/main.js           # Client-side dynamic interactions
│   └── templates/
│       ├── base.html            # Main layout with role-based sidebar
│       ├── login.html           # Authentication screen
│       ├── dashboard.html       # Analytics & application table
│       ├── admin/               # User management, audit logs, system info
│       ├── applications/
│       │   ├── form.html        # 6-step wizard with dynamic partner counter & subforms
│       │   ├── list.html        # Filtered applications list
│       │   └── view.html        # Detailed application view with enhanced partner roster
│       └── pdf/
│           └── preview.html     # PDF document management & downloads
├── generated_documents/         # Output folder for generated PDFs & Excel
├── uploads/                     # Storage for user-uploaded documents
├── tests/                       # Automated test suite (10 tests)
├── app.py                       # Root application entry
├── run.py                       # Server runner
├── config.py                    # Environment configurations (SQLite)
├── app_extensions.py            # Centralized Flask extensions
├── requirements.txt             # Project dependencies
└── README.md                    # Project documentation
```
