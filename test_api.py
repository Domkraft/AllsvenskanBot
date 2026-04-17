import requests
import json

def test_connection():
    url = "https://v3.football.api-sports.io/standings"
    api_key = "650b6ee51b58784aa2427a9242d7aed9"
    
    # Vi testar både 2025 och 2026 för att se vad som finns tillgängligt
    for season in ["2025", "2026"]:
        print(f"\n--- Testar säsong {season} ---")
        params = {
            'league': '113',
            'season': season
        }
        headers = {'x-apisports-key': api_key}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            data = response.json()
            
            if data.get('response'):
                standings = data['response'][0]['league']['standings'][0]
                print(f"Framgång! Hittade {len(standings)} lag.")
                for team in standings:
                    name = team['team']['name']
                    p = team['points']
                    m = team['all']['played']
                    ppg = p/m if m > 0 else 0.0
                    print(f"{team['rank']}. {name}: {p}p på {m} matcher (PPG: {ppg:.2f})")
            else:
                print(f"Ingen data för {season}. API-svar: {data}")
        except Exception as e:
            print(f"Fel vid test av {season}: {e}")

if __name__ == "__main__":
    test_connection()
