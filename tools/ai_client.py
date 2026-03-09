"""
AI client supporting Claude, GPT, Gemini, and OpenRouter models.
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

from .error_handler import retry_with_backoff, TransientError, FatalError

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of AI text generation."""
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> GenerationResult:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost based on token counts."""
        pass


class ClaudeProvider(BaseProvider):
    """Anthropic Claude API provider."""

    # Cost per million tokens (as of 2024)
    INPUT_COST_PER_M = 3.0
    OUTPUT_COST_PER_M = 15.0
    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise FatalError("ANTHROPIC_API_KEY not set")

        self.model = model or self.DEFAULT_MODEL

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise FatalError("anthropic package not installed")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.INPUT_COST_PER_M / 1_000_000 +
                output_tokens * self.OUTPUT_COST_PER_M / 1_000_000)

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> GenerationResult:
        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": messages
            }
            if system:
                kwargs["system"] = system

            response = self.client.messages.create(**kwargs)

            text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self.estimate_cost(input_tokens, output_tokens)

            logger.info(f"{self.model}: {input_tokens} in / {output_tokens} out, ${cost:.4f}")

            return GenerationResult(
                text=text,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost
            )

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, e: Exception):
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str:
            raise TransientError(f"Claude rate limit: {e}")
        elif "unauthorized" in error_str or "401" in error_str:
            raise FatalError(f"Invalid Claude API key: {e}")
        elif "overloaded" in error_str or "529" in error_str:
            raise TransientError(f"Claude overloaded: {e}")
        else:
            raise TransientError(f"Claude error: {e}")


class OpenAIProvider(BaseProvider):
    """OpenAI GPT API provider."""

    # Cost per million tokens for GPT-4o (as of 2024)
    INPUT_COST_PER_M = 2.5
    OUTPUT_COST_PER_M = 10.0
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise FatalError("OPENAI_API_KEY not set")

        self.model = model or self.DEFAULT_MODEL

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise FatalError("openai package not installed")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.INPUT_COST_PER_M / 1_000_000 +
                output_tokens * self.OUTPUT_COST_PER_M / 1_000_000)

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> GenerationResult:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            request = {
                "model": self.model,
                "messages": messages,
            }
            # gpt-5 models require max_completion_tokens instead of max_tokens.
            if self.model.lower().startswith("gpt-5"):
                request["max_completion_tokens"] = max_tokens
            else:
                request["max_tokens"] = max_tokens

            response = self.client.chat.completions.create(**request)

            text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self.estimate_cost(input_tokens, output_tokens)

            logger.info(f"{self.model}: {input_tokens} in / {output_tokens} out, ${cost:.4f}")

            return GenerationResult(
                text=text,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost
            )

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, e: Exception):
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str:
            raise TransientError(f"OpenAI rate limit: {e}")
        elif "unauthorized" in error_str or "401" in error_str:
            raise FatalError(f"Invalid OpenAI API key: {e}")
        else:
            raise TransientError(f"OpenAI error: {e}")


class GeminiProvider(BaseProvider):
    """Google Gemini API provider."""

    # Cost per million tokens for Gemini 1.5 Pro (as of 2024)
    INPUT_COST_PER_M = 0.35
    OUTPUT_COST_PER_M = 1.05
    DEFAULT_MODEL = "gemini-1.5-pro"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise FatalError("GOOGLE_API_KEY not set")

        self.model_name = model or self.DEFAULT_MODEL

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.model = genai.GenerativeModel(self.model_name)
        except ImportError:
            raise FatalError("google-generativeai package not installed")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.INPUT_COST_PER_M / 1_000_000 +
                output_tokens * self.OUTPUT_COST_PER_M / 1_000_000)

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> GenerationResult:
        try:
            # Combine system and user prompt for Gemini
            full_prompt = prompt
            if system:
                full_prompt = f"{system}\n\n{prompt}"

            response = self.model.generate_content(
                full_prompt,
                generation_config=self.genai.GenerationConfig(
                    max_output_tokens=max_tokens
                )
            )

            text = response.text

            # Gemini doesn't always provide token counts directly
            # Estimate based on text length (rough approximation)
            input_tokens = len(full_prompt) // 4
            output_tokens = len(text) // 4
            cost = self.estimate_cost(input_tokens, output_tokens)

            logger.info(f"{self.model_name}: ~{input_tokens} in / ~{output_tokens} out, ~${cost:.4f}")

            return GenerationResult(
                text=text,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost
            )

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, e: Exception):
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
            raise TransientError(f"Gemini rate limit/quota: {e}")
        elif "api key" in error_str or "401" in error_str:
            raise FatalError(f"Invalid Gemini API key: {e}")
        else:
            raise TransientError(f"Gemini error: {e}")


class OpenRouterProvider(BaseProvider):
    """OpenRouter API provider (OpenAI-compatible)."""

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise FatalError("OPENROUTER_API_KEY not set")

        # Strip the "openrouter/" prefix to get the actual model ID
        self.model = model or ""
        if self.model.lower().startswith("openrouter/"):
            self.model = self.model[len("openrouter/"):]

        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.DEFAULT_BASE_URL
            )
        except ImportError:
            raise FatalError("openai package not installed")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # OpenRouter returns cost info in the response; return 0 as placeholder
        return 0.0

    @retry_with_backoff(max_retries=3, initial_delay=2.0)
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> GenerationResult:
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens
            )

            text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0
            cost = self.estimate_cost(input_tokens, output_tokens)

            logger.info(f"openrouter/{self.model}: {input_tokens} in / {output_tokens} out")

            return GenerationResult(
                text=text,
                model=f"openrouter/{self.model}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost
            )

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, e: Exception):
        error_str = str(e).lower()
        if "rate limit" in error_str or "429" in error_str:
            raise TransientError(f"OpenRouter rate limit: {e}")
        elif "unauthorized" in error_str or "401" in error_str:
            raise FatalError(f"Invalid OpenRouter API key: {e}")
        else:
            raise TransientError(f"OpenRouter error: {e}")


class AIClient:
    """AI client supporting Claude, GPT, Gemini, and OpenRouter models."""

    # Model prefix to implementation class mapping
    _IMPLEMENTATIONS = {
        'openrouter/': OpenRouterProvider,
        'claude': ClaudeProvider,
        'gpt-': OpenAIProvider,
        'o1-': OpenAIProvider,
        'o3-': OpenAIProvider,
        'chatgpt': OpenAIProvider,
        'gemini': GeminiProvider,
    }

    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize AI client.

        Args:
            model: Model name (e.g., 'claude-sonnet-4-5-20250929', 'gpt-4o', 'gemini-1.5-pro').
                   Defaults to AI_MODEL env var or 'gpt-4o'.
            api_key: API key (uses appropriate env var if not provided)
        """
        self.model = model or os.getenv('AI_MODEL', self.DEFAULT_MODEL)

        # Find the right implementation for this model
        impl_class = None
        model_lower = self.model.lower()
        for prefix, cls in self._IMPLEMENTATIONS.items():
            if model_lower.startswith(prefix):
                impl_class = cls
                break

        if not impl_class:
            raise FatalError(
                f"Unknown model: {self.model}. "
                f"Supported prefixes: openrouter/, claude, gpt-, o1-, o3-, gemini"
            )

        self._impl = impl_class(api_key, self.model)
        logger.info(f"AI client initialized: {self.model}")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096
    ) -> GenerationResult:
        """
        Generate text.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            max_tokens: Maximum output tokens

        Returns:
            GenerationResult with generated text and metadata
        """
        return self._impl.generate(prompt, system, max_tokens)

    def generate_with_context(
        self,
        system: str,
        user: str,
        context_files: Optional[List[str]] = None,
        max_tokens: int = 8192
    ) -> GenerationResult:
        """
        Generate with additional file context.

        Args:
            system: System prompt with instructions
            user: User prompt
            context_files: List of file contents to include as context
            max_tokens: Maximum output tokens

        Returns:
            GenerationResult with generated text and metadata
        """
        prompt_parts = []

        if context_files:
            prompt_parts.append("=== Context Files ===")
            for i, content in enumerate(context_files, 1):
                prompt_parts.append(f"\n--- File {i} ---\n{content}")
            prompt_parts.append("\n=== End Context ===\n")

        prompt_parts.append(user)
        full_prompt = "\n".join(prompt_parts)

        return self._impl.generate(full_prompt, system, max_tokens)
