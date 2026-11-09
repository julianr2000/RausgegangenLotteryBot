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
    """Optimiert für den vorinstallierten Chromium auf dem Raspberry Pi/Proxmox."""
    options = ChromeOptions()
    options.binary_location = "/usr/bin/chromium-browser"
    
    if headless:
        options.add_argument("--headless=new")
    
    # --- NEU: Bot-Detection Umgehung (Tarnkappe) ---
    # 1. Täuscht einen normalen Windows-PC vor (entfernt das verräterische "Headless")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 2. Versteckt die Tatsache, dass der Browser von einem Skript (Selenium) gesteuert wird
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    # -----------------------------------------------
    
    # Proxmox / LXC Spezifische Optimierungen
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--blink-settings=imagesEnabled=false")

    service = ChromeService(executable_path="/usr/bin/chromedriver")
    
    # 3. Führt ein Skript direkt beim Start aus, um navigator.webdriver komplett zu löschen
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
              get: () => undefined
            })
        '''
    })
    
    return driverSie gaukelt Bunny.net vor, dass hier ein ganz normaler Windows-Nutzer an einem echten Monitor sitzt:

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
        
        # Nutzt jetzt die robusten data-testid Attribute der neuen Website
        email_field = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@data-testid="login-username-input"]')))
        password_field = driver.find_element(By.XPATH, '//*[@data-testid="login-password-input"]')

        email_field.send_keys(email)
        password_field.send_keys(password)

        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@data-testid="login-submit-button"]')))
        login_button.click()
        
        WebDriverWait(driver, 30).until(EC.url_to_be("https://rausgegangen.de/en/"))
        print(f"[{email}] Login erfolgreich.")
        return True
    except Exception as e:
        print(f"[{email}] Login fehlgeschlagen: {e}")
        driver.save_screenshot(f"error_login_{email}.png")
        return False

def handle_raffles(driver, email):
    page = 1 
    while True:
        url = f"https://rausgegangen.de/en/stuttgart/category/lottery/?page={page}"
        driver.get(url)
        try:
            # Wartet, bis die Event-Namen (das neue Layout) geladen sind
            WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.XPATH, '//*[@data-testid="event-tile-name"]')))
        except TimeoutException:
            print(f"[{email}] Keine weiteren Events auf Seite {page} gefunden (Timeout).")
            break

        # Sucht gezielt nur die Links, die auch das Lottery-Badge haben
        lottery_links = driver.find_elements(By.XPATH, '//*[@data-testid="badge-lottery"]/ancestor::a')
        event_urls = [link.get_attribute('href') for link in lottery_links]
        
        if not event_urls:
            print(f"[{email}] Keine Verlosungen auf Seite {page} gefunden.")
            break

        for event_url in event_urls:
            if not event_url: continue
            try:
                driver.get(event_url)
                clear_overlays(driver, email)

                # Bereits teilgenommen? (Prüft auf englisch, deutsch und das Emoji)
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(@aria-label, 'You’re in') or contains(@aria-label, 'Du bist dabei') or contains(., '🤞')]"))
                    )
                    print(f"     - [{email}] Bereits teilgenommen: {event_url}")
                    continue
                except TimeoutException:
                    pass

                # Teilnahme-Prozess (neuer ID-Selektor für den WIN TICKETS Button)
                win_tickets_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, 'participate_button'))
                )
                driver.execute_script("arguments[0].click();", win_tickets_button)

                # Modal Bestätigung (neuer XPATH für den JETZT TEILNEHMEN Button)
                count_me_in = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(@class, "da-btn-primary")]'))
                )
                count_me_in.click()
                print(f"     - [{email}] Erfolg bei: {event_url}")

            except Exception as e:
                print(f"     - [{email}] Fehler bei {event_url}. Details: {e}")
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
    # Nacheinander abarbeiten, um CPU/RAM zu schonen
    for account in accounts:
        process_account(account)

if __name__ == "__main__":
    main()