import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    # Initialize Chrome options
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-popup-blocking')
    options.headless = False  # Set to True if headless mode is required

    # Desired capabilities for logging
    capabilities = webdriver.DesiredCapabilities().CHROME
    capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

    # Launch the browser using undetected_chromedriver
    driver = uc.Chrome(headless=False, use_subprocess=False, options=options)

    # Save session details for reuse
    command_url = driver.command_executor._url
    session_id = driver.session_id

    session_script = f"""
url = '{command_url}'
session_id = "{session_id}"
"""

    # Print session details
    print(f"Command URL: {command_url}")
    print(f"Session ID: {session_id}")

    # Write session script to a file
    session_file =  'selenium_session_details.py'
    with open(session_file, 'w') as file:
        file.write(session_script)

    print(f"Session details saved to: {session_file}")
