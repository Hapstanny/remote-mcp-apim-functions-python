from dataclasses import dataclass
import json
import logging
import os

import azure.functions as func

from datetime import timedelta
from semantic_kernel.agents.open_ai.run_polling_options import RunPollingOptions

from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread
from semantic_kernel.contents import ChatMessageContent, FunctionCallContent, FunctionResultContent
from dotenv import load_dotenv


import requests
import json
import pprint
import typing as t
import time
import uuid

from openai import OpenAI
from openai._exceptions import APIStatusError
from openai._models import FinalRequestOptions
from openai._types import Omit
from openai._utils import is_given
# from synapse.ml.mlflow import get_mlflow_env_config
from sempy.fabric._token_provider import SynapseTokenProvider
from azure.identity import ClientSecretCredential
# from powerbiclient.authentication import InteractiveLoginAuthentication
import openai
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import APIConnectionError

load_dotenv()


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Constants for the Azure Blob Storage container, file, and blob path
_SNIPPET_NAME_PROPERTY_NAME = "snippetname"
_SNIPPET_PROPERTY_NAME = "snippet"
_USER_INPUT_PROPERTY_NAME = "userinput"
_BLOB_PATH = "snippets/{mcptoolargs." + _SNIPPET_NAME_PROPERTY_NAME + "}.json"


@dataclass
class ToolProperty:
    propertyName: str
    propertyType: str
    description: str


# Define the tool properties using the ToolProperty class
tool_properties_save_snippets_object = [
    ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet."),
    ToolProperty(_SNIPPET_PROPERTY_NAME, "string", "The content of the snippet."),
]

tool_properties_get_snippets_object = [ToolProperty(_SNIPPET_NAME_PROPERTY_NAME, "string", "The name of the snippet.")]
tool_properties_get_user_input_object = [ToolProperty(_USER_INPUT_PROPERTY_NAME, "string", "The user input for the agent.")]

# Convert the tool properties to JSON
tool_properties_save_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_save_snippets_object])
tool_properties_get_snippets_json = json.dumps([prop.__dict__ for prop in tool_properties_get_snippets_object])
tool_properties_get_user_input_json = json.dumps([prop.__dict__ for prop in tool_properties_get_user_input_object])

@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="hello_mcp",
    description="Hello world.",
    toolProperties="[]",
)
def hello_mcp(context) -> str:
    """
    A simple function that returns a greeting message.

    Args:
        context: The trigger context (not used in this function).

    Returns:
        str: A greeting message.
    """
    return "Hello I am MCPTool!"


# @app.generic_trigger(
#     arg_name="context",
#     type="mcpToolTrigger",
#     toolName="get_snippet",
#     description="Retrieve a snippet by name.",
#     toolProperties=tool_properties_get_snippets_json,
# )
# @app.generic_input_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_BLOB_PATH)
# def get_snippet(file: func.InputStream, context) -> str:
#     """
#     Retrieves a snippet by name from Azure Blob Storage.

#     Args:
#         file (func.InputStream): The input binding to read the snippet from Azure Blob Storage.
#         context: The trigger context containing the input arguments.

#     Returns:
#         str: The content of the snippet or an error message.
#     """
#     snippet_content = file.read().decode("utf-8")
#     logging.info("Retrieved snippet: %s", snippet_content)
#     return snippet_content


# @app.generic_trigger(
#     arg_name="context",
#     type="mcpToolTrigger",
#     toolName="save_snippet",
#     description="Save a snippet with a name.",
#     toolProperties=tool_properties_save_snippets_json,
# )
# @app.generic_output_binding(arg_name="file", type="blob", connection="AzureWebJobsStorage", path=_BLOB_PATH)
# def save_snippet(file: func.Out[str], context) -> str:
#     content = json.loads(context)
#     if "arguments" not in content:
#         return "No arguments provided"

#     snippet_name_from_args = content["arguments"].get(_SNIPPET_NAME_PROPERTY_NAME)
#     snippet_content_from_args = content["arguments"].get(_SNIPPET_PROPERTY_NAME)

