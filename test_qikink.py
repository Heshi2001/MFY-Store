import requests

url = "https://sandbox.qikink.com/api/token"  # <-- use the full token endpoint
data = {
    "ClientId": "732242721350738",      # note: "ClientId" with capital C
    "client_secret": "f0aa11834dd4d7b82131983db07e983a5504bcf1b7fec740b4752655343a5509"
}

try:
    r = requests.post(url, data=data, timeout=10)
    r.raise_for_status()  # will raise an exception for HTTP errors
    print("Access token response:", r.json())
except requests.exceptions.HTTPError as e:
    print("HTTP Error:", e, r.text)
except Exception as e:
    print("Error:", e)
