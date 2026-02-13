"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def setup_activities(client):
    """Reset activities before each test"""
    # Get activities to ensure consistent state
    response = client.get("/activities")
    assert response.status_code == 200
    return response.json()


class TestActivitiesEndpoint:
    """Tests for the /activities GET endpoint"""
    
    def test_get_activities_returns_200(self, client):
        """Test that /activities returns a 200 status code"""
        response = client.get("/activities")
        assert response.status_code == 200
    
    def test_get_activities_returns_dict(self, client):
        """Test that /activities returns a dictionary"""
        response = client.get("/activities")
        assert isinstance(response.json(), dict)
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupEndpoint:
    """Tests for the /activities/{activity_name}/signup POST endpoint"""
    
    def test_signup_for_valid_activity(self, client, setup_activities):
        """Test signing up for a valid activity"""
        response = client.post(
            "/activities/Music%20club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test that signing up for nonexistent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_cannot_signup_twice(self, client, setup_activities):
        """Test that a student cannot sign up twice for the same activity"""
        email = "newstudent@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Drama%20Club/signup?email=" + email
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Drama%20Club/signup?email=" + email
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_response_format(self, client, setup_activities):
        """Test that signup response has correct format"""
        response = client.post(
            "/activities/Basketball%20Team/signup?email=newplayer@mergington.edu"
        )
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)


class TestUnregisterEndpoint:
    """Tests for the /activities/{activity_name}/unregister POST endpoint"""
    
    def test_unregister_existing_participant(self, client, setup_activities):
        """Test unregistering an existing participant"""
        activities = setup_activities
        
        # Find an activity with participants
        for activity_name, activity_data in activities.items():
            if activity_data["participants"]:
                email = activity_data["participants"][0]
                response = client.post(
                    f"/activities/{activity_name.replace(' ', '%20')}/unregister?email={email}"
                )
                assert response.status_code == 200
                assert "Unregistered" in response.json()["message"]
                return
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from nonexistent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
    
    def test_unregister_not_signed_up_participant(self, client, setup_activities):
        """Test unregistering a participant who is not signed up"""
        response = client.post(
            "/activities/Music%20club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_unregister_response_format(self, client, setup_activities):
        """Test that unregister response has correct format"""
        activities = setup_activities
        
        for activity_name, activity_data in activities.items():
            if activity_data["participants"]:
                email = activity_data["participants"][0]
                response = client.post(
                    f"/activities/{activity_name.replace(' ', '%20')}/unregister?email={email}"
                )
                data = response.json()
                assert "message" in data
                assert isinstance(data["message"], str)
                return


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_flow(self, client, setup_activities):
        """Test complete flow of signing up and then unregistering"""
        email = "integrationtest@mergington.edu"
        activity = "Chess%20Club"
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify in activities list
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email in activities["Chess Club"]["participants"]
        
        # Unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify removed from activities list
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email not in activities["Chess Club"]["participants"]
    
    def test_can_signup_again_after_unregister(self, client, setup_activities):
        """Test that a student can sign up again after unregistering"""
        email = "reregister@mergington.edu"
        activity = "Tennis%20Club"
        
        # First signup
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response2.status_code == 200
        
        # Second signup should succeed
        response3 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response3.status_code == 200
