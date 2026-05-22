from flask import Flask, render_template, request
import mysql.connector
import pandas as pd
import re

app = Flask(__name__)

data = pd.read_csv(r"C:\Users\shree\food_menu.csv")
menu = dict(zip(data["food"], data["price"]))

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Shiva@2008",
    database="clg"
)

cursor = db.cursor()


def extract_foods(sentence):
    sentence = sentence.lower()
    foods = []

    for food in menu.keys():
        if re.search(food, sentence):
            foods.append(food)

    return foods


def calculate_delivery_time(distance, traffic):
    base_time = distance * 2

    if traffic == "low":
        delay = 5
    elif traffic == "medium":
        delay = 10
    elif traffic == "high":
        delay = 20
    else:
        delay = 0

    return base_time + delay


def delivery_charge(traffic):
    if traffic == "medium":
        return 20
    elif traffic == "high":
        return 40
    else:
        return 0


class Order:

    def __init__(self, customer, sentence, distance, traffic):

        self.customer = customer
        self.foods = extract_foods(sentence)
        self.distance = distance
        self.traffic = traffic
        self.time = calculate_delivery_time(distance, traffic)

    def calculate_bill(self):

        total = 0

        for food in self.foods:
            total += menu[food]

        charge = delivery_charge(self.traffic)
        final_total = total + charge

        return total, charge, final_total

    def save_order(self):

        total, charge, final_total = self.calculate_bill()

        foods_string = ", ".join(self.foods)

        sql = """INSERT INTO orders 
        (customer_name, food_item, distance, traffic, estimated_time, total_bill) 
        VALUES (%s,%s,%s,%s,%s,%s)"""

        values = (
            self.customer,
            foods_string,
            self.distance,
            self.traffic,
            self.time,
            final_total
        )

        cursor.execute(sql, values)
        db.commit()


@app.route("/")
def home():
    return render_template("index.html", menu=menu)


@app.route("/order", methods=["POST"])
def order():

    name = request.form["name"]
    sentence = request.form["order"]
    distance = int(request.form["distance"])
    traffic = request.form["traffic"]

    order = Order(name, sentence, distance, traffic)

    if len(order.foods) == 0:
        return "No valid food items detected."

    order.save_order()

    total, charge, final_total = order.calculate_bill()

    return render_template(
        "bill.html",
        name=name,
        foods=order.foods,
        menu=menu,
        total=total,
        charge=charge,
        final_total=final_total,
        distance=distance,
        traffic=traffic,
        time=order.time
    )


if __name__ == "__main__":
    app.run(debug=True)