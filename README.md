# WaterGuard

WaterGuard is a Streamlit prototype for recording water meter readings, monitoring
usage, and configuring alerts.

## Run locally

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy a college-project demo

1. Create a GitHub repository and upload the contents of this folder. Keep the
   local SQLite database, `.venv`, and any secrets out of the repository.
2. In Streamlit Community Cloud, create an app from that repository and select
   `app.py` as the entry point.
3. Before the first account is registered, add a private secret named
   `admin_setup_key` in the app's Streamlit Cloud settings. Use a long,
   randomly generated value and do not publish it.
4. Register the project administrator using that key. All other registrations
   receive the regular user role. The key is only accepted while no admin
   account exists.

The app currently uses a local SQLite database and a shared project workspace.
Streamlit Community Cloud does not provide durable storage for local files, and
accounts share the same readings. Use only demo data on a public deployment;
connect a managed database and add account-level data access controls before
using real personal or operational data.
