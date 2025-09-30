# chord.py
import cloudscraper
from bs4 import BeautifulSoup
import time

scraper = cloudscraper.create_scraper()
base = "https://www.chordtela.com/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36"
}

# Daftar chord dasar
CHORDS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def transpose_chord(chord: str, step: int) -> str:
    """Transpose satu chord (misal C -> D)."""
    root, suffix = chord[0], chord[1:]
    if len(chord) > 1 and chord[1] in ["#", "b"]:
        root, suffix = chord[:2], chord[2:]

    if root not in CHORDS:
        return chord  

    idx = (CHORDS.index(root) + step) % len(CHORDS)
    return CHORDS[idx] + suffix

def transpose_text(text: str, step: int) -> str:
    """Transpose semua chord dalam teks."""
    result = []
    for line in text.splitlines():
        parts = line.split()
        new_line = []
        for word in parts:
            # Deteksi chord sederhana
            if any(word.startswith(c) for c in CHORDS):
                new_line.append(transpose_chord(word, step))
            else:
                new_line.append(word)
        result.append(" ".join(new_line))
    return "\n".join(result)

def getChord(keyword: str, retries=3, delay=2):
    """
    Ambil chord dari chordtela menggunakan cloudscraper dengan retry otomatis.

    :param keyword: slug lagu, misal 'rossa-jangan-hilangkan-dia-ost-i-love-you'
    :param retries: jumlah percobaan sebelum gagal
    :param delay: delay dalam detik antar retry
    :return: teks chord, None jika tidak ditemukan, atau error string
    """
    url = f"{base}{keyword}.html"

    for attempt in range(1, retries + 1):
        try:
            res = scraper.get(url, headers=headers, timeout=10)

            if res.status_code != 200:
                return None  # halaman tidak ditemukan

            parsing = BeautifulSoup(res.text, "html.parser")

            # Ambil chord dari <pre>
            hasil = parsing.find("pre")
            if hasil and hasil.text.strip():
                return hasil.text

            # Fallback: ambil dari <div>
            fallback = parsing.find("div")
            if fallback and fallback.text.strip():
                return fallback.text

            return None  # tidak ada chord sama sekali

        except Exception as e:
            # Retry otomatis
            if attempt < retries:
                time.sleep(delay)
            else:
                return f"❌ Error: {e}"
