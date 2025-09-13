# 
        
        
# file: perchance_generate_and_download.py
# pip install cloudscraper
import cloudscraper
import time
import sys
import random
from http.cookies import SimpleCookie

# ====== CONFIG ======
API_VERIFY_USER = "https://image-generation.perchance.org/api/verifyUser"
API_GET_ADACCESS = "https://perchance.org/api/getAccessCodeForAdPoweredStuff"
API_GENERATE = "https://image-generation.perchance.org/api/generate"
API_DOWNLOAD = "https://image-generation.perchance.org/api/downloadTemporaryImage"  # use ?imageId=...
REFERER = "https://image-generation.perchance.org/embed"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

# Paste cookie header string dari browser di sini
USER_COOKIE_STRING = "usprivacy=1N--; _cc_id=489bf955cb9e1e0a057318a707efae4d; __qca=P1-2447d004-4f45-498e-9717-c1e937b61dda; _ga_C4V4S6SC92=GS2.1.s1750238330$o3$g0$t1750238330$j60$l0$h0; _gid=GA1.2.910433850.1757696389; panoramaId_expiry=1758363476969; panoramaId=58110b6cb0ba5ac558257f6286aa16d539385c037288f0fe9c0e2d06affeff0e; panoramaIdType=panoIndiv; cf_clearance=MYaD1PR.TcAzuiOEYQ3NvA12JXxS3G0YTWitnq.19L8-1757783509-1.2.1.1-jbMgIim3uS.4L35.yJ2fPXxi1nx8s1FYiT9Ik0hJOVIekZvaPX9DtFQMlCzD4BjE7WRD1vKoTxD5IQLkrTfRnDtCZkK.PNASKoSof2wU2bagwEsrPc9aDVKEj2Lsr0SXw7TeihVbL5LSHsW1mR4KNewkHLHX9vkp68SsO9TdiYv4MoiH7VGm1T083.Vyy3kwnjhxDSRQwmbQUXidVm_zUFM1EXSSfjL1PiJ3vaTYu_M; _ga_YJWJRNESS5=GS2.1.s1757783513$o30$g1$t1757783624$j55$l0$h0; _ga=GA1.2.1673193458.1753015665; _gat_gtag_UA_36798824_24=1; cto_bundle=RrzweF8wM2hJQ01qVCUyRjFrbHdtZVRiRTJpYWI5dWJmOFRBSFRIUHh0UiUyRmt3c1NRZ3h0QXB5TUk4bEU3VkFJZUMyTXRZR0ZhMEFTZk5aMzNpRTFRdjV2V2hFV0kzenI0SkZGNEFTRUd2dFNXM1FOUUI0eURHamVqWFBSdUYzNWJwcW5jUmZobG4xejE3ZTVvRjN6NXRpJTJCZ1JCRlNCdWRTY21qY2xJRFpXbmdkTXVVbzAlM0Q"
# ====== helper: parse cookie header into dict ======
def parse_cookie_header(cookie_header: str):
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    cookies = {}
    for k, morsel in cookie.items():
        cookies[k] = morsel.value
    return cookies

# ====== helper: refresh keys (auto retry sampai dapat) ======
def refresh_user_key(scraper, max_attempts=10, delay=3):
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        params = {"thread": "0", "__cacheBust": str(random.random())}
        try:
            r = scraper.get(API_VERIFY_USER, params=params, timeout=15)
            data = r.json()
        except Exception as e:
            print(f"[-] refresh_user_key error (attempt {attempt}):", e)
            time.sleep(delay)
            continue

        if "userKey" in data:
            print(f"[+] Got userKey ({data.get('status')}):", data["userKey"])
            return data["userKey"]

        print(f"[-] Failed refresh userKey (attempt {attempt}):", data)
        time.sleep(delay)

    print("[-] Exhausted attempts to get userKey")
    return None

def refresh_ad_access_code(scraper, max_attempts=10, delay=3):
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            params = {"__cacheBust": str(random.random())}
            r = scraper.get(API_GET_ADACCESS, params=params, timeout=15)
            txt = r.text.strip()
        except Exception as e:
            print(f"[-] refresh_ad_access_code error (attempt {attempt}):", e)
            time.sleep(delay)
            continue

        if txt and len(txt) > 30:
            print("[+] Refreshed adAccessCode:", txt)
            return txt

        print(f"[-] Invalid adAccessCode (attempt {attempt}):", txt)
        time.sleep(delay)

    print("[-] Exhausted attempts to get adAccessCode")
    return None

# ====== helper: ensure session valid (loop sampai dapat) ======
def ensure_valid_session(scraper):
    while True:
        userKey = refresh_user_key(scraper)
        adAccessCode = refresh_ad_access_code(scraper)
        if userKey and adAccessCode:
            return userKey, adAccessCode
        print("[-] Retry ensure_valid_session, waiting 5s...")
        time.sleep(5)
        


