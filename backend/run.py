
import os
import sys
import uvicorn

# Ensure working directory is the backend folder
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

if __name__ == "__main__":
    print("=" * 60)
    print("  Starting server at http://localhost:8000")
    print("=" * 60)
    print()

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[BACKEND_DIR],
    )
