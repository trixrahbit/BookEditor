"""
Centralized AI Manager - Single source of truth for all AI operations
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QSettings

try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIManager:
    """Centralized AI manager for all Azure OpenAI operations"""

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

        self.client: Optional[AzureOpenAI] = None
        self.settings = QSettings("Rabbit Consulting", "Novelist AI")
        self._initialized = True
        self.refresh_client()

    def refresh_client(self):
        """Refresh the Azure OpenAI client with current settings"""
        if not OPENAI_AVAILABLE:
            print("ERROR: OpenAI library not available")
            return

        api_key = self.settings.value("azure/api_key", "")
        endpoint = self.settings.value("azure/endpoint", "")
        api_version = self.settings.value("azure/api_version", "2024-02-15-preview")

        print(f"Refreshing AI client...")
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
                print("  ✓ Client initialized successfully")
            except Exception as e:
                print(f"  ✗ Error initializing client: {e}")
                self.client = None
        else:
            print("  ✗ Missing credentials")
            self.client = None

    def is_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured"""
        is_config = self.client is not None
        print(f"is_configured check: {is_config}")
        return is_config

    def get_deployment(self) -> str:
        """Get the deployment name"""
        deployment = self.settings.value("azure/deployment", "gpt-4")
        print(f"Deployment: {deployment}")
        return deployment

    def get_temperature(self) -> float:
        """Get the temperature setting"""
        return float(self.settings.value("ai/temperature", 70)) / 100.0

    def get_max_tokens(self) -> int:
        """Get max tokens setting"""
        return int(self.settings.value("ai/max_tokens", 4000))

    def call_api(self, messages: List[Dict[str, str]],
                 temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None,
                 system_message: Optional[str] = None) -> str:
        """
        Call Azure OpenAI API with messages

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            system_message: Optional system message (prepended to messages)

        Returns:
            Response content as string

        Raises:
            Exception if not configured or API call fails
        """
        print("call_api called")

        if not self.is_configured():
            raise Exception("Azure OpenAI is not configured. Please configure in Settings.")

        # Add system message if provided
        if system_message:
            messages = [{"role": "system", "content": system_message}] + messages

        # Use provided values or defaults
        temp = temperature if temperature is not None else self.get_temperature()
        tokens = max_tokens if max_tokens is not None else self.get_max_tokens()

        print(f"Calling API with deployment: {self.get_deployment()}, temp: {temp}, tokens: {tokens}")

        try:
            response = self.client.chat.completions.create(
                model=self.get_deployment(),
                messages=messages,
                max_completion_tokens=tokens
            )
            result = response.choices[0].message.content
            print(f"API call successful, got {len(result)} characters")
            return result
        except Exception as e:
            print(f"API call error: {str(e)}")
            raise Exception(f"API call failed: {str(e)}")

    def test_connection(self) -> tuple[bool, str]:
        """Test the Azure OpenAI connection"""
        print("test_connection called")

        if not OPENAI_AVAILABLE:
            print("OpenAI not available")
            return False, "OpenAI library not installed"

        print(f"Client exists: {self.client is not None}")

        if not self.is_configured():
            print("Not configured")
            return False, "Not configured - please enter API credentials"

        try:
            print("Attempting test API call...")
            response = self.client.chat.completions.create(
                model=self.get_deployment(),
                messages=[{"role": "user", "content": "Test"}],
                max_completion_tokens=2000
            )
            print("Test successful!")
            return True, "Connection successful!"
        except Exception as e:
            print(f"Test failed: {str(e)}")
            return False, f"Connection failed: {str(e)}"


# Global instance
ai_manager = AIManager()