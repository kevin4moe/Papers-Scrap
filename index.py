import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re

term = "health"

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
        except:
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
            print(f"Error parsing author info: {str(e)}")
            return '', None
        
    def scrape_page(self, url):
        try:
            time.sleep(random.uniform(5, 10))  # Increased delay
            headers = {
                'User-Agent': self.get_random_user_agent()
            }
            response = requests.get(url, headers=headers)#, proxies=self.proxies)
            response.raise_for_status()
            
            # Debug: Print the full response
            # print(response.text)  # Check for CAPTCHA or blocking
            
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = soup.find_all('div', class_='gs_r gs_or gs_scl')
            
            results = []
            for article in articles:
                try:
                    title_element = article.find('h3', class_='gs_rt')
                    title = title_element.get_text() if title_element else 'No Title'
                    url = title_element.find('a')['href'] if title_element and title_element.find('a') else 'No URL'
                    
                    authors_element = article.find('div', class_='gs_a')
                    authors, year = '', None
                    if authors_element:
                        authors_text = authors_element.get_text()
                        print(f"Authors text: {authors_text}")  # Debug statement
                        authors, year = self.parse_author_info(authors_text)
                    
                    description_element = article.find('div', class_='gs_rs')
                    description = description_element.get_text() if description_element else ''
                    
                    cite_element = article.find('div', class_='gs_fl')
                    citations = 0
                    if cite_element:
                        cite_text = cite_element.find(text=lambda t: t and 'Cited by' in t)
                        if cite_text:
                            citations = int(''.join(filter(str.isdigit, cite_text)))
                    
                    results.append({
                        'title': title,
                        'authors': authors,
                        'year': year if year else pd.NA,
                        'description': description,
                        'url': url,
                        'citations': citations
                    })
                except Exception as e:
                    print(f"Error processing article: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Error scraping page: {str(e)}")
            return []
    
    def scrape_multiple_pages(self, base_url, num_articles=10):  # Start with a smaller number
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
            
            time.sleep(random.uniform(5, 10))  # Increased delay
        
        all_results = all_results[:num_articles]
        return pd.DataFrame(all_results)

def main():
    scraper = GoogleScholarScraper()
    base_url = f"https://scholar.google.com/scholar?q={term}&hl=en&as_sdt=0,5&as_ylo=2018&as_yhi=2025"
    
    df = scraper.scrape_multiple_pages(base_url, num_articles=400)  # Start with a smaller number
    
    if df.empty:
        print("No results found!")
        return
    
    try:
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df = df.sort_values('citations', ascending=False)
        
        if not df['year'].isna().all():
            df = df.sort_values(['year', 'citations'], ascending=[False, False], na_position='last')
        
        output_filename = f'{term}_google_scholar_results.csv'
        df.to_csv(output_filename, index=False)
        print(f"\nScraped {len(df)} articles and saved to {output_filename}")
        
        print("\nYear distribution:")
        year_counts = df['year'].value_counts().sort_index()
        if not year_counts.empty:
            print(year_counts)
        else:
            print("No valid years found in the data")
        
        print("\nFirst few results:")
        print(df[['title', 'year', 'citations']].head())
        
    except Exception as e:
        print(f"Error processing results: {str(e)}")
        df.to_csv(f'{term}_google_scholar_results_raw.csv', index=False)
        print("Saved raw results to backup file")

if __name__ == "__main__":
    main()