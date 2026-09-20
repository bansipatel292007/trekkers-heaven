import unittest
import json
import os
import app
import database

class AuthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.app.config['TESTING'] = True
        app.app.config['SECRET_KEY'] = 'test-secret-key'
        cls.test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_users.db')
        database.DB_PATH = cls.test_db
        if os.path.exists(cls.test_db):
            try: os.remove(cls.test_db)
            except OSError: pass
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'test_db') and os.path.exists(cls.test_db):
            try: os.remove(cls.test_db)
            except OSError: pass

    def setUp(self):
        self.client = app.app.test_client()

    def test_01_index_page_loads(self):
        """Test that the main page loads successfully."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create an account', response.data)
        self.assertIn(b'Google', response.data)
        self.assertIn(b'Apple', response.data)

    def test_02_register_user_success(self):
        """Test registering a new user with Name, Email, Password."""
        payload = {
            'name': 'Alex Mercer',
            'email': 'alex.mercer@example.com',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }
        response = self.client.post('/register', json=payload)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('redirect', data)

        # Verify in database
        user = database.get_user_by_email('alex.mercer@example.com')
        self.assertIsNotNone(user)
        self.assertEqual(user['name'], 'Alex Mercer')

    def test_03_register_duplicate_email(self):
        """Test that registering duplicate email fails cleanly."""
        payload = {
            'name': 'Alex Mercer 2',
            'email': 'alex.mercer@example.com',
            'password': 'AnotherPassword123!',
            'confirm_password': 'AnotherPassword123!'
        }
        response = self.client.post('/register', json=payload)
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    def test_04_login_success(self):
        """Test valid user login."""
        payload = {
            'email': 'alex.mercer@example.com',
            'password': 'StrongPassword123!'
        }
        response = self.client.post('/login', json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

    def test_05_login_invalid_password(self):
        """Test login with incorrect password."""
        payload = {
            'email': 'alex.mercer@example.com',
            'password': 'WrongPassword999'
        }
        response = self.client.post('/login', json=payload)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data['success'])

    def test_06_check_email_api(self):
        """Test check email API availability."""
        # Existing email
        res1 = self.client.post('/api/check-email', json={'email': 'alex.mercer@example.com'})
        data1 = json.loads(res1.data)
        self.assertFalse(data1['available'])

        # New email
        res2 = self.client.post('/api/check-email', json={'email': 'brandnew@example.com'})
        data2 = json.loads(res2.data)
        self.assertTrue(data2['available'])

    def test_07_dashboard_protected(self):
        """Test dashboard requires authentication."""
        # Unauthenticated request
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.headers['Location'])

    def test_08_treks_page(self):
        """Test that the Treks Explorer page loads with treks."""
        response = self.client.get('/treks')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Kedarkantha Trek', response.data)
        self.assertIn(b'Everest Base Camp', response.data)
        self.assertIn(b'Filter Treks', response.data)

    def test_09_treks_api(self):
        """Test the Treks JSON API endpoint."""
        response = self.client.get('/api/treks')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 5)
        self.assertEqual(data[0]['name'], 'Kedarkantha Trek')

    def test_10_update_user_profile(self):
        """Test updating profile details on dashboard."""
        # Login first
        self.client.post('/login', json={'email': 'alex.mercer@example.com', 'password': 'StrongPassword123!'})
        
        # Submit updated profile details
        profile_data = {
            'name': 'Alex Mercer Pro',
            'phone': '+91 9876543210',
            'birthdate': '2000-05-15',
            'age': '26',
            'city': 'Dehradun',
            'state': 'Uttarakhand',
            'country': 'India'
        }
        response = self.client.post('/dashboard', json=profile_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])

        # Verify updated values
        user = database.get_user_by_email('alex.mercer@example.com')
        self.assertEqual(user['name'], 'Alex Mercer Pro')
        self.assertEqual(user['phone'], '+91 9876543210')
        self.assertEqual(user['birthdate'], '2000-05-15')
        self.assertEqual(user['city'], 'Dehradun')
        self.assertEqual(user['state'], 'Uttarakhand')
        self.assertEqual(user['country'], 'India')

    def test_11_change_password(self):
        """Test change password API."""
        self.client.post('/login', json={'email': 'alex.mercer@example.com', 'password': 'StrongPassword123!'})
        
        # Change password
        pwd_payload = {
            'current_password': 'StrongPassword123!',
            'new_password': 'BrandNewPassword456!',
            'confirm_new_password': 'BrandNewPassword456!'
        }
        res = self.client.post('/api/user/change-password', json=pwd_payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])

        # Logout and test login with new password
        self.client.get('/logout')
        login_res = self.client.post('/login', json={'email': 'alex.mercer@example.com', 'password': 'BrandNewPassword456!'})
        self.assertEqual(login_res.status_code, 200)

    def test_12_achievements_api(self):
        """Test adding and retrieving user achievements."""
        self.client.post('/login', json={'email': 'alex.mercer@example.com', 'password': 'BrandNewPassword456!'})
        
        ach_payload = {
            'trek_id': 'kedarkantha',
            'trek_name': 'Kedarkantha Trek',
            'start_date': '2026-01-10',
            'end_date': '2026-01-15'
        }
        res = self.client.post('/api/user/achievements', json=ach_payload)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['achievements']), 1)
        
        # Verify enrichment
        first_ach = data['achievements'][0]
        self.assertEqual(first_ach['trek_name'], 'Kedarkantha Trek')
        self.assertTrue(first_ach['duration_text'])

    def test_13_delete_achievement(self):
        """Test deleting a user achievement."""
        self.client.post('/login', json={'email': 'alex.mercer@example.com', 'password': 'BrandNewPassword456!'})
        
        get_res = self.client.get('/api/user/achievements')
        data = json.loads(get_res.data)
        self.assertTrue(data['success'])
        if data['achievements']:
            ach_id = data['achievements'][0]['id']
            del_res = self.client.delete(f'/api/user/achievements/{ach_id}')
            self.assertEqual(del_res.status_code, 200)
            del_data = json.loads(del_res.data)
            self.assertTrue(del_data['success'])

    def test_14_chat_api(self):
        """Test Sherpa AI chat endpoint."""
        res = self.client.post('/api/chat', json={'message': 'What permits are required for Kedarkantha?'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('reply', data)
        self.assertIn('suggestions', data)

    def test_15_trek_guide_api(self):
        """Test Trek Guide & Itinerary PDF data endpoint."""
        res = self.client.get('/api/treks/kedarkantha/guide')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertIn('trek', data)
        self.assertEqual(data['trek']['id'], 'kedarkantha')
        self.assertIn('permits', data)
        self.assertIn('permits_required', data['permits'])
        self.assertIn('emergency_sos', data)
        self.assertIn('helpline_india', data['emergency_sos'])

    def test_16_trek_guide_not_found(self):
        """Test Trek Guide endpoint with invalid trek id."""
        res = self.client.get('/api/treks/non-existent-trek-999/guide')
        self.assertEqual(res.status_code, 404)
        data = json.loads(res.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Trek not found')

if __name__ == '__main__':
    unittest.main()

