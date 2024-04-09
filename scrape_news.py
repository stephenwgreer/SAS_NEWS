import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
import logging
import os
import csv
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


#############################################
### Scrappers
#############################################

class ScraperStrategy(ABC):

    @abstractmethod
    def scrape(self):
        pass

    @abstractmethod
    def get_source_name(self):
        pass

class OccGovScraper(ScraperStrategy):
    BASE_URL = "https://www.occ.gov"
    
    def scrape(self):
        response = requests.get(self.BASE_URL)
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select(".usa-card-group .usa-card__body a")
        return [(card.text.strip(), self.BASE_URL + card['href']) for card in cards]

    def get_source_name(self):
        return "OCC"

class FederalReserveScraper(ScraperStrategy):
    BASE_URL = "https://www.federalreserve.gov"
    
    def scrape(self):
        response = requests.get(self.BASE_URL + "/newsevents.htm")
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.select(".nePanelBox .news__item .news__title a")
        return [(item.text.strip(), self.BASE_URL + item['href']) for item in news_items]

    def get_source_name(self):
        return "Federal Reserve"

class WebScraper:

    def __init__(self, strategy: ScraperStrategy) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: ScraperStrategy):
        self._strategy = strategy

    def execute_scrape(self):
        """Executes the scraping operation and returns a list of tuples containing the title and link for each item."""
        return self._strategy.scrape()
    
    def get_source_name(self):
        """Returns the name of the source for the current strategy."""
        return self._strategy.get_source_name()

#############################################
### CSV Creation and Comparison
#############################################

def write_to_csv(links, source, filename="links.csv"):
    """Writes links to a CSV file"""
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:  # changed 'w' to 'a' to append
        writer = csv.writer(csvfile)
        for title, link in links:
            writer.writerow([title, link, source])

def load_existing_links():
    """Load existing links from CSV."""
    existing_links = set()

    with open('links.csv', 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header
        for row in reader:
            existing_links.add(row[1])  # Assuming the link is in the second column

    return existing_links

def get_new_links(existing_links, scraped_links):
    """Return links that are not in the existing set."""
    return [(title, link) for title, link in scraped_links if link not in existing_links]

#############################################
### If new link send email
#############################################

def send_email(new_links):
    # Assuming you have set up a way to send emails, for instance using PythonAnywhere's API, SMTP, etc.
    email_content = "Here are the new links:\n\n"
    for title, link in new_links:
        email_content += f"{title}: {link}\n"

    recipient_email = ["stephenwgreer@gmail.com","stephen.greer@sas.com"]

    msg = EmailMessage()
    msg.set_content(email_content)
    msg['Subject'] = "New Content"
    msg['From'] = 'stephenisalertingyou@gmail.com'
    msg['To'] = recipient_email

    # Use environment variable to get password
    password = os.environ.get('APP_PW')
    sending_email = "stephenisalertingyou@gmail.com"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sending_email, password)
            server.send_message(msg)
            server.quit()
    except Exception as e:
        logging.error(f"Unable to send email. Error: {e}")
    

#############################################
### Main
#############################################

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Starting web scraper...")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    existing_links = load_existing_links()
    new_links =[]

    # Check if CSV file exists, if not create it
    if not os.path.exists('links.csv'):
        with open('links.csv', 'w', newline='', encoding='utf-8') as csvfile:  # Just write headers
            writer = csv.writer(csvfile)
            writer.writerow(["Title", "Link", "Source"])
    
    scraper = WebScraper(OccGovScraper())
    occ_links = scraper.execute_scrape()
    new_occ_links = get_new_links(existing_links, occ_links)
    if new_occ_links:
        print("\033[1m\033[94mNew OCC Links:\033[0m")
        for title, link in new_occ_links:
            print(f"{title}: {link}")
        write_to_csv(new_occ_links, scraper.get_source_name())
    else:
        print("\033[1m\033[94mNo new OCC links found.\033[0m")
    
    new_links.extend(new_occ_links)
    
    print("\n")

    scraper.set_strategy(FederalReserveScraper())
    fed_links = scraper.execute_scrape()
    new_fed_links = get_new_links(existing_links, fed_links)
    if new_fed_links:
        print("\033[1m\033[94mNew Federal Reserve Links:\033[0m")
        for title, link in new_fed_links:
            print(f"{title}: {link}")
        write_to_csv(new_fed_links, scraper.get_source_name())
    else:
        print("\033[1m\033[94mNo new Federal Reserve links found.\033[0m")

    new_links.extend(new_fed_links)

    return new_links


if __name__ == "__main__":
    new_links_found = main()
    
    if new_links_found:
        send_email(new_links_found)