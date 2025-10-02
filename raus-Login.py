import os
import time
import concurrent.futures
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

def setup_driver(headless=True):
    """Sets up the Firefox WebDriver.
    
    Args:
        headless (bool): If True, runs Firefox in headless mode. 
                         Set to False for debugging to see the browser window.
    """
    options = FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    service = FirefoxService(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)

def login(driver, email, password):
    """
    Navigates to the login page and logs in.
    Returns True for a successful login, False otherwise.
    """
    driver.get("https://rausgegangen.de/en/login")
    
    try:
        print(f"[{email}] Waiting for login page to be ready...")
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//button[@type="submit" and contains(text(), "Login")]'))
        )
        print(f"[{email}] Login page is ready.")

        # Handle cookie banner now that we know the page is loaded
        print(f"[{email}] Checking for cookie banner...")
        cookie_button = WebDriverWait(driver, 7).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".iubenda-cs-accept-btn.iubenda-cs-btn-primary"))
        )
        cookie_button.click()
        print(f"[{email}] Cookie banner accepted.")
    except TimeoutException:
        print(f"[{email}] Cookie acceptance button not found or not needed. Proceeding with login.")

    try:
        # Now that page is ready, find form elements
        wait = WebDriverWait(driver, 10)
        email_field = wait.until(
            EC.visibility_of_element_located((By.NAME, 'username'))
        )
        password_field = driver.find_element(By.NAME, 'password')

        email_field.clear()
        password_field.clear()
        email_field.send_keys(email)
        password_field.send_keys(password)

        login_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Login")]'))
        )
        login_button.click()
        
        print(f"[{email}] Login button clicked. Waiting for redirect to home page...")
        
        WebDriverWait(driver, 15).until(
            EC.url_to_be("https://rausgegangen.de/en/")
        )
        print(f"[{email}] Successfully logged in and redirected to the home page.")
        return True

    except TimeoutException:
        error_message = "Login failed. The page did not redirect to the home page as expected."
        try:
            error_div = driver.find_element(By.CSS_SELECTOR, 'div.text-danger')
            if error_div.is_displayed():
                error_message = f"Login failed. Reason: {error_div.text.strip()}"
        except NoSuchElementException:
            pass 
        
        print(f"[{email}] {error_message}")
        driver.save_screenshot(f"login_failed_{email}_{time.time()}.png")
        return False
    except Exception as e:
        print(f"[{email}] An unexpected error occurred during login: {e}")
        driver.save_screenshot(f"login_unexpected_error_{email}_{time.time()}.png")
        return False


def logout(driver, email):
    """Logs the current user out."""
    try:
        driver.get("https://rausgegangen.de/en/logout")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href="/en/login"]'))
        )
        print(f"[{email}] Successfully logged out.")
    except Exception as e:
        print(f"[{email}] An error occurred during logout: {e}")


def handle_raffles(driver, email):
    """Iterates through raffle pages and attempts to enter each one."""
    page = 1 
    while True:
        url = f"https://rausgegangen.de/en/stuttgart/category/lottery/?page={page}"
        print(f"[{email}] Navigating to lottery page: {url}")
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.tile-medium'))
            )
        except TimeoutException:
            print(f"[{email}] No more lotteries found on page {page}. Finished processing.")
            break

        tiles = driver.find_elements(By.CSS_SELECTOR, 'div.tile-medium a.event-tile')
        if not tiles:
            print(f"[{email}] No event links found on page {page}, although tiles were present. Stopping.")
            break
        
        event_urls = [tile.get_attribute('href') for tile in tiles]
        print(f"[{email}] Found {len(event_urls)} raffles on page {page}.")

        for event_url in event_urls:
            if not event_url: continue
            try:
                print(f"  -> [{email}] Navigating to {event_url}")
                driver.get(event_url)

                try:
                    WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'You’re in 🤞')]"))
                    )
                    print(f"     - [{email}] Already in this lottery. Skipping.")
                    continue
                except TimeoutException:
                    pass

                win_tickets_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button/span[contains(text(), 'WIN TICKETS')]"))
                )
                win_tickets_button.click()
                print(f"     - [{email}] Clicked 'WIN TICKETS'")

                count_me_in_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '#lottery-participate-button'))
                )
                count_me_in_button.click()
                print(f"     - [{email}] Clicked 'COUNT ME IN!'. Entry successful.")

                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'You’re in 🤞')]"))
                )

            except (TimeoutException, NoSuchElementException) as e:
                print(f"     - [{email}] Could not enter raffle at {event_url}. Error: {type(e).__name__}")
                driver.save_screenshot(f"raffle_error_{email}_{page}_{time.time()}.png")
            except Exception as e:
                print(f"     - [{email}] An unexpected error occurred at {event_url}: {e}")
        page += 1

def process_account(account):
    """
    Handles the entire process for a single account: setup, login, raffles, logout.
    This function is designed to be run in a separate thread.
    """
    email = account.get("email")
    password = account.get("password")

    if not email or not password:
        print("Skipping an account due to missing email or password.")
        return

    print(f"--- Starting process for account: {email} ---")
    # Each thread needs its own WebDriver instance.
    # Change to headless=False to debug a single thread.
    driver = setup_driver(headless=True)
    try:
        if login(driver, email, password):
            handle_raffles(driver, email)
            print(f"--- Finished processing raffles for account: {email} ---")
            logout(driver, email)
        else:
            print(f"--- Skipping raffles for {email} due to login failure. ---")
    except Exception as e:
        print(f"--- A critical error occurred while processing account {email}: {e} ---")
        driver.save_screenshot(f"critical_error_{email}_{time.time()}.png")
    finally:
        # Ensure the driver for this thread is always closed.
        driver.quit()
        print(f"--- WebDriver for {email} has been closed. ---")


def main():
    """
    Main function to orchestrate the parallel processing of multiple accounts.
    """
    accounts = [
        {"email": os.getenv("ACCOUNT_1_EMAIL"), "password": os.getenv("ACCOUNT_1_PASSWORD")},
        {"email": os.getenv("ACCOUNT_2_EMAIL"), "password": os.getenv("ACCOUNT_2_PASSWORD")},
        # Add more accounts here. The script will process them in parallel.
    ]

    # Use a ThreadPoolExecutor to process accounts concurrently.
    # The number of workers determines how many accounts are processed at the same time.
    max_workers = len(accounts)
    print(f"Starting parallel processing for {len(accounts)} accounts with {max_workers} workers.")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # map() will apply the process_account function to each item in the accounts list.
        executor.map(process_account, accounts)

    print("-" * 50)
    print("All accounts have been processed.")

if __name__ == "__main__":
    main()
