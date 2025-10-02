from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv

load_dotenv()

model = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.1)
prompt = ChatPromptTemplate.from_template(
  "Extract 4 to 5 keywords from the following content: {content}. "
  "Your output MUST be 4 to 5 keywords, including spaces. "
  "Each keyword must be a single word. "
  "Each keyword must not contain any special characters."
  "Each keyword must not be over 20 characters. "
  "Do not exceed 4 to 5 keywords under any circumstances. "
  "Text: {content}"
)

chain = prompt | model | StrOutputParser()
extract_keywords_from_content_prompt = ChatPromptTemplate.from_template("You have to extract the keywords from the {answer} in English. The output must not include any other text.")

composed_chain_with_lambda = (
  chain 
  | (lambda input_text: {"answer": input_text})
  | extract_keywords_from_content_prompt
  | model
  | StrOutputParser()
)

def extract_keywords_from_content_service(content: str) -> str:
  return composed_chain_with_lambda.invoke({"content": content})
