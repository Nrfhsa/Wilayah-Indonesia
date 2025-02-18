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
        self.token_lifetime = 3500  # 50 detik margin
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
            response = self.session.get(
                f"{self.base_url}",
                timeout=10
            )
            soup = BeautifulSoup(response.text, 'html.parser')
            
            token_tag = soup.find('meta', {'name': 'csrf-token'})
            if not token_tag:
                self.logger.error("CSRF token meta tag not found")
                return False
                
            csrf_token = token_tag.get('content')
            if not csrf_token:
                self.logger.error("CSRF token content empty")
                return False

            self.session.headers.update({
                'X-CSRF-TOKEN': csrf_token,
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        if self.check_token_expiry() and not self.refresh_token():
            self.logger.error("Failed to refresh expired token")
            return None

        for attempt in range(retries):
            try:
                if method.upper() == 'POST':
                    response = self.session.post(
                        f"{self.base_url}/{endpoint}",
                        data=data,
                        timeout=15
                    )
                else:
                    response = self.session.get(
                        f"{self.base_url}/{endpoint}",
                        timeout=15
                    )

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 419:
                    self.logger.warning("CSRF token expired, refreshing...")
                    if not self.refresh_token():
                        continue
                elif response.status_code == 429:
                    retry_after = 10
                    self.logger.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                else:
                    self.logger.error(f"Request failed with status code: {response.status_code}")
                    
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == retries - 1:
                    raise
                time.sleep(5)
                
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
                    "total_provinces": 0,
                    "total_cities/regencies": 0,
                    "total_districts": 0,
                    "total_villages": 0
                }
            },
            "hierarchy": {
                "provinces": []
            }
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
        if not html:
            raise Exception("Failed to fetch provinces after retries")
        return self.parse_options(html)

    def get_cities(self, province_code):
        html = self.session.make_request('kabupaten', data={'kdprop': province_code})
        if not html:
            raise Exception(f"Failed to fetch cities for province {province_code}")
        return self.parse_options(html)

    def get_districts(self, province_code, city_code):
        html = self.session.make_request('kecamatan', data={
            'kdprop': province_code,
            'kdkab': city_code
        })
        if not html:
            raise Exception(f"Failed to fetch districts for city {city_code}")
        return self.parse_options(html)

    def get_villages(self, province_code, city_code, district_code):
        html = self.session.make_request('desa', data={
            'kdprop': province_code,
            'kdkab': city_code,
            'kdkec': district_code
        })
        if not html:
            raise Exception(f"Failed to fetch villages for district {district_code}")
        return self.parse_options(html)

    def scrape_all(self):
        try:
            provinces = self.get_provinces()
            total_provs = len(provinces)
            self.results["metadata"]["statistics"]["total_provinces"] = total_provs
            
            print(f"\n🟢 Found {total_provs} provinces")
            print("===========================================")

            for index, (prov_code, prov_name) in enumerate(provinces.items(), 1):
                print(f"\n🔵 Starting to scrape Province [{index}/{total_provs}]: {prov_name}")
                
                province_data = {
                    "code": prov_code,
                    "name": prov_name,
                    "total_cities/regencies": 0,
                    "cities": []
                }
                
                try:
                    cities = self.get_cities(prov_code)
                except Exception as e:
                    self.session.logger.error(f"Skipping province {prov_code}: {str(e)}")
                    continue
                
                province_data["total_cities/regencies"] = len(cities)
                self.results["metadata"]["statistics"]["total_cities/regencies"] += len(cities)
                
                for city_code, city_name in cities.items():
                    city_data = {
                        "code": city_code,
                        "name": city_name,
                        "total_districts": 0,
                        "districts": []
                    }
                    
                    try:
                        districts = self.get_districts(prov_code, city_code)
                    except Exception as e:
                        self.session.logger.error(f"Skipping city {city_code}: {str(e)}")
                        continue
                    
                    city_data["total_districts"] = len(districts)
                    self.results["metadata"]["statistics"]["total_districts"] += len(districts)
                    
                    for dist_code, dist_name in districts.items():
                        district_data = {
                            "code": dist_code,
                            "name": dist_name,
                            "total_villages": 0,
                            "villages": []
                        }
                        
                        try:
                            villages = self.get_villages(prov_code, city_code, dist_code)
                        except Exception as e:
                            self.session.logger.error(f"Skipping district {dist_code}: {str(e)}")
                            continue
                        
                        district_data["total_villages"] = len(villages)
                        self.results["metadata"]["statistics"]["total_villages"] += len(villages)
                        
                        district_data["villages"] = [{
                            "code": village_code,
                            "name": village_name
                        } for village_code, village_name in villages.items()]
                        
                        city_data["districts"].append(district_data)
                        time.sleep(self.rate_limit)
                    
                    province_data["cities"].append(city_data)
                    time.sleep(self.rate_limit)
                
                self.results["hierarchy"]["provinces"].append(province_data)
                print(f"🟢 Completed: {prov_name} ({len(cities)} cities)")
                time.sleep(self.rate_limit)

            return self.results

        except Exception as e:
            self.session.logger.error(f"Fatal error during scraping: {str(e)}")
            raise

    def save_results(self, output_dir="output"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"Hierarchy_data_{timestamp}.json")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.session.logger.error(f"Failed to save results: {str(e)}")
            raise

        stats = self.results["metadata"]["statistics"]
        print("\n📊 Final Statistics:")
        print(f"• Total Provinces: {stats['total_provinces']}")
        print(f"• Total Cities/Regencies: {stats['total_cities/regencies']}")
        print(f"• Total Districts: {stats['total_districts']}")
        print(f"• Total Villages: {stats['total_villages']}")
        
        return output_file

def main():
    try:
        scraper = GetData()
        print("🚀 Starting Hierarchy data scraping process...")
        start_time = time.time()
        
        data = scraper.scrape_all()
        output_file = scraper.save_results()
        
        duration = time.time() - start_time
        print(f"\n✅ Scraping process completed in {duration:.2f} seconds")
        print(f"📁 Data saved at: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Critical error: {str(e)}")
        logging.error(f"Main process failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
