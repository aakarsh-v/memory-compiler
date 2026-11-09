import os
import pytest

# Ensure tests always run with deterministic MockEmbeddingProvider
# as per Memory Compiler spec (zero heavy model downloads in CI/tests)
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["EMBEDDING_MODEL_ID"] = "mock-clip-vit-b32"
os.environ["APP_ENV"] = "development"
os.environ["ENABLE_ASYNC_WORKER"] = "False"

# Reload settings to reflect mock provider for test suite
from app.core import config
config.settings = config.Settings(_env_file=None)