#     if not snippet_name_from_args:
#         return "No snippet name provided"

#     if not snippet_content_from_args:
#         return "No snippet content provided"

#     file.set(snippet_content_from_args)
#     logging.info("Saved snippet: %s", snippet_content_from_args)
#     return f"Snippet '{snippet_content_from_args}' saved successfully"


@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="fabricdataagent_mcp",
    description="Calling Fabric Data Agent MCP Tool",
    toolProperties=tool_properties_get_user_input_json,
)
def fabricdataagent_mcp(context) -> str:

    content = json.loads(context)
    if "arguments" not in content:
        return "No arguments provided"

    user_input_from_args = content["arguments"].get(_USER_INPUT_PROPERTY_NAME)
    print(user_input_from_args)

    logging.info("User Input: %s", user_input_from_args)
    logging.info("MCP Data agent with user input: %s", user_input_from_args)


# from azure.identity import DefaultAzureCredential
 
    base_url = os.getenv("base_url")
    question = user_input_from_args



    # Create OpenAI Client
    class FabricOpenAI(OpenAI):
        def __init__(
            self,
            api_version: str ="2024-05-01-preview",
            **kwargs: t.Any,
        ) -> None:
            self.api_version = api_version
            default_query = kwargs.pop("default_query", {})
            default_query["api-version"] = self.api_version
            super().__init__(
                api_key="",
                base_url=base_url,
                default_query=default_query,
                **kwargs,
            )
    


        # def getToken():
        #     # Initialize the credential
        #     credential = DefaultAzureCredential()

        #     # Acquire an access token for a specific scope
        #     token = credential.get_token("https://management.azure.com/.default")

        #     # Access the token value
        #     print("Access Token:", token.token)
        #     logging.info("Fetching Access Token")
        #     return token.token


        scopes = ["https://api.fabric.microsoft.com/.default","https://api.fabric.microsoft.com/Workspace.ReadWrite.All", "https://api.fabric.microsoft.com/Item.ReadWrite.All"]


        credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET")
        )


        def _prepare_options(self, options: FinalRequestOptions) -> None:
            headers: dict[str, str | Omit] = (
                {**options.headers} if is_given(options.headers) else {}
            )
            options.headers = headers
            # headers["Authorization"] = f"Bearer {configs.driver_aad_token}"
            # interactive_auth  = InteractiveLoginAuthentication()
            # TOKEN = interactive_auth.get_access_token()
            # print(":" + super()._authenticate())
            # TOKEN = self.getToken()
            # credential = DefaultAzureCredential()
            token = self.credential.get_token(self.scopes[0])
            TOKEN = token.token
            logging.info("Token Generated")

            headers["Authorization"] = f"Bearer {TOKEN}"
            if "Accept" not in headers:
                headers["Accept"] = "application/json"
            if "ActivityId" not in headers:
                correlation_id = str(uuid.uuid4())
                headers["ActivityId"] = correlation_id

            return super()._prepare_options(options)

# Pretty printing helper
    def pretty_print(messages):
        print("---Conversation---")
        for m in messages:
            print(f"{m.role}: {m.content[0].text.value}")
            logging.info(f"{m.role}: {m.content[0].text.value}")
        print()


    @retry(
    retry=retry_if_exception_type(APIConnectionError),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5)
    )
    def create_assistant(fabric_client):
        logging.info("Creating assistant")
        return fabric_client.beta.assistants.create(model="not used")

    

    fabric_client = FabricOpenAI()
    assistant= None
    
   
    try:
        assistant =  create_assistant(fabric_client)
        # # time.sleep(5)
        # logging.info("First Assistant created: %s", assistant.id)
        # while assistant.id is None:
        #     # assistant = fabric_client.beta.assistants.create(model="not used")
        #     time.sleep(2)
        #     logging.info("sleeping 2 secs")
    except APIConnectionError as e:
        logging.error("Error creating assistant: %s", e.with_traceback())
        # return f"Error creating assistant: {str(e)}"
    # finally:
    #     await time.sleep(15)
    #     logging.info("sleeping 15 secs")
    #     # assistant = fabric_client.beta.assistants.create(model="not used")
        
    logging.info("Assistant created: %s", assistant.id)

    # Create thread
    thread =  fabric_client.beta.threads.create()
    # Create message on thread
    message =  fabric_client.beta.threads.messages.create(thread_id=thread.id, role="user", content=question)

    logging.info("Message: %s", message)
    # Create run
    run =  fabric_client.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
    logging.info("run: %s", run)
       

