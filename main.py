# Import the app instance from app.main
from app.main import app

# This is important for Render deployment
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

# You might need to add this if you run uvicorn from the root directory
# and want it to find the 'app' object correctly.
# However, usually uvicorn main:app works if main.py contains 'app'.
# If you encounter issues, you might need to adjust how uvicorn is called
# or ensure the Python path includes the 'app' directory.

# The rest of the code that was here (FastAPI creation, router includes)
# is now handled within app/main.py and can be removed from this file.

# Example of how you might run this with uvicorn from the root directory:
# uvicorn main:app --reload
