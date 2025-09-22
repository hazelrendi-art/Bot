import cloudscraper
from bs4 import BeautifulSoup

class JavtifulScraper:
    def __init__(self): #proxy_host="127.0.0.1", proxy_port=9050):
        """
        Inisialisasi scraper dengan konfigurasi Tor SOCKS5 proxy.
        Default: 127.0.0.1:9050
        """
        self.scraper = cloudscraper.create_scraper()
        #self.proxies = {
            #"http": f"socks5h://{proxy_host}:{proxy_port}",
            #"https": f"socks5h://{proxy_host}:{proxy_port}"
        #}

    def get_video_url(self, url: str) -> str:
        """
        Ambil URL video dari link javtiful.com
        """
        # GET halaman video
        html = self.scraper.get(url).text
        soup = BeautifulSoup(html, "html.parser")

        # Ambil CSRF token dari element dengan id "token_full"
        token_el = soup.select_one("#token_full")
        if not token_el:
            raise ValueError("❌ CSRF token tidak ditemukan di halaman.")
        csrf_token = token_el["data-csrf-token"]

        # Ambil video_id dari URL
        try:
            video_id = url.split("/")[4]
        except IndexError:
            raise ValueError("❌ URL tidak valid, gagal ambil video_id.")

        # Kirim POST request ke endpoint get_cdn
        data = {
            "video_id": video_id,
            "pid_c": "",
            "token": csrf_token
        }
        res = self.scraper.post(
            "https://javtiful.com/ajax/get_cdn",
            data=data,
            #proxies=self.proxies
        ).json()

        # Validasi hasil
        if res.get("playlists_active") == 1:
            return res.get("playlists")
        else:
            raise ValueError("❌ Tidak ada playlist aktif ditemukan.")
