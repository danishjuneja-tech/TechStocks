import time
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockmarket.settings")

django.setup()

from django.core.management import call_command


print("🚀 Stock price worker started!")

while True:
    try:
        call_command("update_stocks")
        print("📈 Stock prices updated!")

    except Exception as e:
        print("❌ Error:", e)

    time.sleep(2)