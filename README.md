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
    "source": "",
    "statistics": {
      "total_provinces": 0,
      "total_cities/regencies": 0,
      "total_districts": 0,
      "total_villages": 0
    }
  },
  "hierarchy": {
    "provinces": [
      {
        "code": "",
        "name": "",
        "total_cities/regencies": 0,
        "cities": [
          {
            "code": "",
            "name": "",
            "total_districts": 0,
            "districts": [
              {
                "code": "",
                "name": "",
                "total_villages": 0,
                "villages": [
                  {
                    "code": "",
                    "name": ""
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

