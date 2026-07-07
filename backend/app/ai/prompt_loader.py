import os
from backend.app.core.logging import get_logger

logger = get_logger("ANALYSIS")

class PromptLoader:
    # In-memory dictionary cache to prevent repeated disk read IO operations
    _cache = {}

    @classmethod
    def load_prompt(cls, prompt_name: str, conversation_text: str, schema_json: str) -> str:
        """
        Loads prompt template files located in backend/app/ai/prompts/{prompt_name}.txt.
        Formats the template by injecting the conversation transcript text and the JSON validation schema.
        """
        if prompt_name not in cls._cache:
            dir_path = os.path.dirname(__file__)
            file_path = os.path.join(dir_path, "prompts", f"{prompt_name}.txt")
            
            logger.info(f"Loading prompt template from filesystem: {prompt_name}")
            if not os.path.exists(file_path):
                logger.error(f"Prompt file not found at path: {file_path}")
                raise FileNotFoundError(f"Prompt template file not found at: {file_path}")
                
            with open(file_path, "r", encoding="utf-8") as f:
                cls._cache[prompt_name] = f.read()
                
        template = cls._cache[prompt_name]
        return template.format(conversation=conversation_text, schema=schema_json)
