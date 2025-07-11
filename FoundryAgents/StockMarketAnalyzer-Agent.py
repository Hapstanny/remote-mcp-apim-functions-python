"""
this code creates an Azure AI Agent using the Azure AI Projects SDK, 
attaches a Code Interpreter tool, and processes a message in a thread.
It demonstrates how to create an agent, send a message, and handle the response.
"""


import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential,AzureDeveloperCliCredential
from azure.ai.agents.models import CodeInterpreterTool,BingGroundingTool


from dotenv import load_dotenv

load_dotenv()
# Create an Azure AI Client from an endpoint, copied from your Azure AI Foundry project.
AGENT_NAME="StockMarketAnalyzer"
AGENT_INSTRUCTIONS=os.environ[AGENT_NAME]
bing_conn_id=os.environ["BING_CONNECTION_ID"]  
user_question="Research about MSFT"  # Example user question


project_endpoint = os.environ["AZURE_AI_AGENT_ENDPOINT"]  # Ensure the PROJECT_ENDPOINT environment variable is set
# cred=AzureDeveloperCliCredential(tenant_id=os.environ["AZURE_TENANT_ID"])
cred=DefaultAzureCredential()

# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=cred,  # Use Azure Default Credential for authentication
    api_version=os.environ["AZURE_AI_AGENT_API_VERSION"],  # Use the API version from environment variable
)

# code_interpreter = CodeInterpreterTool()
bing_grounding = BingGroundingTool(connection_id=bing_conn_id)  # Ensure the BING_GROUNDING_CONNECTION_ID environment variable is set
with project_client:
    # Create an agent with the Bing Grounding tool
    agent = project_client.agents.create_agent(
        model=os.environ["MODEL_DEPLOYMENT_NAME"],  # Model deployment name
        name=AGENT_NAME,  # Name of the agent
        instructions=AGENT_INSTRUCTIONS,  # Instructions for the agent
        tools=bing_grounding.definitions  # Attach the tools
    )
    print(f"Created agent, ID: {agent.id}")

    # Create a thread for communication
    thread = project_client.agents.threads.create()
    print(f"Created thread, ID: {thread.id}")
    
    # Add a message to the thread
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role="user",  # Role of the message sender
        content=user_question,  # Message content
    )
    print(f"Created message, ID: {message['id']}")
    
    # Create and process an agent run
    run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    print(f"Run finished with status: {run.status}")
    
    # Check if the run failed
    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
    
    # Fetch and log all messages
    messages = project_client.agents.messages.list(thread_id=thread.id)
    for message in messages:
        print(f"Role: {message.role}, Content: {message.content.value if hasattr(message.content, 'value') else message.content}")
    
    # Delete the agent when done
    project_client.agents.delete_agent(agent.id)
    print("Deleted agent")