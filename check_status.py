import sys
import requests

if len(sys.argv) < 3:
    print("Usage: python3 check_status.py <requestId> <accessToken>")
    sys.exit(1)

requestId = sys.argv[1]
token = sys.argv[2]

url = "https://datamanager.googleapis.com/v1/requestStatus:retrieve"
params = {"requestId": requestId}

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.get(url, headers=headers, params=params)

print(f"Status Code: {response.status_code}")
print(f"Response Body: \n{response.text}")
