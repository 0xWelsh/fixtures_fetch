import datetime as dt
import os
from typing import Dict, Tuple
from zoneinfo import ZoneInfo

import gspread
import requests
from google.oauth2.service_account import Credentials


BASE_URL = "https://v3.football.api-sports.io"
LAST_MATCH_LOOKBACK = 5
REQUIRED_COMPLETED_MATCHES = 5
COMPLETED_STATUSES = {"FT", "AET", "PEN"}
SHEET_NAME = "Today's Matches"
CLIENT_TIMEZONE = ZoneInfo("America/New_York")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SESSION = requests.Session()


def api_get(path: str, params: dict | None = None) -> list:
    response = SESSION.get(
        f"{BASE_URL}{path}",
        headers={"x-apisports-key": os.environ["FOOTBALL_API_KEY"]},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("response", [])


def get_worksheet():
    credentials = Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(os.environ["SPREADSHEET_ID"])

    try:
        return spreadsheet.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=SHEET_NAME, rows=2000, cols=20)


def summarize_last_5(team_id: int) -> Tuple[int, int, float, float]:
    try:
        fixtures = api_get("/fixtures", {"team": team_id, "last": LAST_MATCH_LOOKBACK})
    except requests.RequestException:
        return 0, 0, 0.0, 0.0

    gf_total = 0
    ga_total = 0
    completed_count = 0

    for fixture in fixtures:
        status = fixture["fixture"]["status"]["short"]
        home_goals = fixture["goals"]["home"]
        away_goals = fixture["goals"]["away"]

        if status not in COMPLETED_STATUSES or home_goals is None or away_goals is None:
            continue

        is_home = fixture["teams"]["home"]["id"] == team_id
        gf_total += home_goals if is_home else away_goals
        ga_total += away_goals if is_home else home_goals
        completed_count += 1

    divisor = REQUIRED_COMPLETED_MATCHES if completed_count else 1
    return (
        gf_total,
        ga_total,
        round(gf_total / divisor, 2) if completed_count else 0.0,
        round(ga_total / divisor, 2) if completed_count else 0.0,
    )


def build_rows() -> list[list]:
    now = dt.datetime.now(CLIENT_TIMEZONE)
    today = now.date().isoformat()
    fixtures = api_get("/fixtures", {"date": today})
    updated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    team_cache: Dict[int, Tuple[int, int, float, float]] = {}

    print(f"Using client timezone date: {today}")
    print(f"Fixtures fetched: {len(fixtures)}")

    rows = [[
        "Date",
        "Country",
        "League",
        "Home Team",
        "Away Team",
        "Home Team Last 5 Goals Scored",
        "Home Team Last 5 Goals Conceded",
        "Away Team Last 5 Goals Scored",
        "Away Team Last 5 Goals Conceded",
        "Updated",
        "Home Team Last 5 Avg Goals Scored",
        "Home Team Last 5 Avg Goals Conceded",
        "Away Team Last 5 Avg Goals Scored",
        "Away Team Last 5 Avg Goals Conceded",
    ]]

    for fixture in fixtures:
        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]

        if home_id not in team_cache:
            team_cache[home_id] = summarize_last_5(home_id)
        if away_id not in team_cache:
            team_cache[away_id] = summarize_last_5(away_id)

        home_gf, home_ga, home_gf_avg, home_ga_avg = team_cache[home_id]
        away_gf, away_ga, away_gf_avg, away_ga_avg = team_cache[away_id]

        rows.append([
            fixture["fixture"]["date"],
            fixture["league"]["country"],
            fixture["league"]["name"],
            fixture["teams"]["home"]["name"],
            fixture["teams"]["away"]["name"],
            home_gf,
            home_ga,
            away_gf,
            away_ga,
            updated_at,
            home_gf_avg,
            home_ga_avg,
            away_gf_avg,
            away_ga_avg,
        ])

    return rows


def main():
    worksheet = get_worksheet()
    rows = build_rows()
    print(f"Target worksheet: {worksheet.title}")
    print(f"Rows prepared for write: {len(rows)}")

    if len(rows) == 1:
        print("No fixture rows returned. Writing header row only.")

    end_column = column_label(len(rows[0]))
    worksheet.clear()
    worksheet.update(
        range_name=f"A1:{end_column}{len(rows)}",
        values=rows,
    )
    print(f"Sheet update complete: A1:{end_column}{len(rows)}")


def column_label(column_number: int) -> str:
    label = ""

    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        label = chr(65 + remainder) + label

    return label


if __name__ == "__main__":
    main()
