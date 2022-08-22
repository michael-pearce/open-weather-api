# Import statements
from distutils.log import error
import pandas as pd
import json, requests, os
from flask_wtf import FlaskForm
from urllib.parse import urlencode
from collections import defaultdict
from wtforms import StringField, SubmitField
from datetime import datetime, timedelta, timezone
from wtforms.validators import DataRequired, ValidationError
from flask import Flask, render_template, redirect, url_for, send_file, request

# Create Flask instance
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["YOUR_SECRET_KEY"]
app.config["API_KEY"] = os.environ["YOUR_API_KEY"]

# Set hardcoded API URLs and length of historical days to check
currWeatherRoot = "http://api.openweathermap.org/data/2.5/weather?"
histWeatherRoot = "https://api.openweathermap.org/data/2.5/onecall/timemachine?"
iconRoot = "http://openweathermap.org/img/wn/"
historicalDays = 5

# Load list of valid city names from OpenWeather (~157K cities)
with open("./static/condensedCityList.json", encoding="utf8") as f:
    cityList = json.load(f)


class cityForm(FlaskForm):

    """
    cityForm:
        Custom user input form to select city from valid OpenWeather API list

    Args:
        FlaskForm: Base form class from "WTForms" package

    Raises:
        ValidationError: If city name is not listed in approved OpenWeather city list, prompt user to re-enter
    """

    city = StringField("City Name", validators=[DataRequired()])
    submit = SubmitField("Submit")
    country = StringField()

    def validate_city(self, field):
        city = str.strip(field.data).title()
        if city not in cityList:
            raise ValidationError(
                "Please enter a valid city name (non-case sensitive)."
            )


def callAPI(urlRoot: str, params: dict, iconRoot: str, histFlag: bool = False) -> dict:
    """
    callAPi:
        Main method for making API requests to OpenWeather. Can be configured to target multiple
        endpoints. If the icon for the weather type in the response object is not already cached,
        this function will request it from OpenWeather.

    Args:
        urlRoot (str): Root URL for one of OpenWeather's API endpoints
        params (dict): Dictionary of parameters to be appended to the root URL
        iconRoot (str): Root URL for OpenWeather's weather icon endpoint
        histFlag (bool): Indicates where you are calling the historical endpoint or not (changes dict structure correspondingly)

    Returns:
        response (dict): Raw json file supplied by the targeted OpenWeather API endpoint
    """
    fullURL = "".join([urlRoot, urlencode(params)])
    responseRaw = requests.get(fullURL).json()

    if histFlag:
        response = defaultdict(lambda: defaultdict(dict))
        response["weather"] = responseRaw["current"]["weather"]
        response["main"]["temp"] = responseRaw["current"]["temp"]
        response["dt"] = responseRaw["current"]["dt"]
    else:
        response = responseRaw

    iconName = "".join([response["weather"][0]["icon"], "@2x.png"])

    if not os.path.isfile(f"./static/{iconName}"):
        iconURL = "".join([iconRoot, iconName])
        iconResponse = requests.get(iconURL)

        with open(f"./static/{iconName}", "wb") as f:
            f.write(iconResponse.content)

    return response


def cleanAndStore(apiResponse: dict, weatherDict: dict) -> dict:
    """
    cleanAndStore:
        Extracts specific subset of weather stats from a raw OpenWeather response object,
        prepares them for display in Jinja template and appends to an existing dictionary

    Args:
        apiResponse (dict): Raw json file supplied by the targeted OpenWeather API endpoint
        weatherDict (dict): Dictionary with subset of fields as keys and lists for each corresponding value

    Returns:
        weatherDict (dict): Dictionary with cleaned subset of stats appended to the values of each key
    """

    weatherDict["date"].append(
        datetime.utcfromtimestamp(int(apiResponse["dt"])).strftime("%A, %b %d")
    )

    weatherDict["temp"].append(
        "".join([str(round(apiResponse["main"]["temp"], 1)), "°C"])
    )

    weatherDict["description"].append(
        str.title(apiResponse["weather"][0]["description"])
    )

    weatherDict["weather"].append(str.title(apiResponse["weather"][0]["main"]))

    weatherDict["iconName"].append(
        "".join([apiResponse["weather"][0]["icon"], "@2x.png"])
    )

    return weatherDict


# Define home page route
@app.route("/", methods=["GET", "POST"])
def homepage():

    city = None
    form = cityForm()

    if form.validate_on_submit():
        city = str.strip(form.city.data).title()
        form.city.data = None
        return redirect(url_for("results", city=city))

    return render_template("home.html", title="Weather Explorer", form=form, city=city)


# Define API results route
@app.route("/results", methods=["GET"])
def results():

    city = request.args.get("city")

    weatherDict = {
        "date": [],
        "weather": [],
        "description": [],
        "temp": [],
        "iconName": [],
    }

    todayParams = {"appid": app.config["API_KEY"], "q": city, "units": "metric"}
    todayResponse = callAPI(currWeatherRoot, todayParams, iconRoot, histFlag=False)
    weatherDict = cleanAndStore(todayResponse, weatherDict)

    histParams = {
        "appid": app.config["API_KEY"],
        "lat": todayResponse["coord"]["lat"],
        "lon": todayResponse["coord"]["lon"],
        "dt": None,
        "units": "metric",
    }

    for i in range(1, historicalDays + 1):

        date = datetime.now(timezone.utc) + timedelta(days=-i)
        dateUnix = str(round(date.timestamp()))
        histParams["dt"] = dateUnix
        histResponse = callAPI(histWeatherRoot, histParams, iconRoot, histFlag=True)
        weatherDict = cleanAndStore(histResponse, weatherDict)

    weatherDf = pd.DataFrame.from_dict(weatherDict).iloc[::-1]

    weatherDfSave = weatherDf.drop(["iconName"], axis=1)
    weatherDfSave.to_excel(f"./static/sessionData.xlsx")

    return render_template(
        "results.html",
        title="Weather Results",
        city=city,
        rawResponse=todayResponse,
        weatherDf=weatherDf,
    )


# Define route that serves the excel file
@app.route("/download", methods=["GET"])
def download():
    return send_file("./static/sessionData.xlsx")
