import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Function to log in to rausgegangen.de
def login(driver, email, password):
    driver.get("https://rausgegangen.de/login")

    # Wait for the page to fully load
    time.sleep(4)

    # Wait for and click the cookie acceptance button
    try:
        cookie_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".iubenda-cs-accept-btn.iubenda-cs-btn-primary"))
        )
        cookie_button.click()
    except Exception as e:
        print("Cookie acceptance button not found:", e)

    # Find and fill in the email and password fields
    email_field = driver.find_element(By.NAME, 'username')
    password_field = driver.find_element(By.NAME, 'password')

    email_field.send_keys(email)
    password_field.send_keys(password)

    # Wait until the login button is clickable and click it
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//button[@type="submit" and contains(text(), "Login")]'))
    )
    login_button.click()

# Function to handle the raffles
def handle_raffles(driver):
    page = 1
    while True:
        # Open the next page of lotteries
        driver.get(f"https://rausgegangen.de/en/stuttgart/category/lottery/?page={page}")
        time.sleep(3)

        # Wait for the tiles to load
        try:
            tiles = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.tile-medium'))
            )
        except Exception as e:
            print(f"No more lotteries on page {page}: {e}")
            break  # If no tiles are found, exit the loop

        print(f"Processing page {page}, number of tiles: {len(tiles)}")

        for tile in tiles:
            try:
                # Find the event link in the tile
                link = tile.find_element(By.CSS_SELECTOR, 'a.event-tile')
                event_url = link.get_attribute('href')

                # Open the link in a new tab
                driver.execute_script("window.open(arguments[0]);", event_url)
                driver.switch_to.window(driver.window_handles[-1])

                # Check if the "You’re in 🤞" button is present and skip the entry if found
                try:
                    youre_in_button = WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'You’re in 🤞')]"))
                    )
                    if youre_in_button:
                        print("Skipping this entry: already in lottery")
                        driver.close()  # Close the tab
                        driver.switch_to.window(driver.window_handles[0])  # Switch back to the main tab
                        continue
                except Exception as e:
                    print(f"No 'You’re in 🤞' button found: {e}")

                # Click the "WIN TICKETS" button
                try:
                    win_tickets_button = WebDriverWait(driver, 4).until(
                        EC.element_to_be_clickable((By.XPATH, "//button/span[contains(text(), 'WIN TICKETS')]"))
                    )
                    win_tickets_button.click()
                except Exception as e:
                    print(f"Error clicking 'WIN TICKETS' button: {e}")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

                # Click the "COUNT ME IN!" button in the modal
                try:
                    count_me_in_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '#lottery-participate-button'))
                    )
                    count_me_in_button.click()
                except Exception as e:
                    print(f"Error clicking 'COUNT ME IN!' button: {e}")
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    continue

                # Close the current tab and switch back
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

                # Short pause between actions to ensure everything works well
                time.sleep(2)

            except Exception as e:
                print(f"Error processing the tile: {e}")
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

        # Go to the next page
        page += 1

# Function to handle multiple accounts
def handle_multiple_accounts():
    # List of accounts stored in environment variables
    accounts = [
        {"email": os.getenv("ACCOUNT_1_EMAIL"), "password": os.getenv("ACCOUNT_1_PASSWORD")},
        {"email": os.getenv("ACCOUNT_2_EMAIL"), "password": os.getenv("ACCOUNT_2_PASSWORD")},
        # Add more accounts here if needed
    ]
    
    # WebDriver Setup
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()))
    
    for account in accounts:
        try:
            # Log in with the current account
            login(driver, account["email"], account["password"])
            
            # Handle raffles for the current account
            handle_raffles(driver)
            
            print(f"Finished processing for account: {account['email']}")
            time.sleep(5)  # Short pause between accounts

        except Exception as e:
            print(f"Error handling account {account['email']}: {e}")
        
    # Quit the driver after all accounts are processed
    driver.quit()

if __name__ == "__main__":
    handle_multiple_accounts()