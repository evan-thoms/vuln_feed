from agent import run_agent

if __name__ == "__main__":
    while True:
        prompt = input("You: ")
        if prompt.lower() in {"exit", "quit"}:
            break
        response = run_agent(prompt)
        print("Agent:", response)