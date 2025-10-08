from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from typing import Dict
import json

import os
from dotenv import load_dotenv

load_dotenv()

model = ChatOpenAI(
    model="gpt-4o-mini", 
    api_key=os.getenv("OPENAI_API_KEY"), 
    temperature=0.1,
    model_kwargs={"response_format": {"type": "json_object"}}
)

prompt = ChatPromptTemplate.from_template(
    """Summarize the following content in English with markdown formatting.
    Always respond in JSON format with this structure:
    {{{{
      "summary": "your detailed summary here",
      "expected_questions": ["question 1", "question 2", "question 3"]
    }}}}
    Provide exactly 3 relevant follow-up questions the user might have based on your summary.
    
    Content: {content}"""
)

chain = prompt | model | StrOutputParser()

def summarize_service(content: str) -> Dict[str, any]:
    result = chain.invoke({"content": content})
    response_data = json.loads(result)
    return {
        "summary": response_data.get("summary", ""),
        "expected_questions": response_data.get("expected_questions", [])
    }