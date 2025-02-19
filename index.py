import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
from tqdm import tqdm
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

term = "biology"

class GoogleScholarScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
            # Add more user agents here
        ]
        self.proxies = {
            'http': 'http://your_proxy:port',  # Replace with your proxy
            'https': 'http://your_proxy:port',  # Replace with your proxy
        }
        self.articles_processed = 0
        
    def get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def extract_year(self, text):
        try:
            year_match = re.search(r'(?:19|20)\d{2}(?!\d)', text)
            if year_match:
                year = int(year_match.group())
                if 1900 <= year <= 2024:
                    return year
            return None
        except Exception as e:
            logger.error(f"Error extracting year from text: {text}. Error: {str(e)}")
            return None
        
    def parse_author_info(self, text):
        try:
            parts = re.split(r'[…-]', text)
            parts = [part.strip() for part in parts if part.strip()]
            authors = parts[0] if parts else ''
            year = None
            for part in parts:
                year = self.extract_year(part)
                if year:
                    break
            return authors, year
        except Exception as e:
            logger.error(f"Error parsing author info: {str(e)}")
            return '', None
        
    def scrape_page(self, url, pbar):
        try:
            delay = random.uniform(5, 10)
            tqdm.write(f"Waiting {delay:.2f} seconds before next request")
            time.sleep(delay)
            
            headers = {'User-Agent': self.get_random_user_agent()}
            response = requests.get(url, headers=headers)#, proxies=self.proxies)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('div', class_='gs_r gs_or gs_scl')
            
            results = []
            # Remove nested progress bar for articles
            for article in articles:
                try:
                    title_element = article.find('h3', class_='gs_rt')
                    title = title_element.get_text() if title_element else 'No Title'
                    url = title_element.find('a')['href'] if title_element and title_element.find('a') else 'No URL'
                    
                    authors_element = article.find('div', class_='gs_a')
                    authors, year = '', None
                    if authors_element:
                        authors_text = authors_element.get_text()
                        logger.debug(f"Processing authors text: {authors_text}")
                        authors, year = self.parse_author_info(authors_text)
                    
                    description_element = article.find('div', class_='gs_rs')
                    description = description_element.get_text() if description_element else ''
                    
                    # Look for the citations div
                    cite_element = article.find('div', class_='gs_fl gs_flb')
                    citations = 0

                    if cite_element:
                        # Look for "Cited by" link (text-based OR href-based)
                        cite_link = cite_element.find('a', text=lambda t: t and 'Cited by' in t) or \
                                    cite_element.find('a', href=lambda x: x and 'cites=' in x)

                        if cite_link:
                            citations = int(''.join(filter(str.isdigit, cite_link.get_text())))
                        else:
                            # Fall back: Iterate over all links to find "Cited by"
                            for link in cite_element.find_all('a'):
                                if 'Cited by' in link.get_text():
                                    citations = int(''.join(filter(str.isdigit, link.get_text())))
                                    break  # No need to continue once we find it
                    
                    results.append({
                        'title': title,
                        'authors': authors,
                        'year': year if year else pd.NA,
                        'description': description,
                        'url': url,
                        'citations': citations
                    })
                    
                    self.articles_processed += 1
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error scraping page: {str(e)}")
            return []
    
    def scrape_multiple_pages(self, base_url, num_articles=10):
        all_results = []
        num_pages = (num_articles + 9) // 10
        
        logger.info(f"Starting scraping of {num_articles} articles across {num_pages} pages")
        
        with tqdm(total=num_articles, desc="Total Progress", unit="article", dynamic_ncols=True, position=0, leave=True) as pbar:
            for page in range(num_pages):
                start = page * 10
                url = f"{base_url}&start={start}"
                
                # Update progress description
                pbar.set_description(f"Page {page + 1}/{num_pages}")
                results = self.scrape_page(url, pbar)
                all_results.extend(results)
                
                if not results or len(all_results) >= num_articles:
                    break
                
                delay = random.uniform(5, 10)
                # Use tqdm.write for logging to avoid interference with progress bar
                tqdm.write(f"Waiting {delay:.2f} seconds before next page")
                time.sleep(delay)
        
        all_results = all_results[:num_articles]
        logger.info(f"Completed scraping. Total articles collected: {len(all_results)}")
        return pd.DataFrame(all_results)

def main():
    logger.info(f"Starting Google Scholar scraping for term: {term}")
    
    scraper = GoogleScholarScraper()
    base_url = f"https://scholar.google.com/scholar?q={term}&hl=en&as_sdt=0,5&as_ylo=2018&as_yhi=2025"
    
    df = scraper.scrape_multiple_pages(base_url, num_articles=200)
    
    if df.empty:
        logger.error("No results found!")
        return
    
    try:
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df = df.sort_values('citations', ascending=False)
        
        if not df['year'].isna().all():
            df = df.sort_values(['year', 'citations'], ascending=[False, False], na_position='last')
        
        output_filename = f'{term}_google_scholar_results.csv'
        df.to_csv(output_filename, index=False)
        logger.info(f"Scraped {len(df)} articles and saved to {output_filename}")
        
        logger.info("Year distribution:")
        year_counts = df['year'].value_counts().sort_index()
        if not year_counts.empty:
            logger.info("\n" + str(year_counts))
        else:
            logger.warning("No valid years found in the data")
        
        logger.info("First few results:")
        logger.info("\n" + str(df[['title', 'year', 'citations']].head()))
        
    except Exception as e:
        logger.error(f"Error processing results: {str(e)}")
        backup_filename = f'{term}_google_scholar_results_raw.csv'
        df.to_csv(backup_filename, index=False)
        logger.info(f"Saved raw results to backup file: {backup_filename}")

if __name__ == "__main__":
    main()