import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

term = "health"

class GoogleScholarScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def scrape_page(self, url):
        try:
            time.sleep(random.uniform(2, 5))
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('div', class_='gs_r gs_or gs_scl')
            
            results = []
            for article in articles:
                # Extract article title and URL
                title_element = article.find('h3', class_='gs_rt')
                title = title_element.get_text() if title_element else ''
                url = title_element.find('a')['href'] if title_element and title_element.find('a') else None
                
                # Extract authors
                authors_element = article.find('div', class_='gs_a')
                authors = authors_element.get_text() if authors_element else ''
                
                # Extract description
                description_element = article.find('div', class_='gs_rs')
                description = description_element.get_text() if description_element else ''
                
                # Extract citation count
                cite_element = article.find('div', class_='gs_fl')
                citations = 0
                if cite_element:
                    cite_text = cite_element.find(text=lambda t: t and 'Cited by' in t)
                    if cite_text:
                        citations = int(''.join(filter(str.isdigit, cite_text)))
                
                results.append({
                    'title': title,
                    'authors': authors,
                    'description': description,
                    'url': url,
                    'citations': citations
                })
            
            return results
            
        except Exception as e:
            print(f"Error scraping page: {str(e)}")
            return []
    
    def scrape_multiple_pages(self, base_url, num_articles=200):
        all_results = []
        num_pages = (num_articles + 9) // 10
        
        for page in range(num_pages):
            start = page * 10
            url = f"{base_url}&start={start}"
            
            print(f"Scraping page {page + 1}/{num_pages} ({len(all_results)} articles collected)...")
            results = self.scrape_page(url)
            all_results.extend(results)
            
            if not results or len(all_results) >= num_articles:
                break
            
            time.sleep(random.uniform(3, 7))
        
        all_results = all_results[:num_articles]
        return pd.DataFrame(all_results)

def main():
    scraper = GoogleScholarScraper()
    base_url = f"https://scholar.google.com/scholar?as_ylo=2019&q={term}&hl=en&as_sdt=0,5"
    
    df = scraper.scrape_multiple_pages(base_url, num_articles=200)
    
    # Clean the authors field (optional)
    df['authors'] = df['authors'].str.split('-').str[0]  # Takes the part before the first dash
    
    df.to_csv(f'{term}_google_scholar_results.csv', index=False)
    print(f"Scraped {len(df)} articles and saved to {term}_google_scholar_results.csv")
    
    print("\nFirst few results:")
    print(df.head())

if __name__ == "__main__":
    main()