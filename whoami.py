import google.auth

creds, project = google.auth.default()
print("Detected project:", project)
print("Credentials type:", type(creds).__name__)
print("Service account email:",
      getattr(creds, "service_account_email", "(none)"))
print("Quota project:", getattr(creds, "quota_project_id", "(none)"))

