# fixed_groq_agent.py
"""
Fixed version that prevents multiple tool calls
"""
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
import uuid
import os
import os

api_key_name = "GROQ_API"

api_key = os.environ.get(api_key_name)
# Global counter to track actual tool calls
TOOL_CALL_COUNTER = 0

@tool
def add_numbers(a: int, b: int) -> str:
    """Add two numbers together.
    
    Args:
        a: First number to add
        b: Second number to add
    
    Returns:
        The sum of the two numbers
    """
    global TOOL_CALL_COUNTER
    TOOL_CALL_COUNTER += 1
    
    unique_id = str(uuid.uuid4())[:8]
    result = a + b
    
    print(f"🔢 ADD TOOL: {a} + {b} = {result} (ID: {unique_id})")
    return f"The sum is {result}"

@tool
def multiply_numbers(a: int, b: int) -> str:
    """Multiply two numbers together.
    
    Args:
        a: First number to multiply
        b: Second number to multiply
    
    Returns:
        The product of the two numbers
    """
    global TOOL_CALL_COUNTER
    TOOL_CALL_COUNTER += 1
    
    unique_id = str(uuid.uuid4())[:8]
    result = a * b
    
    print(f"✖️ MULTIPLY TOOL: {a} × {b} = {result} (ID: {unique_id})")
    return f"The product is {result}"

class FixedGroqAgent:
    def __init__(self, api_key: str):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=api_key,
            temperature=0,
        )
        
        self.tools = [
            add_numbers,
            multiply_numbers
        ]
        
        # Improved prompt that prevents multiple calls
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful math assistant. 

IMPORTANT INSTRUCTIONS:
1. Use add_numbers for addition problems
2. Use multiply_numbers for multiplication problems  
3. Call each tool ONLY ONCE per question
4. After getting the tool result, provide a clear final answer
5. Do NOT call the same tool multiple times

When you get a math question:
1. Identify if it's addition or multiplication
2. Call the appropriate tool once
3. Give the final answer based on the tool result"""),
            
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=2,  # Reduced to prevent loops
            handle_parsing_errors=True,
            early_stopping_method="generate"  # Stop after generating response
        )
    
    def query(self, user_input: str) -> str:
        try:
            result = self.agent_executor.invoke({
                "input": user_input,
                "chat_history": []
            })
            return result["output"]
        except Exception as e:
            return f"❌ Error: {str(e)}"

def test_fixed_agent():
    global TOOL_CALL_COUNTER
    TOOL_CALL_COUNTER = 0
    
 
    agent = FixedGroqAgent(api_key)
    
    test_cases = [
        "What is 15 + 27?",
        "Calculate 8 times 6", 
        "Add 100 and 200",
        "What is 12 × 5?"
    ]
    
    print("🎯 FIXED GROQ AGENT TEST")
    print("=" * 50)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n🔍 TEST {i}: {query}")
        print("-" * 30)
        
        calls_before = TOOL_CALL_COUNTER
        response = agent.query(query)
        calls_after = TOOL_CALL_COUNTER
        
        calls_made = calls_after - calls_before
        
        print(f"📤 RESPONSE: {response}")
        print(f"🔧 Tool calls made: {calls_made}")
        
        if calls_made == 1:
            print("✅ Perfect! Called tool exactly once")
        elif calls_made > 1:
            print(f"⚠️ Called tool {calls_made} times (should be 1)")
        else:
            print("❌ No tool was called")
        
        print("-" * 30)
    
    print(f"\n🎯 FINAL SUMMARY:")
    print(f"📊 Total tool calls: {TOOL_CALL_COUNTER}")
    print(f"📝 Expected calls: {len(test_cases)}")
    
    if TOOL_CALL_COUNTER == len(test_cases):
        print("✅ PERFECT! Each question called exactly one tool")
    else:
        print(f"⚠️ Made {TOOL_CALL_COUNTER} calls, expected {len(test_cases)}")

if __name__ == "__main__":
    test_fixed_agent()