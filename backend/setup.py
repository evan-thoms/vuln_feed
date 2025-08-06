from db import init_db
import argostranslate.package
import argostranslate.translate

def setup_argos():
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    
    zh_en_package = next(
        filter(lambda x: x.from_code == "zh" and x.to_code == "en", available_packages)
    )
    argostranslate.package.install_from_path(zh_en_package.download())
    
    ru_en_package = next(
        filter(lambda x: x.from_code == "ru" and x.to_code == "en", available_packages)
    )
    argostranslate.package.install_from_path(ru_en_package.download())

def run_setup():
    print("🛠️ Initializing database...")
    init_db()
    print("🌐 Setting up translation packages...")
    setup_argos()
    print("✅ Setup complete.")

if __name__ == "__main__":
    run_setup()
