import os

# Test settings take priority over any local .env file and must be set before
# the app reads its configuration.
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-only-jwt-secret-of-at-least-32-bytes"
os.environ["CRON_SECRET"] = "test-cron-secret"
