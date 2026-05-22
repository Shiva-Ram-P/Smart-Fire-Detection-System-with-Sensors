from flask import Flask, render_template, request
import mysql.connector
import pandas as pd
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import random

app = Flask(__name__)

# ---------------- MENU ----------------
data = pd.read_csv(r"D:\COLLEGE\VS Python\food_menu.csv")
menu = dict(zip(data["food"], data["price"]))

# ---------------- DB ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Shiva@2008",
    database="clg"
)

# ---------------- FUNCTIONS ----------------
def extract_foods(sentence):
    sentence = sentence.lower()
    return [food for food in menu if re.search(rf"\b{food}\b", sentence)]

def calculate_delivery_time(distance, traffic):
    return distance * 3 + {"low": 5, "medium": 10, "high": 20}[traffic]

def delivery_charge(traffic):
    return {"low": 0, "medium": 20, "high": 40}[traffic]

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index1.html", menu=menu)

# ---------------- ORDER ----------------
@app.route("/order", methods=["POST"])
def order():
    name = request.form["name"]
    sentence = request.form["order"]
    distance = int(request.form["distance"])
    traffic = request.form["traffic"]

    foods = extract_foods(sentence)

    if not foods:
        return "❌ No valid food items detected"

    total = sum(menu[f] for f in foods)
    charge = delivery_charge(traffic)
    final_total = total + charge
    time = calculate_delivery_time(distance, traffic)

    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO orders1 
        (customer_name, food_item, distance, traffic, estimated_time, total_bill) 
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (name, ", ".join(foods), distance, traffic, time, final_total))
    db.commit()

    return render_template("bill1.html", **locals(), menu=menu)

# ---------------- ANALYTICS (FIXED) ----------------
@app.route("/analytics")
def analytics():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT order_time, traffic FROM orders1")
        data = cursor.fetchall()

        if not data:
            return "❌ No data available. Place some orders first."

        # Convert to DataFrame manually (SAFEST METHOD)
        df = pd.DataFrame(data, columns=["order_time", "traffic"])

        df["order_time"] = pd.to_datetime(df["order_time"])
        df["hour"] = df["order_time"].dt.hour

        traffic_map = {"low": 1, "medium": 2, "high": 3}
        df["traffic_level"] = df["traffic"].map(traffic_map)

        avg = df.groupby("hour")["traffic_level"].mean()

        # -------- SMOOTH GRAPH --------
        plt.figure(figsize=(6,4))

        plt.plot(avg.index, avg.values, linewidth=2)
        plt.fill_between(avg.index, avg.values, alpha=0.1)

        plt.xticks(range(0,24,2))
        plt.xlabel("Time (Hours)")
        plt.ylabel("Traffic Level")
        plt.title("Traffic Trend")
        plt.grid(alpha=0.3)

        # Save graph
        if not os.path.exists("static"):
            os.makedirs("static")

        plt.savefig("static/traffic1.png", bbox_inches='tight')
        plt.close()

        return render_template("analytics1.html", rand=random.randint(1,10000))

    except Exception as e:
        return f"❌ ERROR: {str(e)}"

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)