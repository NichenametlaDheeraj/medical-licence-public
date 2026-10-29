"""
tests/test_app.py — Test suite for Medical Agency Drug Licence Automation System
Standard library unittest implementation for zero-dependency execution.
"""
import os
import sys
import unittest
from datetime import date

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app_extensions import db
from app.models.user import User
from app.models.application import Application
from app.services.application_service import create_application, get_application
from app.services.pdf_service import generate_all_documents
from app.services.excel_service import export_to_excel


class TestMedicalAgencyApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('development')
        cls.app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
        })
        cls.client = cls.app.test_client()

    def setUp(self):
        with self.app.app_context():
            from werkzeug.security import generate_password_hash
            u = User.query.filter_by(username='user').first()
            if u:
                u.is_active = True
                u.password_hash = generate_password_hash('user123')
            adm = User.query.filter_by(username='admin').first()
            if adm:
                adm.is_active = True
                adm.password_hash = generate_password_hash('admin123')
            db.session.commit()

    def test_01_users_seeded(self):
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            self.assertIsNotNone(admin)
            self.assertEqual(admin.role, 'admin')

            staff = User.query.filter_by(username='user').first()
            self.assertIsNotNone(staff)
            self.assertIn(staff.role, ('user', 'staff'))

    def test_02_application_crud(self):
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            data = {
                'licence_category': 'new_licence',
                'licence_type': 'retail',
                'licence_forms': 'Form20,Form21',
                'status': 'draft',
                'business_constitution': 'proprietorship',
                'app_date': date.today(),
                'firm_name': 'UNITTEST DRUG AGENCY',
                'mobile': '9876543210',
                'district': 'YSR Kadapa',
                'proprietor_name': 'Test Proprietor',
                'premises': {
                    'ownership_type': 'owned',
                    'shop_name': 'UNITTEST DRUG AGENCY',
                    'district': 'YSR Kadapa',
                },
                'pharmacists': [
                    {
                        'full_name': 'Test Pharmacist',
                        'registration_number': 'AP-PH-999',
                        'qualification': 'B. Pharm',
                    }
                ],
                'declarations': [
                    {'question_key': 'dca_compliance', 'answer': 'yes'}
                ],
                'payment': {
                    'challan_number': 'CH-9999',
                    'amount': 3000.0,
                    'payment_status': 'paid',
                }
            }
            app_obj = create_application(data, admin.id)
            self.assertIsNotNone(app_obj.id)
            self.assertTrue(app_obj.app_number.startswith('MED-'))
            self.assertEqual(app_obj.business_details.firm_name, 'UNITTEST DRUG AGENCY')
            self.assertEqual(len(app_obj.pharmacists), 1)

            retrieved = get_application(app_obj.id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.id, app_obj.id)

    def test_03_pdf_generation(self):
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            app_obj = Application.query.first()
            self.assertIsNotNone(app_obj)

            docs = generate_all_documents(app_obj, admin.id)
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0].document_type, 'complete_dossier')

            gen_folder = self.app.config['GENERATED_FOLDER']
            for doc in docs:
                self.assertEqual(doc.status, 'current')
                full_path = os.path.join(gen_folder, doc.filename)
                self.assertTrue(os.path.exists(full_path))
                self.assertGreater(os.path.getsize(full_path), 0)
                self.assertTrue(doc.filename.endswith('_Draft.pdf'))

    def test_04_excel_export(self):
        with self.app.app_context():
            apps = Application.query.all()
            self.assertGreater(len(apps), 0)

            gen_folder = self.app.config['GENERATED_FOLDER']
            out_path = os.path.join(gen_folder, 'unittest_export.xlsx')
            exported_path = export_to_excel(apps, out_path)
            self.assertTrue(os.path.exists(exported_path))
            self.assertGreater(os.path.getsize(exported_path), 0)

    def test_05_unauthenticated_redirect(self):
        resp = self.client.get('/', follow_redirects=False)
        self.assertIn(resp.status_code, (302, 401))

    def test_06_login_and_dashboard_access(self):
        resp = self.client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Total Applications', resp.data)

    def test_07_rbac_staff_restricted_from_admin(self):
        # Logout any existing session first
        self.client.get('/auth/logout')

        # Login as staff
        self.client.post('/auth/login', data={
            'username': 'user',
            'password': 'user123'
        }, follow_redirects=True)

        # Staff blocked from Admin User Management
        resp = self.client.get('/admin/users', follow_redirects=True)
        self.assertIn(b'Access denied', resp.data)

        # Staff blocked from Admin Audit Logs
        resp = self.client.get('/admin/audit-logs', follow_redirects=True)
        self.assertIn(b'Access denied', resp.data)

        # Staff blocked from Archiving and PDF generation
        with self.app.app_context():
            app_obj = Application.query.filter_by(is_archived=False).first()
            if app_obj:
                resp = self.client.post(f'/applications/{app_obj.id}/archive', follow_redirects=True)
                self.assertIn(b'Access denied', resp.data)

                resp = self.client.post(f'/pdf/generate/{app_obj.id}', follow_redirects=True)
                self.assertIn(b'Access denied', resp.data)

    def test_08_rbac_admin_full_access(self):
        # Logout staff session
        self.client.get('/auth/logout')

        # Login as admin
        self.client.post('/auth/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(b'Logged In Users' in resp.data or b'User Management' in resp.data)

        resp = self.client.get('/admin/audit-logs')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Audit Logs', resp.data)

    def test_09_partnership_multiple_members_no_payment(self):
        # Login as user/staff
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'user', 'password': 'user123'}, follow_redirects=True)

        post_data = {
            'application_category': 'new_licence',
            'licence_type': 'retail',
            'licence_forms': ['Form20', 'Form21'],
            'status': 'draft',
            'business_constitution': 'partnership',
            'app_date': date.today().isoformat(),
            'firm_name': 'KADAPA PHARMA PARTNERS',
            'mobile': '9876543210',
            'email': 'contact@kadapapharma.com',
            'ownership_type': 'rented',
            'shop_name': 'KADAPA PHARMA PARTNERS',
            'shop_address': 'Shop 12, Main Bazaar, Kadapa',
            # 3 Partners
            'partner_name[]': ['Dr. Ramesh Kumar', 'Suresh Babu', 'Mahesh Reddy'],
            'partner_father[]': ['K. Venkat Rao', 'K. Venkat Rao', 'M. Ramaiah'],
            'partner_role[]': ['Managing Partner', 'Partner', 'Partner'],
            'partner_pan[]': ['ABCDE1234F', 'FGHIJ5678K', 'LMNOP9012Q'],
            'partner_mobile[]': ['9848011111', '9848022222', '9848033333'],
            'partner_email[]': ['ramesh@pharma.com', 'suresh@pharma.com', 'mahesh@pharma.com'],
            'partner_address[]': ['Kadapa', 'Kadapa', 'Kadapa'],
            'partner_id_doc[]': ['Aadhaar: 1234-5678-9012', 'Voter: ABC1234567', 'Passport: Z9876543'],
            'partner_designated[]': ['1', '3'],
            'partner_auth_signatory[]': ['1'],
            # Pharmacist
            'pharma_name[]': ['G. Srinivas'],
            'pharma_reg_no[]': ['AP-12345'],
            'pharma_qual[]': ['B.Pharm'],
            # Declarations
            'decl_dca_compliance': 'yes',
            'decl_rules_understood': 'yes',
            # NOTE: No payment data sent!
        }

        resp = self.client.post('/applications/new', data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.app.app_context():
            app_obj = Application.query.filter_by(business_constitution='partnership').order_by(Application.id.desc()).first()
            self.assertIsNotNone(app_obj)
            self.assertEqual(app_obj.business_details.firm_name, 'KADAPA PHARMA PARTNERS')
            self.assertEqual(len(app_obj.partners), 3)

            p1 = app_obj.partners[0]
            self.assertEqual(p1.full_name, 'Dr. Ramesh Kumar')
            self.assertEqual(p1.role, 'Managing Partner')
            self.assertTrue(p1.is_designated_partner)
            self.assertTrue(p1.is_authorized_signatory)
            self.assertEqual(p1.id_doc_details, 'Aadhaar: 1234-5678-9012')

            p2 = app_obj.partners[1]
            self.assertEqual(p2.full_name, 'Suresh Babu')
            self.assertFalse(p2.is_designated_partner)
            self.assertFalse(p2.is_authorized_signatory)

            p3 = app_obj.partners[2]
            self.assertEqual(p3.full_name, 'Mahesh Reddy')
            self.assertTrue(p3.is_designated_partner)
            self.assertFalse(p3.is_authorized_signatory)

            # Check view page
            view_resp = self.client.get(f'/applications/{app_obj.id}')
            self.assertEqual(view_resp.status_code, 200)
            self.assertIn(b'Partners / Members (3)', view_resp.data)
            self.assertIn(b'Dr. Ramesh Kumar', view_resp.data)
            self.assertIn(b'Suresh Babu', view_resp.data)
            self.assertIn(b'Mahesh Reddy', view_resp.data)
            # Confirm Payment card is NOT displayed
            self.assertNotIn(b'Challan / Payment Details', view_resp.data)

    def test_10_rbac_staff_ui_separation(self):
        # Staff logged in
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'user', 'password': 'user123'}, follow_redirects=True)

        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        # Admin navigation links MUST NOT appear for staff
        self.assertNotIn(b'href="/admin/users"', resp.data)
        self.assertNotIn(b'href="/admin/audit-logs"', resp.data)
        self.assertNotIn(b'ADMINISTRATION', resp.data)

        # In application view, staff must NOT see admin-only action buttons on their own application
        with self.app.app_context():
            user_obj = User.query.filter_by(username='user').first()
            user_app = Application.query.filter_by(created_by=user_obj.id).first()
            if user_app:
                view_resp = self.client.get(f'/applications/{user_app.id}')
                self.assertEqual(view_resp.status_code, 200)
                self.assertNotIn(b'Generate Draft.pdf', view_resp.data)
                self.assertNotIn(b'Approve Application', view_resp.data)
                self.assertNotIn(b'Archive Application', view_resp.data)
                self.assertNotIn(b'Delete Application', view_resp.data)
                self.assertNotIn(b'Audit History', view_resp.data)

    def test_11_user_account_creation_registration(self):
        self.client.get('/auth/logout')

        # Clean up any previous test user
        with self.app.app_context():
            old = User.query.filter_by(username='newstaff').first()
            if old:
                db.session.delete(old)
                db.session.commit()

        # Test GET /auth/register
        resp = self.client.get('/auth/register')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Create User Account', resp.data)

        # Test password mismatch failure
        resp = self.client.post('/auth/register', data={
            'username': 'newstaff',
            'email': 'newstaff@example.com',
            'password': 'password123',
            'confirm_password': 'password999',
        }, follow_redirects=True)
        self.assertIn(b'Passwords do not match', resp.data)

        # Test successful account creation
        resp = self.client.post('/auth/register', data={
            'username': 'newstaff',
            'email': 'newstaff@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Account created successfully', resp.data)

        # Verify new user role is 'user'
        with self.app.app_context():
            u = User.query.filter_by(username='newstaff').first()
            self.assertIsNotNone(u)
            self.assertIn(u.role, ('user', 'staff'))
            self.assertEqual(u.email, 'newstaff@example.com')

        # Test duplicate username blocked
        self.client.get('/auth/logout')
        resp = self.client.post('/auth/register', data={
            'username': 'newstaff',
            'email': 'different@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow_redirects=True)
        self.assertIn(b'Username is already taken', resp.data)

        # Clean up created user after test
        with self.app.app_context():
            cleanup = User.query.filter_by(username='newstaff').first()
            if cleanup:
                db.session.delete(cleanup)
                db.session.commit()

    def test_12_user_cannot_see_other_applications(self):
        # 1. Login as staff ('user')
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'user', 'password': 'user123'}, follow_redirects=True)

        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            user = User.query.filter_by(username='user').first()
            admin_app = Application.query.filter_by(created_by=admin.id, is_archived=False).first()
            user_app = Application.query.filter_by(created_by=user.id, is_archived=False).first()

            self.assertIsNotNone(admin_app)
            self.assertIsNotNone(user_app)

            # Dashboard should NOT contain admin_app's app_number or firm_name
            resp = self.client.get('/')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(user_app.app_number.encode(), resp.data)
            self.assertNotIn(admin_app.app_number.encode(), resp.data)
            if admin_app.business_details and admin_app.business_details.firm_name:
                self.assertNotIn(admin_app.business_details.firm_name.encode(), resp.data)

            # Applications list should NOT contain admin_app
            resp_list = self.client.get('/applications/')
            self.assertEqual(resp_list.status_code, 200)
            self.assertIn(user_app.app_number.encode(), resp_list.data)
            self.assertNotIn(admin_app.app_number.encode(), resp_list.data)

            # Direct access to view other's application is blocked
            view_resp = self.client.get(f'/applications/{admin_app.id}', follow_redirects=True)
            self.assertIn(b'Access denied', view_resp.data)

            # Direct access to edit other's application is blocked
            edit_resp = self.client.get(f'/applications/{admin_app.id}/edit', follow_redirects=True)
            self.assertIn(b'Access denied', edit_resp.data)

            # Duplicate other's application is blocked
            dup_resp = self.client.post(f'/applications/{admin_app.id}/duplicate', follow_redirects=True)
            self.assertIn(b'Access denied', dup_resp.data)

            # Export single other's application is blocked
            exp_resp = self.client.get(f'/exports/application/{admin_app.id}', follow_redirects=True)
            self.assertIn(b'Access denied', exp_resp.data)

        # 2. Login as admin - Admin CAN see all applications
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        resp_admin = self.client.get('/')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn(admin_app.app_number.encode(), resp_admin.data)
        self.assertIn(user_app.app_number.encode(), resp_admin.data)

    def test_13_user_change_password(self):
        # 1. Login as user
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'user', 'password': 'user123'}, follow_redirects=True)

        # 2. View change password page
        resp = self.client.get('/auth/change-password')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Update Account Password', resp.data)

        # 3. Wrong current password fails
        resp_wrong = self.client.post('/auth/change-password', data={
            'current_password': 'wrongpassword',
            'new_password': 'newsecret123',
            'confirm_password': 'newsecret123'
        }, follow_redirects=True)
        self.assertIn(b'Current password is incorrect', resp_wrong.data)

        # 4. Successful password change
        resp_success = self.client.post('/auth/change-password', data={
            'current_password': 'user123',
            'new_password': 'newsecret123',
            'confirm_password': 'newsecret123'
        }, follow_redirects=True)
        self.assertIn(b'Your password has been changed successfully', resp_success.data)

        # 5. Verify login with new password
        self.client.get('/auth/logout')
        login_new = self.client.post('/auth/login', data={
            'username': 'user',
            'password': 'newsecret123'
        }, follow_redirects=True)
        self.assertEqual(login_new.status_code, 200)
        self.assertIn(b'Welcome back', login_new.data)

        # Restore original password for test consistency
        self.client.post('/auth/change-password', data={
            'current_password': 'newsecret123',
            'new_password': 'user123',
            'confirm_password': 'user123'
        }, follow_redirects=True)

    def test_14_admin_toggle_user_status(self):
        # 1. Login as admin
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        with self.app.app_context():
            u = User.query.filter_by(username='user').first()
            self.assertTrue(u.is_active)

            # 2. Admin deactivates user
            resp = self.client.post(f'/admin/users/{u.id}/toggle-status', follow_redirects=True)
            self.assertIn(b'deactivated', resp.data)

            # 3. Verify user is now inactive
            u_updated = User.query.filter_by(username='user').first()
            self.assertFalse(u_updated.is_active)

        # 4. Deactivated user tries to log in
        self.client.get('/auth/logout')
        resp_login = self.client.post('/auth/login', data={'username': 'user', 'password': 'user123'}, follow_redirects=True)
        self.assertIn(b'is disabled', resp_login.data)

        # 5. Admin reactivates user
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        with self.app.app_context():
            u = User.query.filter_by(username='user').first()
            resp2 = self.client.post(f'/admin/users/{u.id}/toggle-status', follow_redirects=True)
            self.assertIn(b'activated', resp2.data)
            u_reactivated = User.query.filter_by(username='user').first()
            self.assertTrue(u_reactivated.is_active)

    def test_15_forgot_password_flow(self):
        # 1. Ensure logged out
        self.client.get('/auth/logout')

        # 2. View forgot password page
        resp_get = self.client.get('/auth/forgot-password')
        self.assertEqual(resp_get.status_code, 200)
        self.assertIn(b'Forgot Password', resp_get.data)

        # 3. Non-existent username fails
        resp_invalid = self.client.post('/auth/forgot-password', data={
            'identifier': 'nonexistentuser999'
        }, follow_redirects=True)
        self.assertIn(b'No account found', resp_invalid.data)

        # 4. Valid username succeeds and redirects to reset-password
        resp_valid = self.client.post('/auth/forgot-password', data={
            'identifier': 'user'
        }, follow_redirects=False)
        self.assertEqual(resp_valid.status_code, 302)
        reset_url = resp_valid.headers['Location']
        self.assertIn('/auth/reset-password/', reset_url)

        # 5. Access reset-password page
        resp_reset_page = self.client.get(reset_url)
        self.assertEqual(resp_reset_page.status_code, 200)
        self.assertIn(b'Set New Password', resp_reset_page.data)
        self.assertIn(b'user', resp_reset_page.data)

        # 6. Mismatched passwords fail
        resp_mismatch = self.client.post(reset_url, data={
            'new_password': 'mypassword123',
            'confirm_password': 'mismatchpassword'
        }, follow_redirects=True)
        self.assertIn(b'Passwords do not match', resp_mismatch.data)

        # 7. Valid password reset succeeds
        resp_success = self.client.post(reset_url, data={
            'new_password': 'recoveredpass123',
            'confirm_password': 'recoveredpass123'
        }, follow_redirects=True)
        self.assertIn(b'Password reset successfully', resp_success.data)

        # 8. Login with recovered password succeeds
        login_resp = self.client.post('/auth/login', data={
            'username': 'user',
            'password': 'recoveredpass123'
        }, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn(b'Welcome back', login_resp.data)

        # 9. Invalid token fails (must be logged out to test reset page for guests)
        self.client.get('/auth/logout')
        invalid_token_resp = self.client.get('/auth/reset-password/fake-expired-token', follow_redirects=True)
        self.assertIn(b'invalid or has expired', invalid_token_resp.data)

        # Restore user password for future test runs
        with self.app.app_context():
            from werkzeug.security import generate_password_hash
            u = User.query.filter_by(username='user').first()
            if u:
                u.password_hash = generate_password_hash('user123')
                db.session.commit()

    def test_16_excel_sync_and_update_flow(self):
        # 1. Staff user first export
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'user', 'password': 'user123'}, follow_redirects=True)

        resp1 = self.client.get('/exports/all')
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp1.headers.get('X-Export-Name'), 'my_applications.xlsx')
        self.assertIn('attachment; filename=my_applications.xlsx', resp1.headers.get('Content-Disposition', ''))

        # Check file was created on server
        with self.app.app_context():
            u = User.query.filter_by(username='user').first()
            user_server_path = os.path.join(self.app.config['GENERATED_FOLDER'], f'my_applications_user_{u.id}.xlsx')
            self.assertTrue(os.path.exists(user_server_path))

        # 2. Staff user second export (update already downloaded)
        resp2 = self.client.get('/exports/all')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.headers.get('X-Export-Name'), 'my_applications.xlsx')

        # Check status endpoint
        status_resp = self.client.get('/exports/status')
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.get_json()
        self.assertTrue(status_data['has_exported'])
        self.assertEqual(status_data['download_name'], 'my_applications.xlsx')

        # 3. Admin user export
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        admin_resp = self.client.get('/exports/all')
        self.assertEqual(admin_resp.status_code, 200)
        self.assertEqual(admin_resp.headers.get('X-Export-Name'), 'all_applications.xlsx')
        self.assertIn('attachment; filename=all_applications.xlsx', admin_resp.headers.get('Content-Disposition', ''))

        admin_status_resp = self.client.get('/exports/status')
        self.assertEqual(admin_status_resp.status_code, 200)
        admin_status_data = admin_status_resp.get_json()
        self.assertTrue(admin_status_data['has_exported'])
        self.assertEqual(admin_status_data['download_name'], 'all_applications.xlsx')


if __name__ == '__main__':
    unittest.main()
