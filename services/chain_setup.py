from format import QueryResponse,ExtractedJSON
from format import SYSTEM_PROMPT, USER_PROMPT  
from format import ExtractedJSON
from core import settings
import json
from typing import Any, Dict, List, Union
from langchain.callbacks.base import AsyncCallbackHandler, BaseCallbackHandler
from langchain_core.outputs import LLMResult
import asyncio
import logging
from typing import List, Union
from openai import  AsyncOpenAI, NOT_GIVEN
from format import QueryResponse, ExtractedJSON
from functools import partial

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)    
logger = logging.getLogger(__name__)


class MyCustomSyncHandler(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        logger.debug(f"Token received: {token}")


class MyCustomAsyncHandler(AsyncCallbackHandler):
    async def on_chat_model_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        logger.info("LLM processing started...")
        await asyncio.sleep(0.1)  # Simulate async task
        logger.info("Preparation done.")

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        logger.info("LLM processing completed.")
        await asyncio.sleep(0.1)  # Simulate async task
        logger.info("Cleanup done.")

class DictFilter:
    def __init__(self, data: Dict):
        self.orig_data = data['data']
        self.filtered_data = {}
        self.filtered_data['data'] = {}
        self.filtered_data['success'] = data['success']
        self.filtered_data['error'] = data['error']
        
    def _is_about_real_estate(self):
        return self.orig_data['about_real_estate']
    
    def filter_dict(self):
        filtered_dict = {}
        filtered_dict['about_real_estate'] = self._is_about_real_estate()
        property_specs = {}
        
        if self._is_about_real_estate():
            property_specs.update({k: v for k, v in self.orig_data.items() if v is not None})
            del property_specs['about_real_estate']
            
            if property_specs.get('property_type', None):
                property_specs['property_type'] = [k for k, v in property_specs['property_type'].items() if v]
                if not property_specs['property_type']:
                    del property_specs['property_type']
            
            if property_specs.get('listing_type', None):
                property_specs['listing_type'] = [{k: v} for k, v in property_specs['listing_type'].items() if v]
                
                # property_specs['listing_type'] = [d if 'for_rent' in d else list(d.keys())[0]  for d in property_specs['listing_type']]
                if not property_specs['listing_type']:
                    property_specs['listing_type'] = [{'primary_sale': True}]
                    
                    
            ## if they want to assume the listing type, uncomment the following code ##
            # else:
            #     property_specs['listing_type'] = [{'primary_sale': True}, {'resale': True}]
            
            if len(property_specs)==1 and property_specs.get('listing_type', None):
                del property_specs['listing_type']
                # property_specs = None
        
        
        filtered_dict['property_specs'] = property_specs
        self.filtered_data['data'] = filtered_dict
        return self.filtered_data

class PropertyChain:
    def __init__(self):
        # Initialize the parser (which converts a JSON string into an ExtractedJSON instance)
        self.parser = json

        # Build the system message using the JSON schema of ExtractedJSON
        json_schema = ExtractedJSON.model_json_schema()
        formatted_schema = json.dumps(json_schema, indent=2)
        escaped_schema = formatted_schema.replace("{", "{{").replace("}", "}}")
        self.system_message = SYSTEM_PROMPT.format(json_schema=escaped_schema)
        
        # Save the user prompt template (assumed to have the proper placeholders)
        self.prompt_template = USER_PROMPT
        
        # Set up the LLM parameters
        self.model_name = settings.MODEL_NAME
        self.temperature = 0.0
        self.response_format = ExtractedJSON  # This is passed to the API for formatting
        
        # Use your async OpenAI client (should be an instance of AsyncOpenAI or similar)
        self.client = openai_client

        self.completion_parser = partial(
            self.client.beta.chat.completions.parse,
            model=self.model_name,
            temperature=self.temperature,
            response_format=self.response_format
        )

    async def get_completion(self, messages: List[dict]) -> str:
        """
        Calls the preconfigured OpenAI endpoint with the given messages and returns
        the content of the first completion message.
        """
        # Now only 'messages' needs to be passed to the API.
        completion = await self.completion_parser(messages=messages)
        result = completion.choices[0].message
        return result.content


    async def format_user_message(self, template: str, text: Union[str, dict]) -> str:
        """
        Formats the user prompt. If `text` is a string it will be inserted as a positional
        argument; if a dict, it is expanded as keyword arguments.
        """
        if isinstance(text, str):
            return template.format(text)
        elif isinstance(text, dict):
            return template.format(**text)

    async def format_one_example(self, user_template: str, text: Union[str, dict], system_message: str) -> dict:
        """
        Creates the message payload with a system message and a formatted user prompt.
        """
        return {
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": await self.format_user_message(user_template, text)
                }
            ]
        }

    async def extract_info(self, text: Union[str, dict]) -> str:
        """
        Uses the prompt template and system message to create a chat message list,
        then calls the OpenAI API to get a completion.
        """
        logger.info(f"Extracting information from the user query: {text}")
        # Prepare the messages to send to the LLM.
        messages_payload = await self.format_one_example(self.prompt_template, text, self.system_message)
        messages = messages_payload["messages"]
        # Call the API.
        result = await self.get_completion(messages)
        logger.info(f"LLM response received successfully: {result}")
        return result

    async def extract(self, query: str) -> QueryResponse:
        """
        Calls the extraction routine and then parses the raw response (a JSON string)
        into an ExtractedJSON model using the parser.
        """
        raw_result = await self.extract_info(query)
        # Parse the LLM’s raw response into a structured model.
        parsed_result = self.parser.loads(raw_result)
        temp = QueryResponse(success=True, data=parsed_result)
        return QueryResponse(success=True, data=parsed_result)

    async def gen_extracted_info(self, query: str) -> QueryResponse:
        """
        Wraps the extract() method and applies additional filtering if needed.
        (Here, we filter the dictionary representation of the parsed model.)
        """
        extracted_info = await self.extract(query)
        info_filtered = DictFilter(extracted_info.model_dump()).filter_dict()
        return info_filtered
    
