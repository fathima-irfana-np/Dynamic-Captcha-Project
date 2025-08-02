from selenium import webdriver
import time

driver = webdriver.Firefox()


driver.get("http://127.0.0.1:8000/")

print("Opened CAPTCHA page.")


print("Please solve CAPTCHA manually in browser window...")
time.sleep(20)

current_url = driver.current_url
print("Current URL after solving:", current_url)

if "protected" in current_url:
    print("✅ CAPTCHA solved and redirected to protected page.")
else:
    print("❌ Not on protected page. Maybe CAPTCHA not solved yet?")

print(driver.page_source)

input("Press Enter to close browser...")
driver.quit()

