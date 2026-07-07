import json
from typing import Any
from pydantic import ValidationError  # pyrefly: ignore [missing-import]
from backend.app.ai.llm.gemini_client import GeminiClient
from backend.app.core.logging import get_logger

logger = get_logger("ANALYSIS")

def validate_and_parse_json(client: GeminiClient, raw_text: str, conversation_str: str, schema_class: Any, prompt_name: str) -> Any:
    """
    Parses raw response text and validates it against the target Pydantic schema class.
    If it fails, retries once using a JSON repair prompt.
    If it still fails, returns a default failed schema instance instead of crashing.
    """
    def clean_json_text(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    try:
        cleaned_text = clean_json_text(raw_text)
        return schema_class.model_validate_json(cleaned_text)
    except (ValidationError, json.JSONDecodeError) as err:
        logger.warning(f"[{prompt_name.upper()}] JSON schema validation failed: {err}. Retrying once with JSON repair prompt.")
        
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        repair_prompt = f"""
        You previously generated a response that failed validation against this JSON schema:
        {schema_json}

        Malformed response text:
        {raw_text}

        Validation error details:
        {str(err)}

        Please repair the JSON so it strictly matches the schema.
        Respond ONLY with a valid JSON object. Do NOT wrap in markdown fences or HTML blocks.
        """
        
        try:
            # Retry request once
            repair_text = client.generate(repair_prompt, schema_json)
            cleaned_repair = clean_json_text(repair_text)
            return schema_class.model_validate_json(cleaned_repair)
        except Exception as retry_err:
            logger.error(f"[{prompt_name.upper()}] JSON repair retry failed: {retry_err}")
            
            # Return structured analyzer failure DTO without crashing the pipeline
            return schema_class(
                score=0.0,
                summary=f"Analyzer execution failed: {str(retry_err)}",
                strengths=[],
                weaknesses=[],
                recommendations=[],
                issue_tags=["Analysis Failure"]
            )
