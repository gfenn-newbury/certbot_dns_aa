import logging
import os
import time
from certbot import errors
from certbot.plugins import dns_common
from zope.interface import implementer

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class Authenticator(dns_common.DNSAuthenticator):
    """
    Certbot Authenticator for Andrews & Arnold Control Pages using Selenium.
    """

    description = "Obtain certificates using a DNS-01 challenge via Andrews & Arnold Control Pages automation."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):
        super().add_parser_arguments(add, default_propagation_seconds=60)
        add("credentials", help="Path to A&A credentials INI file (or use environment variables).")

    def more_info(self):
        return "Configure your Andrews & Arnold credentials to allow Certbot to automatically manage DNS-01 TXT records."

    def _setup_credentials(self):
        # Fallback to environment variables if no credentials file is passed, 
        # matching your original script design.
        self.username = os.environ.get("AA_USERNAME")
        self.password = os.environ.get("AA_PASSWORD")
        
        if self.conf("credentials"):
            pass

        if not self.username or not self.password:
            raise errors.PluginError("A&A Username and Password must be provided via environment variables.")

    def _perform(self, domain, validation_name, validation_value):
        self._setup_credentials()
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()), options=options
        )
        wait = WebDriverWait(driver, 15)

        try:
            logger.info("Navigating to Andrews & Arnold Control Pages login...")
            driver.get("https://control.aa.net.uk/")


            username_field = wait.until(
                EC.presence_of_element_located((By.NAME, "USERNAME"))
            )
            password_field = driver.find_element(By.NAME, "PASSWORD")

            username_field.send_keys(self.username)
            password_field.send_keys(self.password)

            login_button = driver.find_element(
                By.XPATH, "//button[@type='submit'] | //input[@type='submit']"
            )
            login_button.click()


            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(text(), 'Logout')]")
                )
            )
            logger.info("Successfully logged into A&A Control Pages.")

            logger.info(f"Navigating to DNS settings for {domain}...")
            domain_link = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//a[contains(text(), '{domain}')]")
                )
            )
            domain_link.click()

            # 4. Input DNS TXT Record Data
            record_type = wait.until(
                EC.presence_of_element_located((By.NAME, "rectype"))
            )
            Select(record_type).select_by_visible_text("TXT")

            ttl_elem = wait.until(
                EC.presence_of_element_located((By.NAME, "TTL"))
            )
            Select(ttl_elem).select_by_visible_text("1 minute")

            record_name = wait.until(
                EC.presence_of_element_located((By.NAME, "node"))
            )

            record_name.send_keys(validation_name)

            record_value = wait.until(
                EC.presence_of_element_located((By.NAME, "recvalue"))
            )
            record_value.send_keys(validation_value)
            record_value.send_keys(Keys.ENTER)

            logger.info("Successfully added DNS challenge record.")
            time.sleep(5)  # Allow form submission to settle

        except Exception as e:
            logger.error(f"Failed to add DNS record via Selenium: {e}")
            raise errors.PluginError(f"Selenium automation failed: {e}")
        finally:
            driver.quit()

    def _cleanup(self, domain, validation_name, validation_value):
        pass

    # Certbot hooks
    def perform(self, achalls):
        responses = []
        for achall in achalls:
            domain = achall.domain
            # Extract challenge details
            validation_name = "_acme-challenge" # adjust based on whether it needs full or relative node
            validation_value = achall.validation(achall.account_key)
            logger.info(f"Validation value: {validation_value}")
            self._perform(domain, validation_name, validation_value)
            responses.append(achall.response(achall.account_key))
        return responses

    def cleanup(self, achalls):
        for achall in achalls:
            domain = achall.domain
            validation_name = "_acme-challenge"
            validation_value = achall.validation(achall.account_key)
            self._cleanup(domain, validation_name, validation_value)