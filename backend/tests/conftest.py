import os
os.environ["DATABASE_URL"] = "sqlite:///./test-sentinel.db"
os.environ["API_TOKEN"] = "test-only-token"
os.environ["SYNC_JOBS"] = "true"
