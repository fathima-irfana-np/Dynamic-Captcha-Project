

driver = webdriver.Firefox()


driver.get("http://127.0.0.1:8000/")

print("Opened CAPTCHA page.")


print("Please solve CAPTCHA manually in browser window...")
time.sleep(20)

current_url = driver.current_url
print("Current URL after solving:", current