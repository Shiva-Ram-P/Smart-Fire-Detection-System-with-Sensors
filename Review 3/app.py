from flask import Flask, request, render_template_string
import mysql.connector
import matplotlib.pyplot as plt
import datetime
import os
import csv
import re
from sklearn.linear_model import LinearRegression
import numpy as np

app = Flask(__name__)

# ---------------- DATABASE CONNECTION ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Shiva@2008",
    database="food_db"
)

cursor = db.cursor()

# ---------------- READ CSV MENU ----------------
menu_list = []

with open(r"D:\COLLEGE\VS Python\food_menu.csv", "r") as file:
    reader = csv.reader(file)
    next(reader)

    for row in reader:
        menu_list.append({
            "food": row[0].strip().lower(),
            "price": float(row[1])
        })

# ---------------- OLD FUNCTION (fallback) ----------------
def predict_time(distance, traffic, items):
    traffic_factor = {"Low": 1, "Medium": 1.5, "High": 2}
    prep_time = len(items) * 5
    return int(prep_time + (distance * traffic_factor[traffic] * 5))


def train_model():
    cursor.execute("SELECT distance, traffic, food, delivery_time FROM orders")
    data = cursor.fetchall()

    if len(data) < 5:
        return None  # not enough data

    X = []
    y = []

    traffic_map = {"Low": 0, "Medium": 1, "High": 2}

    for row in data:
        distance = float(row[0])
        traffic = traffic_map[row[1]]

        items = re.split(r"[,\s]+", row[2].strip().lower())
        items = [i for i in items if i and i not in ["and", "&"]]
        item_count = len(items)

        X.append([distance, traffic, item_count])
        y.append(row[3])

    model = LinearRegression()
    model.fit(X, y)

    return model


home_page = """ 
<!-- SAME HTML (no change) -->
""" + """
<!DOCTYPE html>
<html>
<head>
<title>Food Delivery</title>
<style>
body {
    margin: 0;
    padding: 0;
    font-family: Arial;
    background: url('/static/bg.png') no-repeat center center;
    background-size: cover;
    height: 105vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: white;
    text-align: center;
}
.container {
    background: rgba(255,255,255,0.1);
    width: 360px;
    padding: 20px;
    border-radius: 15px;
    margin-top: 100px;
}
input, select {
    width: 100%;
    padding: 10px;
    margin: 10px 0;
    border-radius: 8px;
    border: none;
}
button {
    padding: 10px;
    width: 100%;
    background: orange;
    border: none;
    color: white;
    border-radius: 8px;
}
a { color: yellow; }
</style>
</head>

<body>
<div class="container">
    <h3>Menu</h3>
    <p>
    {% for item in menu %}
        {{item.food}} - ₹{{item.price}}<br>
    {% endfor %}
    </p>

    <form method="POST">
        <input type="text" name="name" placeholder="Enter Name" required>
        <input type="text" name="food" placeholder="pizza and pasta or burger" required>
        <input type="number" name="distance" placeholder="Distance (km)" required>

        <select name="traffic">
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
        </select>

        <button type="submit">Place Order</button>
    </form>

    <br>
    <a href="/graph">📊 View Graph</a>

    {% if result %}
    <h3>{{result}}</h3>
    {% endif %}
</div>
</body>
</html>
"""

graph_page = """
<!DOCTYPE html>
<html>
<head>
<title>Graph</title>
</head>
<body style="text-align:center">

<h2>Traffic Analysis (0–23 Hours)</h2>
<img src="/static/graph.png" width="800">

<br><br>
<a href="/">⬅ Back</a>

</body>
</html>
"""

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    result = ""

    if request.method == "POST":
        name = request.form["name"]
        food = request.form["food"]
        distance = float(request.form["distance"])
        traffic = request.form["traffic"]

        items = re.split(r"[,\s]+", food.strip().lower())
        items = [i for i in items if i and i not in ["and", "&"]]

        valid_foods = [item["food"] for item in menu_list]

        total_price = 0
        for i in items:
            if i not in valid_foods:
                return render_template_string(home_page, result="Invalid food item!", menu=menu_list)
            for m in menu_list:
                if m["food"] == i:
                    total_price += m["price"]

        model = train_model()

        traffic_map = {"Low": 0, "Medium": 1, "High": 2}
        traffic_val = traffic_map[traffic]
        item_count = len(items)

        if model:
            delivery_time = int(model.predict([[distance, traffic_val, item_count]])[0])
        else:
            delivery_time = predict_time(distance, traffic, items)


        now = datetime.datetime.now()

        cursor.execute("""
        INSERT INTO orders (name, food, distance, traffic, total_price, order_time, delivery_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, food, distance, traffic, total_price, now, delivery_time))
        db.commit()

        result = f"Time: {delivery_time} min | Total: ₹{total_price}"

    return render_template_string(home_page, result=result, menu=menu_list)


@app.route("/graph")
def graph():
    cursor.execute("SELECT order_time, traffic FROM orders")
    data = cursor.fetchall()

    if not data:
        return "<h3>No data available</h3><a href='/'>Back</a>"

    hours = list(range(24))
    low = [0]*24
    medium = [0]*24
    high = [0]*24

    for row in data:
        hour = row[0].hour
        traffic = row[1]

        if traffic == "Low":
            low[hour] += 1
        elif traffic == "Medium":
            medium[hour] += 1
        else:
            high[hour] += 1

    traffic_score = []

    for h in hours:
        total = low[h] + medium[h] + high[h]

        if total == 0:
            traffic_score.append(0)
        else:
            score = (low[h]*0 + medium[h]*1 + high[h]*2) / total
            traffic_score.append(score)

    plt.figure(figsize=(16,9))
    ax = plt.gca()

    ax.plot(hours, traffic_score, marker='o')
    ax.fill_between(hours, traffic_score, 0, alpha=0.2)

    ax.set_xticks([0,3,6,9,12,15,18,21,23])
    ax.set_xlabel("Hours")
    ax.set_yticks([0,1,2])
    ax.set_yticklabels(["Low","Medium","High"])

    plt.title("Traffic Analysis (0–23 Hours)")
    plt.grid(alpha=0.3)

    graph_path = r"D:\COLLEGE\VS Python\Review 3\static\graph.png"

    if not os.path.exists(os.path.dirname(graph_path)):
        os.makedirs(os.path.dirname(graph_path))

    plt.savefig(graph_path)
    plt.close()

    return render_template_string(graph_page)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)