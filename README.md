# Administrative Hierarchy Scraper

"A Python web scraper that extracts administrative hierarchy data from cekbansos.kemensos.go.id, including codes for provinces, cities, districts, and villages in Indonesia."

## Installation & Usage

1. Clone this repository
   ```bash
   git clone https://github.com/Nrfhsa/Wilayah-Indonesia
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the scraper:
   ```bash
   python main.py
   ```

## Data Structure

```json
{
  "metadata": {
    "timestamp": "",
    "source": "cekbansos.kemensos.go.id",
    "statistics": {
      "provinces": 0,
      "cities": 0,
      "districts": 0,
      "villages": 0
    }
  },
  "province": {
    "province_code": {
      "name": "Province Name",
      "cities": {
        "city_code": {
          "name": "City Name",
          "districts": {
            "district_code": {
              "name": "District Name",
              "villages": ["Village 1", "Village 2"]
            }
          }
        }
      }
    }
  }
}
```

