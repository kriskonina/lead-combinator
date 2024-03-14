import asyncio
from functools import partial
import json
import openai
import logging
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
    ChatCompletionNamedToolChoiceParam
)
from openai.types.shared_params import FunctionDefinition

from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    TypedDict,
    cast
)
from fastapi import HTTPException
from starlette.status import (
    HTTP_503_SERVICE_UNAVAILABLE,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from tenacity import retry, stop_after_attempt, wait_random_exponential

from lead_combinator.backend.app.utils.function_to_jsonschema import function_to_json_schema
from lead_combinator.backend.hooks.openai_functions import Functions

callback_functions_list = [
    fn for fn_name in dir(Functions)
    if not fn_name.startswith('_') and callable(fn:=getattr(Functions, fn_name))
]

callback_functions: dict[str, tuple[Callable, FunctionDefinition]] = {
    fn.__name__: (fn, function_to_json_schema(fn))
    for fn in callback_functions_list
}

class ChunkResponse(TypedDict):
    id: str
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    # functions: 

# Configure logging
logger = logging.getLogger(__name__)

async def wrapper (to_call: partial[Any]):
    try:
        out = await to_call()
    except Exception as exc:
        print(f"Error calling function {to_call.func.__name__}: {exc}")
        raise
    return {
        "role": "function",
        "name": to_call.func.__name__,
        "content": json.dumps(out)
    }

class OpenAIService:
    def __init__(self):
        self.client = openai.AsyncOpenAI()
        self.loaded_callback_functions = {k: v[1] for k, v in callback_functions.items()}

    def get_function_calls (self, fns: list[ChoiceDeltaToolCall]):
        for fn in fns:
            function = fn.function
            if function and (name_fn:=function.name) and (ff:=callback_functions.get(name_fn)):
                try:
                    fn_args = json.loads(function.arguments or "[]")
                except json.JSONDecodeError as exc:
                    print(f"Error decoding arguments for function {name_fn}: {exc}")
                    raise
                to_call = partial(ff[0], *fn_args)
                yield wrapper(to_call)

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(min=1, max=20))
    async def generate_response(
        self,
        prompts: Iterable[ChatCompletionMessageParam],
        function_choice_name: Literal["none", "auto"] | str = 'auto',
        load_functions = False,
        **kwargs,
    ):
        if function_choice_name and function_choice_name not in self.loaded_callback_functions and function_choice_name not in ('auto', 'none'):
            logger.error(f"Function {function_choice_name} not found")
            raise ValueError(f"Function {function_choice_name} not found")

        function_choice = function_choice_name
        functions_spec = []

        if load_functions or function_choice_name:
            functions_spec = [ChatCompletionToolParam(function=fn, type='function') for fn in self.loaded_callback_functions.values()]

        if function_choice_name not in ('auto', 'none'):
            function_choice = ChatCompletionNamedToolChoiceParam(function={'name': function_choice_name}, type='function')

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=prompts,
                stream=True,
                temperature=0.7,
                max_tokens=150,
                response_format={"type": "json_object"},
                tools=functions_spec,
                tool_choice=cast(ChatCompletionNamedToolChoiceParam, function_choice),
                **kwargs,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                content = delta.content
                role = delta.role
                output = []
                if delta.tool_calls:
                    output = await asyncio.gather(self.get_function_calls(delta.tool_calls))
                try:
                    content = json.loads(content or '')
                except json.JSONDecodeError as exc:
                    logger.error(f"Error decoding content for chunk {chunk.id}: {exc}")
                    raise
                yield {
                    "id": chunk.id,
                    'content': content,
                    'role': role,
                    'fn_output': output
                }

            # Attempt to validate the response structure
            # validated_response = self._validate_response_structure(response)
            # return {"text": validated_response.choices[0].text.strip()}

        except openai.OpenAIError as e:
            logger.error(f"OpenAI service error: {e}")
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI service is currently unavailable.",
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred.",
            )

    # def _validate_response_structure(self, response: Dict[str, Any]) -> OpenAIResponseModel:
    #     # This method attempts to validate the OpenAI API response structure
    #     # using the defined Pydantic model.
    #     return OpenAIResponseModel(**response)



async def main():
    service = OpenAIService()
prompt = 'You will act as the most jovial and professional lead finder, who needs to find out exactly what his client does. Ask questions that can be answered through the usage of a modern UI. For that end, you will have to indicated in your answer what type of UI component must be rendered and with that properties. Ensure all your output is in JSON.'
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": prompt},
    ]
    async for chunk in service.generate_response(messages):
        print(chunk)

asyncio.run(main())