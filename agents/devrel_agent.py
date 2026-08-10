import os
import requests
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_API_URL = os.getenv(
    "OLLAMA_API_URL", "https://aditya69690-100-hack.hf.space/api/generate"
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

def recommend_devrel_action(issue, model="tinyllama", min_word_count=8):
    """
    Generate DevRel suggestions for GitHub issues using TinyLLama
    """
    
    title = issue.get("title", "")[:150]  # Slightly longer for context
    body = issue.get("body", "")[:300]    # More context for better suggestions
    label = issue.get("predicted_label", "unknown")
    
    # More detailed prompt for concrete, actionable suggestions
    prompt = f"""You are a Developer Relations expert. Analyze this GitHub issue and provide ONE specific, actionable DevRel strategy.

Issue Type: {label}
Title: {title}
Description: {body}

Provide a concrete suggestion that includes:
- What specific content to create (blog post, tutorial, documentation, etc.)
- Target audience and key points to address
- Expected outcome for the community

Keep response under 120 words but complete the thought.

DevRel Action:"""

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
                    "temperature": 0.4,
                    "max_tokens": 200,
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            return content if len(content.split()) >= 8 else ""
        except Exception as e:
            logger.warning(f"Groq call failed: {e}")
            return ""

    if GROQ_API_KEY:
        result = call_groq(prompt)
        if result:
            return result

    def call_llm(prompt_text, attempt):
        try:
            logger.info(f"DevRel attempt {attempt}: Calling LLM API...")
            
            # Use the /api/generate format that works
            payload = {
                "model": model,
                "prompt": prompt_text,
                "stream": False,
                "options": {
                    "temperature": 0.4,  # Slightly higher for more creative responses
                    "num_predict": 150,  # Allow up to 120+ words
                    "top_p": 0.85,
                    "stop": ["\n\nDevRel Action:", "Action:", "\n\n\n"]  # Better stop tokens
                }
            }
            
            response = requests.post(
                OLLAMA_API_URL,
                json=payload,
                timeout=45,  # Longer timeout for generation
                headers={"Content-Type": "application/json"}
            )
            
            logger.info(f"DevRel response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"DevRel HTTP Error {response.status_code}: {response.text}")
                return ""
            
            response_data = response.json()
            logger.info(f"DevRel full response: {response_data}")
            
            # Extract content from /api/generate response format
            content = response_data.get("response", "").strip()
            
            if not content:
                logger.error("DevRel empty content in response")
                return ""
            
            # Clean the response
            cleaned = content.strip()
            logger.info(f"DevRel LLM returned: '{cleaned}'")
            
            # Basic quality checks - more flexible length
            if len(cleaned) < 20:  # Minimum for meaningful suggestion
                logger.warning(f"DevRel response too short: '{cleaned}'")
                return ""
            
            # Check word count - flexible around 120 words
            word_count = len(cleaned.split())
            if word_count < 10:  # Too short to be useful
                logger.warning(f"DevRel response too brief ({word_count} words): '{cleaned}'")
                return ""
            
            # Remove common unhelpful responses
            unhelpful_phrases = [
                "no suggestion", 
                "not applicable", 
                "unclear",
                "i don't know",
                "cannot determine",
                "sorry"
            ]
            
            if any(phrase in cleaned.lower() for phrase in unhelpful_phrases):
                logger.warning(f"DevRel unhelpful response: '{cleaned}'")
                return ""
            
            # Check minimum word count for substance
            if len(cleaned.split()) < 8:  # Reduced minimum for flexibility
                logger.warning(f"DevRel response below minimum word count: '{cleaned}'")
                return ""
            
            logger.info(f"DevRel successful suggestion: '{cleaned}'")
            return cleaned
            
        except requests.exceptions.Timeout:
            logger.error(f"DevRel timeout on attempt {attempt}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"DevRel request error on attempt {attempt}: {e}")
            return ""
        except Exception as e:
            logger.error(f"DevRel unexpected error on attempt {attempt}: {e}")
            return ""

    # Try LLM first (single attempt due to reliability issues)
    result = call_llm(prompt, 1)
    
    if result:  # If we got a valid response
        return result

    # Enhanced fallback suggestions - more concrete and detailed
    logger.info(f"DevRel using enhanced fallback suggestion for {label}")
    
    title_lower = issue.get("title", "").lower()
    body_lower = issue.get("body", "").lower()
    
    if label == "bug":
        if any(word in title_lower + body_lower for word in ["auth", "login", "security", "permission"]):
            return "Create a comprehensive authentication troubleshooting guide with common error codes, step-by-step debugging workflows, and security best practices. Include code examples for different auth methods and a community FAQ section. Target developers implementing authentication features. Expected outcome: Reduced auth-related support tickets and improved developer onboarding experience."
        elif any(word in title_lower + body_lower for word in ["api", "endpoint", "request", "response"]):
            return "Develop an API debugging toolkit including error code documentation, request/response examples, and interactive testing tools. Create video tutorials showing common API integration patterns. Target backend developers and integration teams. Expected outcome: Faster API adoption and reduced integration support overhead."
        elif any(word in title_lower + body_lower for word in ["performance", "slow", "timeout", "memory"]):
            return "Build a performance optimization guide with profiling tools, benchmarking examples, and monitoring best practices. Include case studies of common bottlenecks and their solutions. Target senior developers and DevOps teams. Expected outcome: Improved application performance and reduced performance-related issues."
        else:
            return "Document this bug pattern in a comprehensive troubleshooting knowledge base with diagnostic steps, common causes, and prevention strategies. Create community-driven solution threads and maintain an updated FAQ. Target all developer skill levels. Expected outcome: Faster issue resolution and community self-service capabilities."
    
    elif label == "feature":
        if any(word in title_lower + body_lower for word in ["integration", "api", "sdk", "webhook"]):
            return "Write a complete integration tutorial series with code examples, SDKs comparison, and real-world use cases. Include sandbox environments and interactive demos. Target integration developers and technical decision-makers. Expected outcome: Accelerated feature adoption and reduced integration complexity."
        elif any(word in title_lower + body_lower for word in ["ui", "interface", "design", "component"]):
            return "Create a design system documentation with component library, usage patterns, and accessibility guidelines. Include Figma templates and code snippets for popular frameworks. Target frontend developers and designers. Expected outcome: Consistent user experiences and faster UI development cycles."
        elif any(word in title_lower + body_lower for word in ["mobile", "ios", "android", "react native"]):
            return "Develop mobile-specific implementation guides with platform considerations, native bridging examples, and testing strategies. Include app store optimization tips and deployment workflows. Target mobile developers. Expected outcome: Increased mobile platform adoption and smoother mobile integrations."
        else:
            return "Develop a feature showcase series with implementation examples, use case scenarios, and migration guides. Include community feedback collection and roadmap discussions. Target product managers and lead developers. Expected outcome: Higher feature utilization and community-driven product feedback."
    
    elif label == "question":
        if any(word in title_lower + body_lower for word in ["how", "setup", "install", "configure"]):
            return "Create a comprehensive setup guide with step-by-step instructions, environment-specific configurations, and common pitfall solutions. Include video walkthroughs and automated setup scripts. Target new developers and system administrators. Expected outcome: Reduced onboarding friction and faster time-to-first-success."
        elif any(word in title_lower + body_lower for word in ["best", "practice", "recommend", "pattern"]):
            return "Write an architectural best practices guide with proven patterns, anti-patterns to avoid, and scalability considerations. Include community case studies and expert interviews. Target senior developers and architects. Expected outcome: Improved code quality and reduced technical debt across the community."
        elif any(word in title_lower + body_lower for word in ["upgrade", "migration", "version", "breaking"]):
            return "Develop a migration strategy guide with version compatibility matrices, automated migration tools, and rollback procedures. Include breaking changes documentation and timeline recommendations. Target maintenance teams and project leads. Expected outcome: Smoother upgrades and reduced migration-related issues."
        else:
            return "Add this to a searchable FAQ knowledge base with detailed answers, related topics, and community discussions. Create tutorial content addressing the core concepts. Target developers at all skill levels. Expected outcome: Improved self-service capabilities and reduced repetitive support requests."
    
    elif label == "documentation":
        if any(word in title_lower + body_lower for word in ["missing", "unclear", "confusing", "incomplete"]):
            return "Rewrite the unclear documentation sections with improved structure, practical examples, and user-friendly language. Include interactive code samples and visual diagrams. Target developers struggling with current docs. Expected outcome: Improved documentation usability and reduced confusion-related support requests."
        elif any(word in title_lower + body_lower for word in ["example", "tutorial", "guide", "walkthrough"]):
            return "Create comprehensive tutorial series with real-world examples, progressive complexity levels, and hands-on exercises. Include downloadable sample projects and community showcase submissions. Target learning developers and educators. Expected outcome: Accelerated learning curve and increased community engagement."
        else:
            return "Expand documentation with interactive examples, advanced use cases, and integration patterns. Include community-contributed content and regular content audits. Target all developer segments. Expected outcome: More comprehensive knowledge base and stronger community contributions."
    
    else:  # discussion or unknown
        return "Facilitate structured community discussions with dedicated forums, regular AMAs, and feedback collection mechanisms. Create discussion templates and moderation guidelines. Target active community members and potential contributors. Expected outcome: Stronger community engagement and valuable product insights for roadmap planning."

# Test function
def test_devrel():
    """Test function to verify the DevRel agent is working"""
    test_issue = {
        "title": "How to implement authentication in the API?",
        "body": "I'm trying to add user authentication to my API but can't find clear documentation.",
        "predicted_label": "question",
        "web_context": "Authentication is a common requirement for APIs."
    }
    result = recommend_devrel_action(test_issue)
    print(f"Test DevRel result: {result}")
    return result

if __name__ == "__main__":
    test_devrel()