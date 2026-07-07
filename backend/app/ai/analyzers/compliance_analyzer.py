import json
from backend.app.ai.llm.gemini_client import GeminiClient
from backend.app.ai.prompt_loader import PromptLoader
from backend.app.ai.dto.conversation import ConversationResult
from backend.app.ai.dto.analysis import ComplianceAnalysis
from backend.app.ai.analyzers.utils import validate_and_parse_json

class ComplianceAnalyzer:
    """
    Script Compliance analyzer agent checking identity verification, disclosures, and consent.
    """
    def __init__(self, client: GeminiClient = None) -> None:
        self.client = client or GeminiClient()

    def analyze(self, conversation: ConversationResult) -> ComplianceAnalysis:
        conversation_text = "\n".join(f"{s.speaker}: {s.text}" for s in conversation.segments)
        
        schema_json = json.dumps(ComplianceAnalysis.model_json_schema(), indent=2)
        prompt = PromptLoader.load_prompt("compliance", conversation_text, schema_json)
        
        raw_response = self.client.generate(prompt, schema_json)
        return validate_and_parse_json(
            self.client, 
            raw_response, 
            conversation_text, 
            ComplianceAnalysis, 
            "compliance"
        )
