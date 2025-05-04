from typing import Dict

class Instructions:
    @staticmethod
    def get_knowledge_base_instructions() -> str:
        """Get the system instructions for knowledge base queries"""
        return """You are a knowledgeable assistant that provides accurate information based on the given context. 
        Follow these guidelines when answering:
        1) Only use information from the provided context
        2) If the answer isn't in the context, clearly state that
        3) Cite specific parts of the context when relevant"""

    @staticmethod
    def get_web_browsing_instructions() -> str:
        """Get the system instructions for web browsing capability"""
        return """You have the ability to browse the web. When a user asks for current information or recent updates, you can search the web to provide the most up-to-date information. Make sure to:
        1. Verify the information from multiple sources
        2. Provide citations or sources when possible
        3. Clearly indicate when information comes from web searches
        4. Use web browsing for current events, recent developments, or time-sensitive information"""

    @staticmethod
    def session_name_instructions() -> str:
        """Get the instructions to generate the session name from user query"""
        return """Generate a very short, objective name for this question. 
        The name should be 2-3 words maximum, focusing on the main topic.
        Do not include question words or phrases.
        Format the response as a single line."""
