"""
Prompt Loader for loading prompts from external files.
Handles environment variable injection and prompt template rendering.
"""
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Loader for interview prompts from external markdown files.
    Handles prompt templates with variable substitution.
    """
    
    def __init__(self):
        """Initialize prompt loader."""
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self._file_cache: dict[str, str] = {}
        self._rendered_cache: dict[str, str] = {}
        self._MAX_RENDERED_CACHE = 200
        
        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {self.prompts_dir}")
    
    def _render(self, content: str, kwargs: dict[str, Any]) -> str:
        """Replace {{variable}} or {variable} placeholders in content."""
        for key, value in kwargs.items():
            double_brace_placeholder = f"{{{{{key}}}}}"
            single_brace_placeholder = f"{{{key}}}"

            # Prefer the exact {{key}} form; falling back to {key} only avoids
            # mangling double-brace templates into stray {value} braces.
            if double_brace_placeholder in content:
                content = content.replace(double_brace_placeholder, str(value))
            elif single_brace_placeholder in content:
                content = content.replace(single_brace_placeholder, str(value))
        return content

    def _load_cached(self, relative_path: str) -> str:
        """Read and cache a prompt file resolved under the prompts directory.

        Supports nested subdirectories (e.g. ``intelligence/company_brain.md``).
        """
        if relative_path not in self._file_cache:
            file_path = self.prompts_dir / relative_path
            if not file_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                self._file_cache[relative_path] = f.read()
        return self._file_cache[relative_path]

    def load(
        self,
        category: str,
        filename: str,
        **kwargs: Any
    ) -> str:
        """
        Load a prompt file and inject variables.
        
        Args:
            category: Category (system, interview, evaluation, intelligence)
            filename: Filename (e.g., "interviewer_system.md", "answer_evaluation.md")
            **kwargs: Variables to inject into the prompt template
            
        Returns:
            str: The rendered prompt
            
        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        cache_key = f"{category}/{filename}"

        if cache_key not in self._file_cache:
            if not (self.prompts_dir / category / filename).exists():
                raise FileNotFoundError(
                    f"Prompt file not found: {self.prompts_dir / category / filename}"
                )
            self._file_cache[cache_key] = self._load_cached(cache_key)

        content = self._file_cache[cache_key]
        
        # Generate rendered cache key from all inputs
        key_data = f"{category}/{filename}:{sorted(kwargs.items())}"
        rendered_key = hashlib.md5(key_data.encode()).hexdigest()
        
        if rendered_key in self._rendered_cache:
            logger.debug(f"Rendered prompt cache hit: {category}/{filename}")
            return self._rendered_cache[rendered_key]
        
        content = self._render(content, kwargs)
        
        if len(self._rendered_cache) < self._MAX_RENDERED_CACHE:
            self._rendered_cache[rendered_key] = content
        
        logger.info(f"Loaded prompt: {category}/{filename} with {len(kwargs)} variables")
        return content
    
    def load_system_prompt(self, filename: str, **kwargs: Any) -> str:
        """
        Load a system prompt from the system category.
        
        Args:
            filename: System prompt filename (e.g., "interviewer_system.md")
            **kwargs: Variables to inject
            
        Returns:
            str: Rendered system prompt
        """
        return self.load("system", filename, **kwargs)
    
    def load_interview_prompt(self, filename: str, **kwargs: Any) -> str:
        """
        Load an interview prompt from the interview category.
        
        Args:
            filename: Interview prompt filename (e.g., "question_generation.md")
            **kwargs: Variables to inject
            
        Returns:
            str: Rendered interview prompt
        """
        return self.load("interview", filename, **kwargs)
    
    def load_evaluation_prompt(self, filename: str, **kwargs: Any) -> str:
        """
        Load an evaluation prompt from the evaluation category.
        
        Args:
            filename: Evaluation prompt filename (e.g., "answer_evaluation.md")
            **kwargs: Variables to inject
            
        Returns:
            str: Rendered evaluation prompt
        """
        return self.load("evaluation", filename, **kwargs)
    
    def load_by_path(self, prompt_path: str, **kwargs: Any) -> str:
        """
        Load a prompt by file path relative to prompts directory.

        Args:
            prompt_path: Relative path (e.g., "system/interviewer_system.md",
                "intelligence/company_brain.md")
            **kwargs: Variables to inject
            
        Returns:
            str: Rendered prompt
        """
        content = self._load_cached(prompt_path)
        return self._render(content, kwargs)
    
    def list_prompts(self, category: str = None) -> list[str]:
        """
        List available prompts, recursing into nested subdirectories.

        Args:
            category: Optional category to filter by

        Returns:
            list[str]: List of prompt filenames
        """
        prompts = []

        category_dir = self.prompts_dir / category if category else self.prompts_dir

        if category_dir.exists() and category_dir.is_dir():
            for file_path in sorted(category_dir.rglob('*.md')):
                relative = file_path.relative_to(self.prompts_dir)
                prompts.append(str(relative).replace('\\', '/'))

        return prompts


# Singleton instance
_prompt_loader_instance: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """
    Get or create prompt loader singleton.
    
    Returns:
        PromptLoader: Singleton instance
    """
    global _prompt_loader_instance
    
    if _prompt_loader_instance is None:
        _prompt_loader_instance = PromptLoader()
    
    return _prompt_loader_instance


# Convenience functions
def load_prompt(category: str, filename: str, **kwargs) -> str:
    """
    Load a prompt with variables.
    
    Args:
        category: Category directory
        filename: Prompt filename
        **kwargs: Variables to inject
        
    Returns:
        str: Rendered prompt
    """
    return get_prompt_loader().load(category, filename, **kwargs)


def load_system_prompt(filename: str, **kwargs) -> str:
    """Load system prompt with variables."""
    return get_prompt_loader().load_system_prompt(filename, **kwargs)


def load_interview_prompt(filename: str, **kwargs) -> str:
    """Load interview prompt with variables."""
    return get_prompt_loader().load_interview_prompt(filename, **kwargs)


def load_evaluation_prompt(filename: str, **kwargs) -> str:
    """Load evaluation prompt with variables."""
    return get_prompt_loader().load_evaluation_prompt(filename, **kwargs)


def list_prompts(category: str = None) -> list[str]:
    """
    List available prompts.
    
    Args:
        category: Optional category to filter by
        
    Returns:
        list[str]: List of prompt filenames
    """
    return get_prompt_loader().list_prompts(category)