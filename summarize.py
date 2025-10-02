from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

import os
from dotenv import load_dotenv

load_dotenv()

model = ChatOpenAI(model="gpt-4.1-mini", api_key=os.getenv("OPENAI_API_KEY"), temperature=0.1)
prompt = ChatPromptTemplate.from_template("Summarize the following content: {content}")
chain = prompt | model | StrOutputParser()
summarize_prompt = ChatPromptTemplate.from_template("You have to summarize the {answer} in English and markdown formatting. The output must not include any other text.")

composed_chain_with_lambda = (
  chain 
  | (lambda input_text: {"answer": input_text})
  | summarize_prompt
  | model
  | StrOutputParser()
)

def summarize_service(content: str) -> str:
  return composed_chain_with_lambda.invoke({"content": content})