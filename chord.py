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

def getChord(keyword: str):
    """Ambil chord dari chordtela."""
    try:
        url = f"{base}{keyword}"
        res = scraper.get(url, headers=headers)

        if res.status_code == 200:
            parsing = BeautifulSoup(res.text, "html.parser")
            hasil = parsing.find("pre")
            if hasil:
                return hasil.text
            return None
        return None
    except Exception as e:
        return f"❌ Error: {e}"
