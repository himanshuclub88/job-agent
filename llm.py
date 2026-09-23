import json
import time

from openai import OpenAI


def make_nvidia_schema(schema):
    """
    NVIDIA structured-output JSON Schema requires
    additionalProperties=false on every object.
    """

    schema_json = schema.model_json_schema()

    def fix_object(obj):
        if isinstance(obj, dict):

            if obj.get("type") == "object":
                obj["additionalProperties"] = False

            for value in obj.values():
                fix_object(value)

        elif isinstance(obj, list):

            for item in obj:
                fix_object(item)

    fix_object(schema_json)

    return schema_json


class LLMClient:

    def __init__(self, settings):

        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        self.model = settings.llm_model

    def structured(self, system_prompt, user_prompt, schema):

        last_error = None

        response_schema = make_nvidia_schema(schema)

        for attempt in range(3):

            try:

                response = self.client.chat.completions.create(

                    model=self.model,

                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],

                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema.__name__,
                            "schema": response_schema,
                            "strict": True,
                        },
                    },

                    temperature=0,

                    max_tokens=4096,

                    timeout=120,
                )

                content = response.choices[0].message.content

                data = json.loads(content)

                return schema.model_validate(data)

            except Exception as e:

                last_error = e

                print(
                    f"LLM request failed "
                    f"(attempt {attempt + 1}/3): "
                    f"{type(e).__name__}: {e}"
                )

                if attempt < 2:

                    wait = 2 ** attempt

                    print(
                        f"Retrying in {wait} seconds..."
                    )

                    time.sleep(wait)

        raise last_error


if __name__ == "__main__":

    from pydantic import BaseModel
    from config import settings


    class TestResponse(BaseModel):
        message: str
        success: bool


    llm = LLMClient(settings)

    result = llm.structured(

        system_prompt=(
            "Return a JSON response matching the schema."
        ),

        user_prompt=(
            "Say hello and indicate that the test succeeded."
        ),

        schema=TestResponse,
    )

    print("\nRESULT:")
    print(result)