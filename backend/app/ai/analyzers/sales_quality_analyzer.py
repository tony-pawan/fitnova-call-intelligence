import json
from backend.app.ai.llm.gemini_client import GeminiClient
from backend.app.ai.prompt_loader import PromptLoader
from backend.app.ai.dto.conversation import ConversationResult
from backend.app.ai.dto.analysis import SalesQualityAnalysis
from backend.app.ai.analyzers.utils import validate_and_parse_json

class SalesQualityAnalyzer:
    """
    Sales Quality analyzer agent checking tonality, active listening, objections, and call closing.
    """
    def __init__(self, client: GeminiClient = None) -> None:
        self.client = client or GeminiClient()

    def analyze(self, conversation: ConversationResult) -> SalesQualityAnalysis:
        conversation_text = "\n".join(f"{s.speaker}: {s.text}" for s in conversation.segments)
        
        schema_json = json.dumps(SalesQualityAnalysis.model_json_schema(), indent=2)
        prompt = PromptLoader.load_prompt("sales_quality", conversation_text, schema_json)
        
        raw_response = self.client.generate(prompt, schema_json)
        return validate_and_parse_json(
            self.client, 
            raw_response, 
            conversation_text, 
            SalesQualityAnalysis, 
            "sales_quality"
        )
