# chord.py
import cloudscraper
from bs4 import BeautifulSoup 

scraper = cloudscraper.create_scraper()
base = "https://www.chordtela.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36"
}

def getChord(keyword: str):
    """
    Ambil chord dari chordtela berdasarkan keyword (format: artis-judul-lagu)
    Contoh: wali-bocah-ngapa-yang-enak
    """
    try:
        url = f"{base}{keyword}.html"
        res = scraper.get(url, headers=headers)

        if res.status_code == 200:
            parsing = BeautifulSoup(res.text, "html.parser")
            hasil = parsing.find("div", class_="post-body")
            
            if hasil:
                return hasil.get_text("\n", strip=True)
            else:
                return None
        else:
            return None
    except Exception as e:
        return f"❌ Error: {e}"