# Wait for run to complete
    while run.status == "queued" or run.status == "in_progress":
        run = fabric_client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        print(run.status)
        logging.info("Run status: %s", run.status)
        time.sleep(2)

    # Print messages
    response = fabric_client.beta.threads.messages.list(thread_id=thread.id, order="asc")
    pretty_print(response)
    logging.info("Response: %s", response)

    # Delete thread
    # fabric_client.beta.threads.delete(thread_id=thread.id)




@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="StockMarketAnalyzer_agent_mcp",
    description="Calling Stock Market Analyzer Foundry Agent MCP Tool",
    toolProperties=tool_properties_get_user_input_json,
)
async def StockMarketAnalyzer_agent_mcp(context) -> str:
    """
    Calling Stock Market Analyzer Foundry Agent MCP Tool
    """
    content = json.loads(context)
    if "arguments" not in content:
        return "No arguments provided"

    user_input_from_args = content["arguments"].get(_USER_INPUT_PROPERTY_NAME)
    logging.info("MCP Data agent with user input: %s", user_input_from_args)

    try: 
            api_version="2025-05-15-preview"
            creds = DefaultAzureCredential()
           
            endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
            agent_id = os.getenv("STA_AZURE_AI_AGENT_ID")
            api_version = os.getenv("AZURE_AI_AGENT_API_VERSION")

            polling_options = RunPollingOptions(   # Total time to wait
                 run_polling_interval=timedelta(seconds=30),
                 run_polling_backoff=timedelta(seconds=30),
                 default_polling_interval=timedelta(seconds=30),
                 default_polling_backoff=timedelta(seconds=30)
                   )

            if not endpoint or not agent_id:
                logging.error("Missing environment configuration: endpoint or agent_id.")
                return "Configuration error: missing endpoint or agent ID."

            # Create an Azure AI Agent client
      
            client = AzureAIAgent.create_client(
                credential=creds,
                endpoint=endpoint,
                api_version=api_version)
            
            agent_definition = await client.agents.get_agent(
                agent_id=agent_id
            )

            logging.info("User Input: %s", agent_id)
            logging.info("Agent Definition: %s", agent_definition)
            logging.info("Starting agent agent")

            agent = AzureAIAgent(
                client=client,
                definition=agent_definition,
                polling_options=polling_options)

            thread: AzureAIAgentThread = None

            logging.info("Starting agent invocation with definition")

            async for message in agent.invoke(
                messages=user_input_from_args, 
                thread=thread,
                on_intermediate_message=handle_intermediate_steps):
                response = message

                print(f"Agent response: {response}", end="", flush=True)
                thread = response.thread
                
            logging.info(f"Agent response final: {response}")
            return f"{response if response else 'No response'}"

    except Exception as e:
        logging.error("Error invoking agent: %s", e)
        return f"Error: {str(e)}"


    finally:
        await thread.delete() if thread else None
        await creds.close()
        if client:
            await client.close()

    # return f"{response.message.content if response else 'No response'}"



        # try:
        #     while True:
        #         user_input = user_input_from_agrs
        #         if not user_input.strip():
        #             print("No input provided. Exiting the conversation.")
        #             break
        #         print(f"# User: '{user_input}'")
        #         # 4. Invoke the agent for the specified thread for response
        #         for response in agent.invoke(
        #             messages=user_input,
        #             thread=thread
        #             # on_intermediate_message=handle_intermediate_steps,
        #         ):
        #             # Print the agent's response
        #             print(f"{response}", end="", flush=True)
        #             # Update the thread for subsequent messages
        #             thread = response.thread
        #             # If the response is a final message, print it
        #             # if response.is_final:
        #             #     print(f"\n# Agent: {response.content}")
        #             #     break
        #         # If the user input is empty, break the loop
                
        # # Handle keyboard interrupt to gracefully exit the conversation            
        # except:
        #     print("error in invoking agent.")
                        
        # return f"{response}.\n"

 

