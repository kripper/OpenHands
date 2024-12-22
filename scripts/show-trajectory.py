import requests
import json

json_data = {
    'feedback_id': '4dbb93310608f43026c9843cf184ce93240b31565f6eb913fbcda369d43ec639',
}

response = requests.post(
    'https://show-od-trajectory-3u9bw9tx.uc.gateway.dev/show-od-trajectory',
    json=json_data,
)

with open('response.json', 'w') as f:
    json.dump(response.json(), f)

