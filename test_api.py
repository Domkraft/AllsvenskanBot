import requests
import json

def test_standing_api():
    # Vi använder den endpoint som ger tabellen för ligan
    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-standing-all"
    querystring = {"leagueid": "113"} # Allsvenskan

    headers = {
        "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com",
        "x-rapidapi-key": "170b780b7bmshecdec44a331227cp1015d9jsn69b356a1e214"
    }

    try:
        print("Anropar RapidAPI för att hämta tabellen...")
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code != 200:
            print(f"Fel: Statuskod {response.status_code}")
            print(response.text)
            return

        data = response.json()
        
        # Vi skriver ut de första 2000 tecknen av svaret för att se strukturen
        print("\n--- JSON STRUKTUR (START) ---")
        print(json.dumps(data, indent=2)[:2000])
        print("--- SLUT PÅ UTDRAG ---\n")

        # Försök hitta tabellen i det här specifika API:ets struktur
        # Ofta: data -> response -> standings -> table
        if 'response' in data and 'standings' in data['response']:
            standings = data['response']['standings']
            print(f"Hittade {len(standings)} rader i tabellen.")
            
            # Visa första laget som exempel för att se fältnamn (points, played, etc)
            if len(standings) > 0:
                print(f"Exempel på lagdata: {standings[0]}")
        else:
            print("Kunde inte hitta 'standings' i 'response'. Kolla utdraget ovan.")

    except Exception as e:
        print(f"Ett fel uppstod: {e}")

if __name__ == "__main__":
    test_standing_api()
