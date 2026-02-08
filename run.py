# import uvicorn
# from app.main import app

# if __name__ == "__main__":
#     print("Starting AI Query Router...")
#     print("Visit http://localhost:8000/docs for API documentation")
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


import uvicorn
print("Step 1: Starting imports...")

try:
    from app.main import app
    print("Step 2: Successfully imported app")
except Exception as e:
    print(f"Error importing app: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

if __name__ == "__main__":
    print("Step 3: Starting AI Query Router...")
    print("Visit http://localhost:8000/docs for API documentation")
    print("Step 4: About to start uvicorn...")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)