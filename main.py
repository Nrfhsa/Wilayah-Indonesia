import requests
from bs4 import BeautifulSoup
import time
import json
import logging
from datetime import datetime
import os

class GetSession:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://cekbansos.kemensos.go.id"
        self.last_token_refresh = None
        self.token_lifetime = 3600  
        self.setup_logging()
        self.refresh_token()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='process.log'
        )
        self.logger = logging.getLogger(__name__)

    def refresh_token(self):
        try:
            response = self.session.get(f"{self.base_url}")
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
            
            self.session.headers.update({
                'X-CSRF-TOKEN': csrf_token,
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            self.last_token_refresh = datetime.now()
            self.logger.info("CSRF token refreshed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error refreshing token: {str(e)}")
            return False

    def check_token_expiry(self):
        if not self.last_token_refresh:
            return True
            
        time_elapsed = (datetime.now() - self.last_token_refresh).total_seconds()
        return time_elapsed >= self.token_lifetime

    def make_request(self, endpoint, method='POST', data=None, retries=3):
        if self.check_token_expiry():
            self.refresh_token()

        for attempt in range(retries):
            try:
                if method.upper() == 'POST':
                    response = self.session.post(
                        f"{self.base_url}/{endpoint}",
                        data=data
                    )
                else:
                    response = self.session.get(
                        f"{self.base_url}/{endpoint}"
                    )

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 419:  
                    self.logger.warning("CSRF token expired, refreshing...")
                    self.refresh_token()
                    continue
                else:
                    self.logger.error(f"Request failed with status code: {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"Request attempt {attempt + 1} failed: {str(e)}")
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)  

        return None

class GetData:
    def __init__(self):
        self.session = GetSession()
        self.results = {
            "metadata": {
                "timestamp": str(datetime.now()),
                "source": "cekbansos.kemensos.go.id",
                "statistics": {
                    "provinces": 0,
                    "cities": 0,
                    "districts": 0,
                    "villages": 0
                }
            },
            "province": {}
        }
        self.rate_limit = 1  

    def parse_options(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        options = {}
        for option in soup.find_all('option'):
            value = option.get('value')
            if value and value != '0' and not value.startswith('==='):
                options[value] = option.text.strip()
        return options

    def get_provinces(self):
        html = self.session.make_request('provinsi')
        if html:
            return self.parse_options(html)
        return {}

    def get_cities(self, province_code):
        html = self.session.make_request('kabupaten', data={'kdprop': province_code})
        if html:
            return self.parse_options(html)
        return {}

    def get_districts(self, province_code, city_code):
        html = self.session.make_request('kecamatan', data={
            'kdprop': province_code,
            'kdkab': city_code
        })
        if html:
            return self.parse_options(html)
        return {}

    def get_villages(self, province_code, city_code, district_code):
        html = self.session.make_request('desa', data={
            'kdprop': province_code,
            'kdkab': city_code,
            'kdkec': district_code
        })
        if html:
            return self.parse_options(html)
        return {}

    def update_statistics(self, level, count):
        self.results["metadata"]["statistics"][level] += count

    def scrape_all(self):
        try:
            provinces = self.get_provinces()
            self.update_statistics("provinces", len(provinces))
            self.session.logger.info(f"Found {len(provinces)} provinces")

            for province_code, province_name in provinces.items():
                time.sleep(self.rate_limit)
                
                self.results["province"][province_code] = {
                    "name": province_name,
                    "cities": {}
                }
                
                cities = self.get_cities(province_code)
                self.update_statistics("cities", len(cities))
                self.session.logger.info(f"Found {len(cities)} cities for province: {province_name}")
                
                for city_code, city_name in cities.items():
                    time.sleep(self.rate_limit)
                    
                    self.results["province"][province_code]["cities"][city_code] = {
                        "name": city_name,
                        "districts": {}
                    }
                    
                    districts = self.get_districts(province_code, city_code)
                    self.update_statistics("districts", len(districts))
                    
                    for district_code, district_name in districts.items():
                        time.sleep(self.rate_limit)
                        
                        self.results["province"][province_code]["cities"][city_code]["districts"][district_code] = {
                            "name": district_name,
                            "villages": {}
                        }
                        
                        villages = self.get_villages(province_code, city_code, district_code)
                        self.update_statistics("villages", len(villages))
                        
                        self.results["province"][province_code]["cities"][city_code]["districts"][district_code]["villages"] = villages
                        
                        self.session.logger.info(f"Scraped {len(villages)} villages for district: {district_name} in {city_name}")

            return self.results

        except Exception as e:
            self.session.logger.error(f"Error during scraping: {str(e)}")
            raise

    def save_results(self, output_dir="output"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_dir}/administrative_hierarchy_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        stats = self.results["metadata"]["statistics"]
        self.session.logger.info(f"Final statistics: {stats['provinces']} provinces, {stats['cities']} cities, "
                        f"{stats['districts']} districts, {stats['villages']} villages")
        
        return output_file

def main():
    try:
        scraper = GetData()
        scraper.scrape_all()
        output_file = scraper.save_results()
        
        print(f"Scraping completed successfully. Results saved to {output_file}")
        
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        logging.error(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    main()