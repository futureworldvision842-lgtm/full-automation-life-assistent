import requests

def test_austin():
    try:
        r = requests.get('https://data.austintexas.gov/resource/b4k4-sfkb.json?$limit=5', timeout=6)
        if r.status_code == 200:
            cams = r.json()
            print(f"Austin cameras available: {len(cams)}")
            for c in cams:
                url = c.get('screenshot_address')
                if url:
                    t = requests.head(url, timeout=3)
                    print(f"  Austin: {c.get('camera_id')} - {c.get('location_name')} -> {url} (HTTP {t.status_code})")
    except Exception as e:
        print("Austin error:", e)

def test_caltrans():
    try:
        # Caltrans District 4 (Bay Area) Bay Bridge
        url = 'https://cwwp2.dot.ca.gov/data/d4/cctv/image/i80atbaybridgewestbound/i80atbaybridgewestbound.jpg'
        t = requests.head(url, timeout=4)
        print(f"Caltrans Bay Bridge -> {url} (HTTP {t.status_code})")
    except Exception as e:
        print("Caltrans error:", e)

if __name__ == "__main__":
    test_austin()
    test_caltrans()
