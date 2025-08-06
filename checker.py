#!/usr/bin/env python3
"""
Selenium Bot Template for BasoKa Login Checker
This bot runs in headless mode (no visible browser window)
Replace this with your actual Selenium automation code.
"""

import os
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_chrome_driver():
    """Setup Chrome driver with headless configuration"""
    chrome_options = Options()
    
    # Headless mode - no visible browser window
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Disable images and CSS for faster loading
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    
    # User agent to avoid detection
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    # Additional stealth options
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logger.error(f"Failed to setup Chrome driver: {e}")
        raise

def log_result(success: bool, username: str, details: str = "", additional_data: dict = None):
    """Log a login attempt result"""
    timestamp = datetime.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "username": username,
        "details": details,
        "ip": additional_data.get("ip") if additional_data else None,
        "user_agent": additional_data.get("user_agent") if additional_data else None
    }
    
    if success:
        file_path = Path("successful_logins.json")
    else:
        file_path = Path("failed_logins.json")
    
    # Read existing data
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    
    # Add new entry
    data.append(entry)
    
    # Write back to file
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    status = 'SUCCESS' if success else 'FAILED'
    logger.info(f"{status}: {username} at {timestamp} - {details}")

def check_login(driver, username: str, password: str, login_url: str) -> bool:
    """
    Perform login check using Selenium
    Replace this with your actual login logic
    """
    try:
        logger.info(f"Checking login for user: {username}")
        
        # Navigate to login page
        driver.get(login_url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # TODO: Replace these selectors with your actual login form selectors
        # Example login logic (replace with your actual selectors):
        
        # Find username field
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))  # Replace with actual selector
        )
        username_field.clear()
        username_field.send_keys(username)
        
        # Find password field
        password_field = driver.find_element(By.NAME, "password")  # Replace with actual selector
        password_field.clear()
        password_field.send_keys(password)
        
        # Submit form
        submit_button = driver.find_element(By.XPATH, "//input[@type='submit']")  # Replace with actual selector
        submit_button.click()
        
        # Wait for result and check if login was successful
        # Replace this logic with your actual success/failure detection
        time.sleep(3)
        
        # Example: Check if we're redirected to a success page or if error message appears
        try:
            # Look for success indicator (replace with your actual success check)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))  # Replace with actual selector
            )
            return True
        except TimeoutException:
            # Look for error message (replace with your actual error check)
            try:
                error_element = driver.find_element(By.CLASS_NAME, "error")  # Replace with actual selector
                error_message = error_element.text
                logger.warning(f"Login failed for {username}: {error_message}")
                return False
            except:
                logger.warning(f"Login failed for {username}: Unknown error")
                return False
    
    except Exception as e:
        logger.error(f"Error during login check for {username}: {e}")
        return False

def main():
    """Main bot loop"""
    logger.info("🤖 BasoKa Selenium Bot started (Headless Mode)")
    
    # Configuration - Replace with your actual values
    LOGIN_URL = "https://your-login-page.com"  # Replace with actual URL
    CHECK_INTERVAL = 60  # seconds between checks
    
    # Test credentials - Replace with your actual credential source
    test_credentials = [
        {"username": "user1", "password": "pass1"},
        {"username": "admin", "password": "admin123"},
        {"username": "test", "password": "test123"},
    ]
    
    driver = None
    
    try:
        # Setup Chrome driver
        driver = setup_chrome_driver()
        logger.info("Chrome driver initialized successfully (headless mode)")
        
        while True:
            for cred in test_credentials:
                username = cred["username"]
                password = cred["password"]
                
                try:
                    success = check_login(driver, username, password, LOGIN_URL)
                    
                    # Log the result
                    if success:
                        log_result(True, username, "Login successful")
                    else:
                        log_result(False, username, "Login failed")
                    
                    # Small delay between attempts
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error checking {username}: {e}")
                    log_result(False, username, f"Error: {str(e)}")
            
            logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check cycle...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error in bot: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Chrome driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

if __name__ == "__main__":
    main()
