from flask import Flask, request, render_template_string
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import requests

app = Flask(__name__)

# ---------------- LOAD DATA ----------------
data = pd.read_csv(r"D:\COLLEGE\VS Python\Crop_recommendation_full_2200.csv")

X = data.drop('label', axis=1)
y = data['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier()
model.fit(X_train, y_train)

# ---------------- WEATHER ----------------
def get_weather(city):
    try:
        api_key = "8bf7500948c047fae94c72b93172951e"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        res = requests.get(url).json()

        if res.get("cod") != 200:
            return None, None

        return res["main"]["temp"], res["main"]["humidity"]
    except:
        return None, None

# ---------------- IMAGE MAP ----------------
crop_images = {
    "rice": "static/images/rice.jpg",
    "wheat": "static/images/wheat.jpg",
    "maize": "static/images/maize.jpg",
    "cotton": "static/images/cotton.jpg",
    "sugarcane": "static/images/sugarcane.jpg",
    "potato": "static/images/potato.jpg",
    "onion": "static/images/onion.jpg",
    "tomato": "static/images/tomato.jpg",
    "chilli": "static/images/chilli.jpg",
    "groundnut": "static/images/groundnut.jpg",
    "sunflower": "static/images/sunflower.jpg",
    "coffee": "static/images/coffee.jpg"
}

default_img = "static/images/default.jpg"

# ---------------- EXPLANATION ----------------
def get_explanation(temp, humidity):
    reasons = []
    if temp > 25:
        reasons.append("🌡 Warm temperature supports growth")
    if humidity > 60:
        reasons.append("💧 High humidity is suitable")
    return reasons

# ---------------- HTML ----------------
html = """
<!DOCTYPE html>
<html>
<head>
<title>AI Crop Recommendation</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    font-family: 'Segoe UI';
    background: linear-gradient(135deg, #43cea2, #185a9d);
    color: white;
}

.header {
    text-align: center;
    padding: 20px;
    font-size: 28px;
    font-weight: bold;
}

.container {
    width: 90%;
    max-width: 900px;
    margin: auto;
}

.card {
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(10px);
    padding: 25px;
    border-radius: 20px;
}

input {
    width: 100%;
    padding: 12px;
    border-radius: 10px;
    border: none;
    margin-bottom: 12px;
}

.grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
}

.full { grid-column: span 2; }

button {
    margin-top: 10px;
    width: 100%;
    padding: 12px;
    background: #00c853;
    color: white;
    border: none;
    border-radius: 10px;
    cursor: pointer;
}

.result {
    text-align: center;
    margin-top: 15px;
    font-size: 22px;
    color: #00ffcc;
}

/* ✅ IMAGE FIX */
.image-box {
    display: flex;
    justify-content: center;
}

.image-box img {
    width: 300px;          /* reduced size */
    height: 200px;         /* fixed height */
    object-fit: cover;     /* prevent stretching */
    border-radius: 12px;
    margin-top: 15px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.3);
}

.explain {
    margin-top: 10px;
    background: rgba(255,255,255,0.2);
    padding: 12px;
    border-radius: 10px;
}

@media(max-width:600px) {
    .grid { grid-template-columns: 1fr; }
    .full { grid-column: span 1; }

    .image-box img {
        width: 100%;
        height: auto;
    }
}
</style>
</head>

<body>

<div class="header">🌱 AI Crop Recommendation System</div>

<div class="container">
<div class="card">

<form method="POST">

<input name="city" placeholder="Enter City" required>

<div class="grid">
<input name="N" placeholder="Nitrogen" required>
<input name="P" placeholder="Phosphorus" required>
<input name="K" placeholder="Potassium" required>
<input name="temp" placeholder="Temperature (optional)">
<input name="humidity" placeholder="Humidity (optional)">
<input name="ph" placeholder="pH" required>
<input class="full" name="rainfall" placeholder="Rainfall" required>
</div>

<button>Get Recommendation</button>
</form>

{% if result %}
<div class="result">🌾 {{ result }}</div>

<div class="image-box">
<img src="/{{ image }}" alt="Crop Image">
</div>

<div class="explain">
<b>Why this crop?</b><br>
{% for r in explanation %}
✔ {{ r }}<br>
{% endfor %}
</div>
{% endif %}

</div>
</div>

</body>
</html>
"""

# ---------------- ROUTE ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    result = None
    image = None
    explanation = None

    if request.method == "POST":
        try:
            city = request.form["city"]
            temp_api, humidity_api = get_weather(city)

            temp = float(request.form["temp"]) if request.form["temp"] else (temp_api or 25)
            humidity = float(request.form["humidity"]) if request.form["humidity"] else (humidity_api or 70)

            values = [
                float(request.form["N"]),
                float(request.form["P"]),
                float(request.form["K"]),
                temp,
                humidity,
                float(request.form["ph"]),
                float(request.form["rainfall"])
            ]

            result = model.predict([values])[0]

            image = crop_images.get(result.lower(), default_img)
            explanation = get_explanation(temp, humidity)

        except Exception as e:
            result = "Error: " + str(e)

    return render_template_string(html, result=result, image=image, explanation=explanation)

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("Starting Flask App...")
    app.run(debug=True)