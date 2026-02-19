import os
import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from dotenv import load_dotenv

# Pfad zum Ordner definieren, damit .env immer gefunden wird
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

def setup_driver(headless=True):
    """Optimiert für den vorinstallierten Chromium auf dem Raspberry Pi."""
    options = ChromeOptions()
    options.binary_location = "/usr/bin/chromium-browser"
    
    if headless:
        options.add_argument("--headless=new")
    
    # Raspberry Pi Spezifische Optimierungen
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--blink-settings=imagesEnabled=false") # Spart RAM auf dem Pi

    service = ChromeService(executable_path="/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)

def clear_overlays(driver, email):
    """Schließt Popups wie das Social-Onboarding oder Cookie-Banner."""
    selectors = [
        "button.social-onboarding-dismissal-on-click", 
        "#social_onboarding_cta",                       
        ".iubenda-cs-accept-btn.iubenda-cs-btn-primary"  
    ]
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                if el.is_displayed():
                    el.click()
                    print(f"[{email}] Overlay entfernt: {selector}")
                    time.sleep(1)
        except Exception:
            continue

def login(driver, email, password):
    driver.get("https://rausgegangen.de/en/login")
    try:
        clear_overlays(driver, email)
        wait = WebDriverWait(driver, 20)
        
        email_field = wait.until(EC.visibility_of_element_located((By.NAME, 'username')))
        password_field = driver.find_element(By.NAME, 'password')

        email_field.send_keys(email)
        password_field.send_keys(password)

        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Login")]')))
        login_button.click()
        
        WebDriverWait(driver, 30).until(EC.url_to_be("https://rausgegangen.de/en/"))
        print(f"[{email}] Login erfolgreich.")
        return True
    except Exception:
        print(f"[{email}] Login fehlgeschlagen.")
        return False

def handle_raffles(driver, email):
    page = 1 
    while True:
        url = f"https://rausgegangen.de/en/stuttgart/category/lottery/?page={page}"
        driver.get(url)
        try:
            WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.tile-medium')))
        except TimeoutException:
            break

        tiles = driver.find_elements(By.CSS_SELECTOR, 'div.tile-medium a.event-tile')
        event_urls = [tile.get_attribute('href') for tile in tiles]

        for event_url in event_urls:
            if not event_url: continue
            try:
                driver.get(event_url)
                clear_overlays(driver, email)

                # Bereits teilgenommen?
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'You’re in 🤞')]"))
                    )
                    continue
                except TimeoutException:
                    pass

                # Teilnahme-Prozess
                win_tickets_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button/span[contains(text(), 'WIN TICKETS')]"))
                )
                driver.execute_script("arguments[0].click();", win_tickets_button)

                count_me_in = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#lottery-participate-button'))
                )
                count_me_in.click()
                print(f"     - [{email}] Erfolg bei: {event_url}")

            except Exception:
                continue
        page += 1

def process_account(account):
    email = account.get("email")
    password = account.get("password")
    if not email or not password: return

    driver = setup_driver(headless=True)
    try:
        if login(driver, email, password):
            handle_raffles(driver, email)
    finally:
        driver.quit()

def main():
    accounts = [
        {"email": os.getenv("ACCOUNT_1_EMAIL"), "password": os.getenv("ACCOUNT_1_PASSWORD")},
        {"email": os.getenv("ACCOUNT_2_EMAIL"), "password": os.getenv("ACCOUNT_2_PASSWORD")},
    ]
    # Auf dem Pi nacheinander abarbeiten, um CPU/RAM zu schonen
    for account in accounts:
        process_account(account)

if __name__ == "__main__":
    main()
