"""
Centralized AI Manager - Single source of truth for all AI operations
"""

import time
import re
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QSettings

from utils.rate_limiter import RateLimiter

try:
    from openai import AzureOpenAI, OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIManager:
    """Centralized AI manager for all OpenAI and Azure OpenAI operations"""

    _instance = None

    def __new__(cls):
        """Singleton pattern - only one AI manager instance"""
        if cls._instance is None:
            cls._instance = super(AIManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the AI manager"""
        if self._initialized:
            return

        self.client: Optional[AzureOpenAI | OpenAI] = None
        self.settings = QSettings("Rabbit Consulting", "Novelist AI")
        
        # Track models that don't support temperature
        self._unsupported_temp_models = set()
        
        # Initialize rate limiter
        # Defaults: 50 RPM, 500 RPH, 1s min delay
        self.limiter = RateLimiter(
            requests_per_minute=50,
            requests_per_hour=500,
            min_delay_seconds=1.0
        )
        
        self._initialized = True
        self.refresh_client()

    def refresh_client(self):
        """Refresh the AI client with current settings"""
        if not OPENAI_AVAILABLE:
            print("ERROR: OpenAI library not available")
            return

        self._unsupported_temp_models.clear()
        provider = self.settings.value("ai/provider", "azure")
        print(f"Refreshing AI client (Provider: {provider})...")

        if provider == "openai":
            api_key = self.settings.value("openai/api_key", "")
            model = self.settings.value("openai/model", "gpt-4")
            
            print(f"  Model: {model}")
            print(f"  API Key: {'*' * 20}" if api_key else "  API Key: (empty)")

            if api_key:
                try:
                    self.client = OpenAI(api_key=api_key)
                    print("  ✓ OpenAI client initialized successfully")
                except Exception as e:
                    print(f"  ✗ Error initializing OpenAI client: {e}")
                    self.client = None
            else:
                print("  ✗ Missing OpenAI credentials")
                self.client = None
        else:
            # Default to Azure
            api_key = self.settings.value("azure/api_key", "")
            endpoint = self.settings.value("azure/endpoint", "")
            api_version = self.settings.value("azure/api_version", "2024-02-15-preview")

            print(f"  Endpoint: {endpoint[:30]}..." if endpoint else "  Endpoint: (empty)")
            print(f"  API Key: {'*' * 20}" if api_key else "  API Key: (empty)")
            print(f"  API Version: {api_version}")

            if api_key and endpoint:
                try:
                    self.client = AzureOpenAI(
                        api_key=api_key,
                        azure_endpoint=endpoint,
                        api_version=api_version
                    )
                    print("  ✓ Azure OpenAI client initialized successfully")
                except Exception as e:
                    print(f"  ✗ Error initializing Azure client: {e}")
                    self.client = None
            else:
                print("  ✗ Missing Azure credentials")
                self.client = None

    def is_configured(self) -> bool:
        """Check if AI is properly configured"""
        is_config = self.client is not None
        print(f"is_configured check: {is_config}")
        return is_config

    def get_deployment(self) -> str:
        """Get the deployment/model name"""
        provider = self.settings.value("ai/provider", "azure")
        if provider == "openai":
            return self.settings.value("openai/model", "gpt-4")
        return self.settings.value("azure/deployment", "gpt-4")

    def get_temperature(self) -> float:
        """Get the temperature setting"""
        return float(self.settings.value("ai/temperature", 70)) / 100.0

    def get_max_tokens(self) -> int:
        """Get max tokens setting"""
        return int(self.settings.value("ai/max_tokens", 4000))

    def should_disable_temperature(self) -> bool:
        """Check if temperature should be disabled globally"""
        return self.settings.value("ai/disable_temperature", False, type=bool)

    def call_api(self, messages: List[Dict[str, str]],
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None,
                 system_message: Optional[str] = None) -> str:
        """
        Call OpenAI/Azure API with messages with automatic retries and rate limiting.
        """
        print("call_api called")

        if not self.is_configured():
            raise Exception("AI is not configured. Please configure in Settings.")

        # Add system message if provided
        if system_message:
            messages = [{"role": "system", "content": system_message}] + messages

        # Use provided values or defaults
        temp = temperature if temperature is not None else self.get_temperature()
        tokens = max_tokens if max_tokens is not None else self.get_max_tokens()

        deployment = self.get_deployment()
        
        # Adjust for o1 models which only support temperature 1
        is_o1 = "o1" in deployment.lower()
        disable_temp = self.should_disable_temperature() or (deployment in self._unsupported_temp_models)
        
        if is_o1:
            print(f"  Model {deployment} detected as o1-style. Setting temperature to default (1.0).")
            temp = 1.0
        
        if disable_temp:
            print(f"  Temperature disabled globally by setting.")

        # Standard parameters for both clients
        params = {
            "model": deployment,
            "messages": messages,
            "max_completion_tokens": tokens
        }

        # Only include temperature if it's NOT an o1 model AND NOT disabled globally
        if not is_o1 and not disable_temp:
            params["temperature"] = temp

        max_retries = 5
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                # Proactive rate limiting
                self.limiter.wait_if_needed()
                
                print(f"Calling API (Attempt {attempt+1}/{max_retries}) with model: {deployment}")
                response = self.client.chat.completions.create(**params)
                
                # Record successful request
                self.limiter.record_request()
                
                result = response.choices[0].message.content
                print(f"API call successful, got {len(result)} characters")
                return result

            except Exception as e:
                err_msg = str(e)
                print(f"API call error (Attempt {attempt+1}): {err_msg}")
                # Use a more robust check for temperature unsupported
                is_temp_err = ("temperature" in err_msg.lower() and 
                               ("unsupported_value" in err_msg.lower() or 
                                "unsupported value" in err_msg.lower() or
                                "does not support" in err_msg.lower() or
                                "only the default (1) value is supported" in err_msg.lower()))
                
                if is_temp_err:
                    # Remember this model doesn't support temperature
                    self._unsupported_temp_models.add(deployment)
                    
                    if "temperature" in params:
                        print("  Detected unsupported temperature value. Retrying without temperature...")
                        del params["temperature"]
                    
                    # We don't increment attempt here if we want to retry immediately without waiting
                    # but it's safer to just let it loop and use one of the retries
                    # Actually, if we just update params and continue, we don't need to wait for rate limits etc.
                    # but let's just let it retry in the next loop iteration to keep it simple.
                    # OR we can just update it and try again right now.
                    try:
                        response = self.client.chat.completions.create(**params)
                        self.limiter.record_request()
                        result = response.choices[0].message.content
                        return result
                    except Exception as retry_e:
                        err_msg = str(retry_e)
                        print(f"Retry without temperature failed: {err_msg}")

                # Check for rate limit error (429)
                is_rate_limit = "429" in err_msg or "RateLimitReached" in err_msg or "rate limit" in err_msg.lower()
                
                if is_rate_limit and attempt < max_retries - 1:
                    # Try to extract "retry after X seconds"
                    wait_time = base_delay * (2 ** attempt) # Exponential backoff
                    
                    # Pattern for Azure/OpenAI "retry after" messages
                    retry_match = re.search(r"retry after (\d+) second", err_msg.lower())
                    if retry_match:
                        wait_time = float(retry_match.group(1)) + 1.0 # Add a small buffer
                    
                    print(f"Rate limit hit. Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    continue
                
                # If it's the last attempt or not a rate limit error we want to retry
                if attempt == max_retries - 1:
                    raise Exception(f"API call failed after {max_retries} attempts: {err_msg}")
                
                # For other errors, we can retry in the next loop iteration (exponential backoff)
                # unless it's an error we know won't be fixed by retrying.
                # But wait, we already handled the temperature retry internally above.
                
                # Let's add a small sleep for general errors to avoid tight loops
                time.sleep(1.0)
                continue

        return "" # Should not reach here

    def test_connection(self) -> tuple[bool, str]:
        """Test the AI connection"""
        print("test_connection called")

        if not OPENAI_AVAILABLE:
            print("OpenAI not available")
            return False, "OpenAI library not installed"

        if not self.is_configured():
            print("Not configured")
            return False, "Not configured - please enter API credentials"

        try:
            print("Attempting test API call...")
            deployment = self.get_deployment()
            response = self.client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": "Test"}],
                max_completion_tokens=10
            )
            print("Test successful!")
            return True, "Connection successful!"
        except Exception as e:
            print(f"Test failed: {str(e)}")
            return False, f"Connection failed: {str(e)}"


# Global instance
ai_manager = AIManager()