# llm.py

from __future__ import annotations

from functools import lru_cache

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from config import settings


@lru_cache(maxsize=1)
def get_llm():

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0,
        timeout=800,
        max_retries=2,
    )


def build_structured_chain(
    system_prompt: str,
    output_model: type[BaseModel],
) -> Runnable:

    parser = PydanticOutputParser(
        pydantic_object=output_model
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                system_prompt
                + "\n\n"
                + "You MUST follow these output instructions:\n"
                + "{format_instructions}",
            ),
            (
                "human",
                "{input}",
            ),
        ]
    )

    return (
        prompt.partial(
            format_instructions=parser.get_format_instructions()
        )
        | get_llm()
        | parser
    )
if __name__ == "__main__":

    from pydantic import BaseModel
    from langchain_core.output_parsers import PydanticOutputParser
    from langchain_core.prompts import PromptTemplate


    class TestResponse(BaseModel):
        message: str
        success: bool


    parser = PydanticOutputParser(
        pydantic_object=TestResponse
    )


    prompt = PromptTemplate(
        template="""
You are testing an LLM connection.

Return a response confirming that the model test was successful.

{format_instructions}

User request:
{user_input}
""",
        input_variables=["user_input"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        },
    )


    llm = get_llm()

    chain = prompt | llm | parser


    try:
        result = chain.invoke({
            "user_input": "Say hello and confirm that the LLM test succeeded."
        })

        print("\n========== LLM TEST ==========")
        print("Message :", result.message)
        print("Success :", result.success)
        print("Type    :", type(result).__name__)
        print("==============================\n")

    except Exception as e:

        print("\n========== LLM TEST FAILED ==========")
        print("Error type :", type(e).__name__)
        print("Error      :", str(e))
        print("=====================================\n")