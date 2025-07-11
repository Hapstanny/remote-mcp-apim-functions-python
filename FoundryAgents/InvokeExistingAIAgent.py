# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os

from azure.identity.aio import DefaultAzureCredential,AzureDeveloperCliCredential

from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread
from semantic_kernel.contents import ChatMessageContent, FunctionCallContent, FunctionResultContent

"""
The following sample demonstrates how to use an already existing
Azure AI Agent within Semantic Kernel. This sample requires that you
have an existing agent created either previously in code or via the
Azure Portal (or CLI).
"""


# Simulate a conversation with the agent
USER_INPUTS = [
    "Using the provided doc, tell me about the evolution of RAG.",
]

from dotenv import load_dotenv

load_dotenv()

def get_user_input():
    """
    Prompt the user for input and return the entered value.

    Returns:
        str: The input provided by the user.
    """
    user_input = input("Enter your input: ")
    return user_input


async def handle_intermediate_steps(message: ChatMessageContent) -> None:
    for item in message.items or []:
        if isinstance(item, FunctionResultContent):
            print(f"Function Result:> {item.result} for function: {item.name}")
        elif isinstance(item, FunctionCallContent):
            print(f"Function Call:> {item.name} with arguments: {item.arguments}")
        else:
            print(f"{item}")

# tenant_id = os.environ["AZURE_TENANT_ID"]

async def main() -> None:
    async with (
        # AzureDeveloperCliCredential(tenant_id=tenant_id) as creds,
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):
        # 1. Retrieve the agent definition based on the `agent_id`
        # Replace the "your-agent-id" with the actual agent ID
        # you want to use.
        agent_definition = await client.agents.get_agent(
            agent_id= os.environ["AZURE_AI_AGENT_ID"],
            # endpoint=os.environ["AZURE_AI_AGENT_ENDPOINT"]
        )

        # 2. Create a Semantic Kernel agent for the Azure AI agent
        agent = AzureAIAgent(
            client=client,
            definition=agent_definition,
        )

        # 3. Create a thread for the agent
        # If no thread is provided, a new thread will be
        # created and returned with the initial response
        thread: AzureAIAgentThread = None

        try:
            while True:
                user_input = get_user_input()
                if not user_input.strip():
                    print("No input provided. Exiting the conversation.")
                    break
                print(f"# User: '{user_input}'")
                # 4. Invoke the agent for the specified thread for response
                async for response in agent.invoke(
                    messages=user_input,
                    thread=thread,
                    on_intermediate_message=handle_intermediate_steps,
                ):
                    # Print the agent's response
                    print(f"{response}", end="", flush=True)
                    # Update the thread for subsequent messages
                    thread = response.thread
                    # If the response is a final message, print it
                
        # Handle keyboard interrupt to gracefully exit the conversation            
        except KeyboardInterrupt:
            print("\nConversation ended by user.")
                        
        finally:
            # 5. Cleanup: Delete the thread and agent
            await thread.delete() if thread else None
            # Do not clean up the agent so it can be used again

if __name__ == "__main__":
    asyncio.run(main())