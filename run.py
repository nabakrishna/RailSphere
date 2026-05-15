from dotenv import load_dotenv
import os

# Load .env from the project root before anything reads os.environ
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
