import os
import time
import requests
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_API_URL = os.getenv(
    "OLLAMA_API_URL", "https://aditya69690-100-hack.hf.space/api/generate"
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def classify_issue(issue_text, model="tinyllama", retries=3):
    """
    Classify GitHub issues using TinyLLama hosted on HuggingFace
    Returns one of: bug, feature, question, documentation, discussion, unknown
    """
    
    # Very short and focused prompt for TinyLLama
    # Truncate issue text more aggressively
    truncated_text = issue_text[:300] if len(issue_text) > 300 else issue_text
    
    # Simplified prompt that works better with small models
    prompt = f"Classify this GitHub issue as one word: bug, feature, question, documentation, or discussion.\n\nIssue: {truncated_text}\n\nClassification:"

    def call_groq(prompt_text):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "temperature": 0.1,
                    "max_tokens": 5,
                },
                timeout=20,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip().lower()
            first_word = content.split()[0].strip(":.-*") if content.split() else content
            valid_labels = {"bug", "feature", "question", "documentation", "discussion"}
            if first_word in valid_labels:
                return first_word
            for label in valid_labels:
                if label in content:
                    return label
            return "unknown"
        except Exception as e:
            logger.warning(f"Groq call failed: {e}")
            return "unknown"

    if GROQ_API_KEY:
        result = call_groq(prompt)
        if result != "unknown":
            return result

    def call_llm(prompt_text, attempt):
        try:
            logger.info(f"Attempt {attempt}: Calling LLM API...")

            # Use the /api/generate format that works
            payload = {
                "model": model,
                "prompt": prompt_text,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 5,  # Very short response
                    "top_p": 0.9,
                    "stop": ["\n", ".", ",", " "]  # Stop early
                }
            }
            
            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=45,  # Increased timeout for CPU inference
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"HTTP Error {response.status_code}: {response.text}")
                return "unknown"
            
            response_data = response.json()
            logger.info(f"Full response: {response_data}")
            
            # Extract content from /api/generate response format
            content = response_data.get("response", "").strip()
            
            if not content:
                logger.error("Empty content in response")
                return "unknown"
                
            # Clean and extract the classification
            cleaned = content.strip().lower()
            logger.info(f"LLM returned: '{cleaned}'")
            
            # Extract first word and validate
            first_word = cleaned.split()[0] if cleaned.split() else cleaned
            
            # Remove common prefixes
            first_word = first_word.replace(":", "").replace("-", "").replace("*", "")
            
            # Check if it's a valid classification
            valid_labels = {"bug", "feature", "question", "documentation", "discussion"}
            if first_word in valid_labels:
                logger.info(f"Successfully classified as: {first_word}")
                return first_word
            
            # Try to find valid label within the response
            for label in valid_labels:
                if label in cleaned:
                    logger.info(f"Found valid label in response: {label}")
                    return label
            
            logger.warning(f"No valid label found in: '{cleaned}'")
            return "unknown"
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout on attempt {attempt}")
            return "unknown"
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error on attempt {attempt}: {e}")
            return "unknown"
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt}: {e}")
            return "unknown"

    # Retry logic with exponential backoff
    for attempt in range(1, retries + 1):
        result = call_llm(prompt, attempt)
        
        if result != "unknown":
            return result
        
        if attempt < retries:
            wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
            logger.info(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    # Fallback classification based on keywords
    logger.info("Using keyword-based fallback classification")
    issue_lower = issue_text.lower()
    
    if any(word in issue_lower for word in ["bug", "error", "crash", "broken", "fix", "issue"]):
        return "bug"
    elif any(word in issue_lower for word in ["feature", "enhancement", "add", "new", "implement"]):
        return "feature"
    elif any(word in issue_lower for word in ["how", "what", "why", "question", "help", "?"]):
        return "question"
    elif any(word in issue_lower for word in ["docs", "documentation", "readme", "guide", "tutorial"]):
        return "documentation"
    else:
        return "discussion"

# Test function to verify the API is working
def test_classifier():
    """Test function to verify the classifier is working"""
    test_issue = "The login button is not working when I click it. Getting error 500."
    result = classify_issue(test_issue)
    print(f"Test classification result: {result}")
    return result

if __name__ == "__main__":
    test_classifier()