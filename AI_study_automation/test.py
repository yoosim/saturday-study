# test_discord.py
import requests
url = "https://discordapp.com/api/webhooks/1428011625541275782/JTSdA0ugVqxRj_1VrqIKdq58C7qn3CuVll-bWm7yHp8fryqzmvmgkbrEUiaTxvZpXrwt"
r = requests.post(url, json={"content":"✅ 웹훅 테스트: Python OK"})
r.raise_for_status()
print("ok")
