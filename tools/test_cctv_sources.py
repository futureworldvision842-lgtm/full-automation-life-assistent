import requests

def test_tfl():
    try:
        r = requests.get('https://api.tfl.gov.uk/Place/Type/JamCam', timeout=10)
        if r.status_code == 200:
            places = r.json()
            print(f"Total London JamCams available: {len(places)}")
            count = 0
            for p in places:
                props = {item.get('key'): item.get('value') for item in p.get('additionalProperties', [])}
                if props.get('available') == 'true' and props.get('imageUrl'):
                    img_url = props.get('imageUrl')
                    # verify image works
                    t_res = requests.head(img_url, timeout=4)
                    print(f"[{count+1}] {p.get('commonName')} -> {img_url} (HTTP {t_res.status_code})")
                    count += 1
                    if count >= 6:
                        break
    except Exception as e:
        print("TfL fetch error:", e)

if __name__ == "__main__":
    test_tfl()