async def handle_intermediate_steps(message: ChatMessageContent) -> None:
    for item in message.items or []:
        if isinstance(item, FunctionResultContent):
            print(f"Function Result:> {item.result} for function: {item.name}")
        elif isinstance(item, FunctionCallContent):
            print(f"Function Call:> {item.name} with arguments: {item.arguments}")
        else:
            print(f"{item}")



@app.generic_trigger(
    arg_name="context",
    type="mcpToolTrigger",
    toolName="AISearch_Agent_mcp",
    description="Calling AI state readiness and AI adoption and transformation among employee and their experience. Its aFoundry Agent MCP Tool",
    toolProperties=tool_properties_get_user_input_json,
)
async def AISearch_Agent_mcp(context) -> str:
    """
    Calling Foundry Agent MCP Tool
    """
    content = json.loads(context)
    if "arguments" not in content:
        return "No arguments provided"

    user_input_from_args = content["arguments"].get(_USER_INPUT_PROPERTY_NAME)
    print(user_input_from_args)

    logging.info("User Input: %s", user_input_from_args)
    logging.info("MCP Data agent with user input: %s", user_input_from_args)

    try: 

            api_version="2025-05-15-preview"
            creds = DefaultAzureCredential()
           
            endpoint = os.getenv("AZURE_AI_AGENT_ENDPOINT")
            agent_id = os.getenv("AIS_AZURE_AI_AGENT_ID")
            api_version = os.getenv("AZURE_AI_AGENT_API_VERSION")

            logging.info(f"Loaded agent_id: {agent_id}")
            logging.info(f"Loaded endpoint: {endpoint}")
            logging.info(f"Loaded api_version: {api_version}")
            
            polling_options = RunPollingOptions(   # Total time to wait
                 run_polling_interval=timedelta(seconds=30),
                 run_polling_backoff=timedelta(seconds=30),
                 default_polling_interval=timedelta(seconds=30),
                 default_polling_backoff=timedelta(seconds=30)
                   )

            if not endpoint or not agent_id:
                logging.error("Missing environment configuration: endpoint or agent_id.")
                return "Configuration error: missing endpoint or agent ID."

            # Create an Azure AI Agent client
      
            client = AzureAIAgent.create_client(
                credential=creds,
                endpoint=endpoint,
                api_version=api_version)
            
            agent_definition = await client.agents.get_agent(
                agent_id=agent_id
            )

            logging.info("User Input: %s", agent_id)
            logging.info("Agent Definition: %s", agent_definition)

            logging.info("Starting agent agent")

            agent = AzureAIAgent(
                client=client,
                definition=agent_definition,
                polling_options=polling_options)

            thread: AzureAIAgentThread = None

            logging.info("Starting agent invocation with definition")
            
            async for message in agent.invoke(
                messages=user_input_from_args, 
                thread=thread,
                on_intermediate_message=handle_intermediate_steps):
                response = message

                print(f"Agent response: {response}", end="", flush=True)
                thread = response.thread
                
            logging.info(f"Agent response final: {response}")
            return f"{response if response else 'No response'}"


    except Exception as e:
        logging.error("Error invoking agent: %s", e)
        return f"Error: {str(e)}"


    finally:
        await thread.delete() if thread else None
        await creds.close()
        if client:
            await client.close()
