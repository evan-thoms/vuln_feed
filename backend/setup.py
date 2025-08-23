from db import init_db
# Translation handled by OpenAI

def setup_argos():
    # Translation handled by OpenAI - no setup needed
    pass

def run_setup():
    print("🛠️ Initializing database...")
    init_db()
    print("🌐 Setting up translation packages...")
    setup_argos()
    print("✅ Setup complete.")

if __name__ == "__main__":
    run_setup()
