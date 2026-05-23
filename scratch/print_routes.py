import os
import sys

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
import Auth.router as AuthRouter

print("AuthRouter file:", AuthRouter.__file__)
print("Registered Routes:")
for route in app.routes:
    print(f"Path: {route.path}, Name: {route.name}, Methods: {getattr(route, 'methods', None)}")
