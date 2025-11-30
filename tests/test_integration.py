# tests/test_integration.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from algorithms.integration import get_user_recommendations, moderate_post_content

User = get_user_model()

class AlgorithmIntegrationTest(TestCase):
    def setUp(self):
        self.fan = User.objects.create_user(
            username='testfan',
            email='fan@test.com',
            password='testpass123',
            user_type='fan'
        )
        self.celebrity = User.objects.create_user(
            username='testceleb',
            email='celeb@test.com',
            password='testpass123',
            user_type='celebrity'
        )
    
    def test_recommendations_generation(self):
        """Test recommendation generation"""
        recommendations = get_user_recommendations(self.fan, 'celebrities', limit=5)
        self.assertIsNotNone(recommendations)
        self.assertIn('celebrities', recommendations)
    
    def test_content_moderation(self):
        """Test content moderation"""
        # Test toxic content
        toxic_content = "I hate you, you're stupid and worthless!"
        result = moderate_post_content(toxic_content)
        self.assertTrue(result['should_block'])
        
        # Test normal content
        normal_content = "Had a great day at the concert!"
        result = moderate_post_content(normal_content)
        self.assertFalse(result['should_block'])
    
    def test_payment_simulation(self):
        """Test payment simulation"""
        from apps.payments.models import PaymentSimulation
        
        payment = PaymentSimulation.objects.create(
            user=self.fan,
            celebrity=self.celebrity,
            amount=100.00,
            payment_method='esewa',
            payment_for='merchandise',
            reference_id='test123'
        )
        
        success = payment.simulate_payment()
        self.assertIn(payment.payment_status, ['success', 'failed'])
        if success:
            self.assertIsNotNone(payment.transaction_id)