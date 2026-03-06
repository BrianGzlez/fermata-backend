#!/usr/bin/env python3
"""
Comprehensive test suite for the Consorzio Autolinee API.
"""

import requests
import json
import time
import pytest

BASE_URL = "http://localhost:8000"


class TestConsorzioAPI:
    """Test suite for the Consorzio Autolinee API."""
    
    def test_health_check(self):
        """Test the health check endpoint."""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_get_lines(self):
        """Test getting all bus lines."""
        response = requests.get(f"{BASE_URL}/lines")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            assert "value" in data[0]
            assert "label" in data[0]
    
    def test_search_stops(self):
        """Test stop search functionality."""
        response = requests.get(f"{BASE_URL}/search/stops?q=cosenza")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert isinstance(data["results"], list)
    
    def test_search_stops_invalid_query(self):
        """Test stop search with invalid query."""
        response = requests.get(f"{BASE_URL}/search/stops?q=a")
        assert response.status_code == 400
    
    def test_nearby_stops(self):
        """Test nearby stops functionality."""
        # Test with Cosenza coordinates
        response = requests.get(f"{BASE_URL}/stops/nearby?lat=39.2986&lon=16.2540&radius=2.0")
        assert response.status_code == 200
        data = response.json()
        assert "nearby_stops" in data
        assert "count" in data
    
    def test_nearby_stops_invalid_coordinates(self):
        """Test nearby stops with invalid coordinates."""
        response = requests.get(f"{BASE_URL}/stops/nearby?lat=200&lon=200")
        assert response.status_code == 400
    
    def test_service_alerts(self):
        """Test service alerts endpoint."""
        response = requests.get(f"{BASE_URL}/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert "count" in data
    
    def test_user_favorites(self):
        """Test user favorites functionality."""
        user_id = "test_user"
        
        # Get initial favorites
        response = requests.get(f"{BASE_URL}/users/{user_id}/favorites")
        assert response.status_code == 200
        
        # Add a favorite
        response = requests.post(f"{BASE_URL}/users/{user_id}/favorites?item_type=stop&item_id=COSENZA")
        assert response.status_code == 200
        
        # Check favorites were added
        response = requests.get(f"{BASE_URL}/users/{user_id}/favorites")
        assert response.status_code == 200
        data = response.json()
        assert "COSENZA" in data["favorites"]["stops"]
        
        # Remove favorite
        response = requests.delete(f"{BASE_URL}/users/{user_id}/favorites?item_type=stop&item_id=COSENZA")
        assert response.status_code == 200
    
    def test_accessibility_info(self):
        """Test accessibility information endpoint."""
        response = requests.get(f"{BASE_URL}/stops/COSENZA/accessibility")
        assert response.status_code == 200
        data = response.json()
        assert "accessibility" in data
        assert "wheelchair_accessible" in data["accessibility"]
    
    def test_route_planning(self):
        """Test route planning functionality."""
        response = requests.get(f"{BASE_URL}/routes/plan?from_stop=COSENZA&to_stop=SCALEA")
        assert response.status_code == 200
        data = response.json()
        assert "routes" in data
        assert "count" in data
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        response = requests.post(f"{BASE_URL}/admin/clear-cache")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


def run_integration_tests():
    """Run integration tests manually."""
    print("🧪 Running Consorzio API Integration Tests")
    print("=" * 50)
    
    test_suite = TestConsorzioAPI()
    
    tests = [
        ("Health Check", test_suite.test_health_check),
        ("Get Lines", test_suite.test_get_lines),
        ("Search Stops", test_suite.test_search_stops),
        ("Search Stops Invalid", test_suite.test_search_stops_invalid_query),
        ("Nearby Stops", test_suite.test_nearby_stops),
        ("Nearby Invalid Coords", test_suite.test_nearby_stops_invalid_coordinates),
        ("Service Alerts", test_suite.test_service_alerts),
        ("User Favorites", test_suite.test_user_favorites),
        ("Accessibility Info", test_suite.test_accessibility_info),
        ("Route Planning", test_suite.test_route_planning),
        ("Clear Cache", test_suite.test_clear_cache),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"🔍 Testing {test_name}...", end=" ")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"🏁 Tests completed: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} tests failed")


if __name__ == "__main__":
    run_integration_tests()