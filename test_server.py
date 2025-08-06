"""
Test script to verify all endpoints work correctly
Run this script to test your Flask server
"""

import requests
import json
import time
from typing import Dict, Any


class FlaskServerTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        
    def test_endpoint(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, timeout=10, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, timeout=10, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Try to parse JSON, fall back to text if it fails
            try:
                data = response.json()
            except ValueError:
                data = {"raw_content": response.text, "content_type": response.headers.get('content-type')}
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": data,
                "url": url
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}",
                "url": url
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def run_all_tests(self):
        """Run all endpoint tests"""
        print("🚀 Testing BasoKa Flask Server Endpoints")
        print("=" * 50)
        
        tests = [
            ("GET", "/health", "Health Check"),
            ("GET", "/status", "Get Status"),
            ("GET", "/is_running", "Check if Running"),
            ("GET", "/log", "Get Logs"),
            ("POST", "/start", "Start Process"),
            ("GET", "/is_running", "Check Running After Start"),
            ("POST", "/stop", "Stop Process"),
            ("GET", "/is_running", "Check Running After Stop"),
        ]
        
        results = []
        
        for method, endpoint, description in tests:
            print(f"\n📋 Testing: {description}")
            print(f"   {method} {endpoint}")
            
            result = self.test_endpoint(method, endpoint)
            results.append({
                "test": description,
                "method": method,
                "endpoint": endpoint,
                **result
            })
            
            if result["success"]:
                print(f"   ✅ Success (Status: {result['status_code']})")
                if result.get("data"):
                    print(f"   📄 Response: {json.dumps(result['data'], indent=6)}")
            else:
                print(f"   ❌ Failed: {result['error']}")
            
            # Small delay between tests
            time.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        print(f"   ✅ Successful: {successful}/{total}")
        print(f"   ❌ Failed: {total - successful}/{total}")
        
        if successful == total:
            print("   🎉 All tests passed!")
        else:
            print("   ⚠️  Some tests failed. Check the output above.")
        
        return results


def main():
    """Main test function"""
    print("Starting Flask Server Test Suite...")
    print("Make sure your Flask server is running on http://localhost:8000")
    
    # Wait for user confirmation
    input("\nPress Enter to continue with testing...")
    
    tester = FlaskServerTester()
    results = tester.run_all_tests()
    
    # Save results to file
    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Test results saved to: test_results.json")


if __name__ == "__main__":
    main()
