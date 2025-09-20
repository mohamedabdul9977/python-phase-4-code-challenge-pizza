#!/usr/bin/env python3
from models import db, Restaurant, RestaurantPizza, Pizza
from flask_migrate import Migrate
from flask import Flask, request, make_response, jsonify
from flask_restful import Api, Resource
from sqlalchemy.exc import IntegrityError
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

migrate = Migrate(app, db)

db.init_app(app)

api = Api(app)


@app.route("/")
def index():
    return "<h1>Code challenge</h1>"


# GET /restaurants
@app.get('/restaurants')
def get_restaurants():
    restaurants = Restaurant.query.all()
    # Only id, name, address per spec
    result = [r.to_dict(only=('id', 'name', 'address')) for r in restaurants]
    return jsonify(result), 200


# GET /restaurants/<int:id>
@app.get('/restaurants/<int:id>')
def get_restaurant(id):
    restaurant = db.session.get(Restaurant, id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    # Build the response exactly like the spec:
    data = restaurant.to_dict(only=('id', 'name', 'address'))
    # include restaurant_pizzas with nested pizza (id, name, ingredients) and other fields
    rp_list = []
    for rp in restaurant.restaurant_pizzas:
        rp_list.append({
            "id": rp.id,
            "pizza": rp.pizza.to_dict(only=('id', 'name', 'ingredients')),
            "pizza_id": rp.pizza_id,
            "price": rp.price,
            "restaurant_id": rp.restaurant_id
        })
    data['restaurant_pizzas'] = rp_list
    return jsonify(data), 200


# DELETE /restaurants/<int:id>
@app.delete('/restaurants/<int:id>')
def delete_restaurant(id):
    restaurant = db.session.get(Restaurant, id)
    if not restaurant:
        return jsonify({"error": "Restaurant not found"}), 404

    # Because of cascade, deleting restaurant will remove associated RestaurantPizzas
    db.session.delete(restaurant)
    db.session.commit()
    return ('', 204)  # empty body, proper status code


# GET /pizzas
@app.get('/pizzas')
def get_pizzas():
    pizzas = Pizza.query.all()
    result = [p.to_dict(only=('id', 'name', 'ingredients')) for p in pizzas]
    return jsonify(result), 200


# POST /restaurant_pizzas
@app.post('/restaurant_pizzas')
def create_restaurant_pizza():
    data = request.get_json()
    # expected fields: price, pizza_id, restaurant_id
    try:
        rp = RestaurantPizza(
            price=data.get('price'),
            pizza_id=data.get('pizza_id'),
            restaurant_id=data.get('restaurant_id')
        )
        db.session.add(rp)
        db.session.commit()
    except (ValueError,) as e:
        # validation from @validates
        db.session.rollback()
        return jsonify({"errors": ["validation errors"]}), 400
    except IntegrityError as e:
        db.session.rollback()
        # likely pizza_id or restaurant_id foreign key missing
        return jsonify({"errors": ["Invalid pizza_id or restaurant_id"]}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"errors": [str(e)]}), 400

    # On success, return rp with nested pizza and restaurant (as in spec)
    result = {
        "id": rp.id,
        "pizza": rp.pizza.to_dict(only=('id', 'name', 'ingredients')),
        "pizza_id": rp.pizza_id,
        "price": rp.price,
        "restaurant": rp.restaurant.to_dict(only=('id', 'name', 'address')),
        "restaurant_id": rp.restaurant_id
    }
    return jsonify(result), 201


if __name__ == "__main__":
    app.run(port=5555, debug=True)
