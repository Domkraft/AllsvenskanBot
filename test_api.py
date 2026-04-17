import requests
import json

def test_rapid_api():
    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-standing-all"
    querystring = {"leagueid": "113"} # Allsvenskan

    headers = {
        "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
        "x-rapidapi-key": "170b780b7bmshecdec44a331227cp1015d9jsn69b356a1e214"
    }

    try:
        print("Anropar RapidAPI: Free API Live Football Data...")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code != 200:
            print(f"Fel statuskod: {response.status_code}")
            print(f"Svar: {response.text}")
            return

        data = response.json()
        
        # Vi skriver ut hela JSON-strukturen (formaterad) så vi kan inspektera den
        print("\n--- RÅDATA FRÅN API ---")
        print(json.dumps(data, indent=2))
        print("-----------------------\n")

        # Försök att extrahera tabellen baserat på vanlig struktur
        # Vi letar efter var lagen ligger (t.ex. data['response']['standings'])
        res = data.get('response', {})
        standings = res.get('standings', [])

        if not standings:
            # Ibland ligger det direkt under 'data' eller 'content'
            print("Kunde inte hitta 'standings' i 'response'. Letar i hela objektet...")
            # Här får vi titta i loggen efter körning för att se var den gömmer sig
        else:
            print(f"Hittade {len(standings)} rader i tabellen:")
            for team in standings:
                # Vi gissar inte fältnamnen, vi skriver ut vad som finns i första laget
                print(f"Lag-objekt exempel: {team}")
                break 

    except Exception as e:
        print(f"Ett tekniskt fel uppstod: {e}")

if __name__ == "__main__":
    test_rapid_api()
