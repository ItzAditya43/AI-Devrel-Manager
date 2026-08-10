import requests
import json
import time

# Your HuggingFace endpoint
OLLAMA_API_URL = "https://aditya69690-100-hack.hf.space/api/chat"

def test_endpoint_basic():
    """Test basic connectivity to your HuggingFace endpoint"""
    print("=" * 50)
    print("TESTING BASIC CONNECTIVITY")
    print("=" * 50)
    
    try:
        # Simple health check
        response = requests.get(OLLAMA_API_URL.replace("/api/chat", "/"), timeout=10)
        print(f"Health check status: {response.status_code}")
        print(f"Health check response: {response.text[:200]}")
    except Exception as e:
        print(f"Health check failed: {e}")

def test_endpoint_formats():
    """Test different API formats that might work with your endpoint"""
    print("\n" + "=" * 50)
    print("TESTING DIFFERENT API FORMATS")
    print("=" * 50)
    
    test_message = "Classify this as bug, feature, or question: Login button not working"
    
    # Format 1: Ollama-style chat
    format1 = {
        "model": "tinyllama",
        "messages": [
            {"role": "system", "content": "You are a classifier. Return only: bug, feature, or question."},
            {"role": "user", "content": test_message}
        ],
        "stream": False
    }
    
    # Format 2: Simple prompt format
    format2 = {
        "model": "tinyllama",
        "prompt": test_message,
        "stream": False
    }
    
    # Format 3: HuggingFace transformers format
    format3 = {
        "inputs": test_message,
        "parameters": {
            "max_new_tokens": 10,
            "temperature": 0.1
        }
    }
    
    # Format 4: OpenAI-style
    format4 = {
        "model": "tinyllama",
        "messages": [{"role": "user", "content": test_message}],
        "max_tokens": 10,
        "temperature": 0.1
    }
    
    formats = [
        ("Ollama Chat Format", format1),
        ("Simple Prompt Format", format2),
        ("HuggingFace Format", format3),
        ("OpenAI Format", format4)
    ]
    
    for name, payload in formats:
        print(f"\n--- Testing {name} ---")
        try:
            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"JSON Response: {json.dumps(result, indent=2)}")
                except:
                    print(f"Text Response: {response.text}")
            else:
                print(f"Error Response: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")
        
        time.sleep(2)  # Be nice to the server

def test_generate_endpoint():
    """Test if there's a /generate endpoint instead"""
    print("\n" + "=" * 50)
    print("TESTING /generate ENDPOINT")
    print("=" * 50)
    
    generate_url = OLLAMA_API_URL.replace("/chat", "/generate")
    print(f"Testing: {generate_url}")
    
    payload = {
        "model": "tinyllama",
        "prompt": "Classify as bug, feature, or question: Login button broken. Answer:",
        "stream": False
    }
    
    try:
        response = requests.post(
            generate_url,
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"JSON Response: {json.dumps(result, indent=2)}")
            except:
                print(f"Text Response: {response.text}")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Generate endpoint test failed: {e}")

def test_different_urls():
    """Test different possible URL patterns"""
    print("\n" + "=" * 50)
    print("TESTING DIFFERENT URL PATTERNS")
    print("=" * 50)
    
    base_url = "https://aditya69690-100-hack.hf.space"
    urls_to_test = [
        f"{base_url}/api/chat",
        f"{base_url}/api/generate", 
        f"{base_url}/v1/chat/completions",
        f"{base_url}/generate",
        f"{base_url}/chat",
        f"{base_url}/api/completions",
        f"{base_url}/completion"
    ]
    
    simple_payload = {
        "model": "tinyllama",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False
    }
    
    for url in urls_to_test:
        print(f"\n--- Testing URL: {url} ---")
        try:
            response = requests.post(
                url,
                json=simple_payload,
                timeout=15,
                headers={"Content-Type": "application/json"}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ This URL works!")
                try:
                    result = response.json()
                    print(f"Sample response: {json.dumps(result, indent=2)[:200]}...")
                except:
                    print(f"Text response: {response.text[:200]}...")
            elif response.status_code in [404, 405]:
                print("❌ URL not found or method not allowed")
            else:
                print(f"⚠️ Unexpected status: {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    print("🧪 DEBUGGING HUGGINGFACE LLM ENDPOINT")
    print("This script will help identify the correct API format for your endpoint")
    
    test_endpoint_basic()
    test_endpoint_formats()
    test_generate_endpoint()
    test_different_urls()
    
    print("\n" + "=" * 50)
    print("DEBUG COMPLETE")
    print("=" * 50)
    print("Look for responses marked with ✅ - those are working endpoints!")
    print("Copy the working format to your classifier and devrel agents.")