# ====== main ======
def main():
    # create cloudscraper session (handles CF js-challenges)
    scraper = cloudscraper.create_scraper(
        browser={"custom": USER_AGENT}
    )

    # set headers similar to browser
    scraper.headers.update({
    "User-Agent": USER_AGENT,
    "Referer": REFERER,
    "Origin": "https://image-generation.perchance.org",
    "Accept": "*/*",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    "sec-ch-ua": '"Chromium";v="140", "Not=A? Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-mobile": "?1",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
})

    # load cookies from provided cookie header (if any)
    if USER_COOKIE_STRING and USER_COOKIE_STRING.strip():
        ck = parse_cookie_header(USER_COOKIE_STRING)
        for name, val in ck.items():
            scraper.cookies.set(name, val, domain=".perchance.org")
        print("[*] Loaded cookies:", ", ".join(ck.keys()))
    else:
        print("[!] No cookie string provided. The request may be rejected.")

    # refresh keys setiap kali jalan (auto-loop sampai berhasil)
    userKey, adAccessCode = ensure_valid_session(scraper)

    # prompt dari user
    user = input("masukan prompt : ")
    userNeg = input("masukan Negatif Prompt (opsional): ")
    # ========== TRY GENERATE WITH RETRY ==========
    max_retries = 2
    for attempt in range(1, max_retries + 1):
        params = {
            "prompt": user,
            "seed": -1,
            "resolution": "768x768",
            "guidanceScale": 7,
            "negativePrompt": userNeg,
            "channel": "ai-text-to-image-generator",
            "subChannel": "public",
            "userKey": userKey,
            "adAccessCode": adAccessCode,
            "requestId": str(int(time.time() * 1000)),
            "__cacheBust": str(random.random()),
        }

        print(f"[*] Attempt {attempt}: POST generate")
        try:
            resp = scraper.post(API_GENERATE, params=params, timeout=120)
        except Exception as e:
            print("Request error:", e)
            sys.exit(1)

        print("[*] generate status:", resp.status_code)
        try:
            data = resp.json()
        except Exception:
            print("Non-JSON response preview:", resp.text[:1000])
            sys.exit(1)

        # cek invalid_key atau error
        if isinstance(data, dict) and data.get("status") in ("invalid_key", "error"):
            print("[-] Key invalid, refreshing session...")
            userKey, adAccessCode = ensure_valid_session(scraper)
            if not userKey:
                print("[-] Could not refresh keys. Abort.")
                sys.exit(1)
            continue  # retry generate
        else:
            break  # sukses

    print("[*] generate response:", data)

    # ========== DOWNLOAD IMAGE ==========
    image_id = None
    ext = "jpg"
    if isinstance(data, dict):
        image_id = data.get("imageId") or data.get("id") or data.get("image_id") or data.get("temporaryId")
        if data.get("fileExtension"):
            ext = data.get("fileExtension")
        if not image_id and data.get("url"):
            image_url_direct = data.get("url")
            print("[*] Direct URL provided by API:", image_url_direct)
            dl = scraper.get(image_url_direct, stream=True, timeout=120)
            if dl.status_code == 200:
                fname = "result_direct." + (image_url_direct.split(".")[-1].split("?")[0] or "jpg")
                with open(fname, "wb") as f:
                    f.write(dl.content)
                print("[+] Saved", fname)
                return
            else:
                print("[-] Direct download failed:", dl.status_code, dl.text[:400])
    else:
        print("Unexpected generate response format:", type(data))
        sys.exit(1)

    if not image_id:
        print("[-] Could not find imageId in generate response. Response keys:", list(data.keys()))
        sys.exit(1)

    download_url = f"{API_DOWNLOAD}?imageId={image_id}"
    print("[*] Attempting download via downloadTemporaryImage endpoint:", download_url)

    dl_headers = {
        "User-Agent": USER_AGENT,
        "Referer": REFERER,
        "Origin": "https://image-generation.perchance.org",
        "Accept": "*/*",
    }

    dl = scraper.get(download_url, headers=dl_headers, stream=True, timeout=120)
    print("[*] download status:", dl.status_code)

    if dl.status_code == 200 and dl.headers.get("content-type", "").startswith("image"):
        ct = dl.headers.get("content-type", "")
        if "/" in ct:
            ext = ct.split("/")[1].split(";")[0] or ext
        fname = f"result.{ext}"
        with open(fname, "wb") as f:
            for chunk in dl.iter_content(8192):
                f.write(chunk)
        print("[+] Saved image to", fname)
    else:
        print("[-] Download failed or not an image. Status:", dl.status_code)
        print("Response headers:", dl.headers)
        preview = dl.text if hasattr(dl, "text") and dl.text and len(dl.text) < 2000 else dl.content[:1000]
        try:
            print("Preview:", preview)
        except Exception:
            print("Preview binary (first 200 bytes):", dl.content[:200])



def generate_perchance_image(scraper, prompt: str, negative: str = ""):
    # refresh keys
    userKey, adAccessCode = ensure_valid_session(scraper)

    params = {
        "prompt": prompt,
        "seed": -1,
        "resolution": "768x768",
        "guidanceScale": 7,
        "negativePrompt": negative,
        "channel": "ai-text-to-image-generator",
        "subChannel": "public",
        "userKey": userKey,
        "adAccessCode": adAccessCode,
        "requestId": str(int(time.time() * 1000)),
        "__cacheBust": str(random.random()),
    }

    resp = scraper.post(API_GENERATE, params=params, timeout=120)
    data = resp.json()

    image_id = data.get("imageId") or data.get("temporaryId")
    if not image_id:
        return None, f"❌ Error: {data}"

    download_url = f"{API_DOWNLOAD}?imageId={image_id}"
    dl = scraper.get(download_url, stream=True, timeout=120)

    if dl.status_code == 200 and dl.headers.get("content-type", "").startswith("image"):
        fname = f"result.jpg"
        with open(fname, "wb") as f:
            for chunk in dl.iter_content(8192):
                f.write(chunk)
        return fname, None
    else:
        return None, f"❌ Gagal download: {dl.status_code}"
        



if __name__ == "__main__":
    main()
