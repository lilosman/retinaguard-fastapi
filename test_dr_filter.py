import requests

r = requests.get('http://141.140.0.233/api/doctor/patients', timeout=10)
print('STATUS:', r.status_code)
if r.status_code == 200:
    data = r.json()
    print('Total patients:', len(data))
    for p in data[:8]:
        name = p.get('name')
        risk = p.get('risk')
        prob = p.get('probability')
        urgent = p.get('isUrgent')
        print(f"  Patient: {name} | Risk: {risk} | Prob: {prob}% | Urgent: {urgent}")
