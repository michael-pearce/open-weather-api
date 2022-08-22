# Description

open-weather-api is a simple flask web app that  allows you to check the historical 5-day weather and current weather of any city on the OpenWeather API [list.](https://openweathermap.org/)

## Requirements

Users must have a valid API Key from OpenWeather which can be obtained for free from [here.](https://home.openweathermap.org/users/sign_up)

To run the flask app, users must have their API key and a random seed set as environment variables. Please see below for Windows instructions with Python.

```python
import os

# sets required environment variables
os.environ['YOUR_API_KEY'] = "YOUR_API_KEY_HERE"
os.environ['YOUR_SECRET_KEY'] = "RANDOM_SEED_HERE"
```

## License
[MIT](https://choosealicense.com/licenses/mit/)