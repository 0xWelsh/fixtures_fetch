# Football Sheet Updater

This folder contains the GitHub Actions version of the football sheet updater.

## Required GitHub Secrets

- `FOOTBALL_API_KEY`: the API-Football key
- `SPREADSHEET_ID`: the Google Sheets file ID
- `GOOGLE_SERVICE_ACCOUNT_JSON`: the full service-account JSON key

## Google Setup

1. Create a Google Cloud service account.
2. Enable Google Sheets API and Google Drive API.
3. Download the JSON key.
4. Share the target Google Sheet with the service-account email as `Editor`.

## GitHub Actions Setup

1. Push this folder to a GitHub repo.
2. Add the three secrets above in `Settings -> Secrets and variables -> Actions`.
3. Run the workflow manually once from the `Actions` tab.
4. Leave the schedule enabled for automatic daily runs.

## Schedule

The workflow runs daily at `03:00 UTC`:

```yaml
cron: "0 3 * * *"
```

Change that in `.github/workflows/daily-update.yml` if the client wants a different time.
