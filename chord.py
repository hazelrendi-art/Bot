import cloudscraper
from bs4 import BeautifulSoup 

scraper = cloudscraper.create_scraper()
base = "https://www.chordtela.com/"
userInput = input("Masukkan keyword (contoh: wali-bocah-ngapa-yang-enak): ")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36"
}

def getChord(keyword):
    try:
        # langsung gabung ke base (jangan pakai +)
        q = f"{base}{keyword}.html"
        res = scraper.get(q, headers=headers)

        if res.status_code == 200:
            parsing = BeautifulSoup(res.text, "html.parser")
            hasil = parsing.find("div", class_="post-body")
            
            if hasil:
                print(hasil.get_text("\n", strip=True))
                return hasil.get_text("\n", strip=True)
            else:
                print("❌ Tidak menemukan chord di halaman")
                return None
        else:
            print(f"⚠️ Error {res.status_code}")
            return None
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")
        return None

