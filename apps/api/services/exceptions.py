class PersonaAccessDenied(Exception):
    pass


class LLMServiceUnavailable(Exception):
    def __init__(self, persona_id):
        self.persona_id = persona_id
        super().__init__(f"LLM service unavailable for persona {persona_id}")


class LLMRequestInvalid(Exception):
    pass
