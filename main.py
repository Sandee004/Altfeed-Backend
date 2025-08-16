from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from utils import db, create_tables, Animal, Feed, Users
import json, os
from animals_seed import seed_animals
from feed_cattle_seed import feed_cattle_seed
from feed_poultry_seed import feed_poultry_seed
from feed_goat_seed import feed_goat_seed
from datetime import timedelta

app = Flask(__name__)
load_dotenv()

# --- Config ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=12)

db.init_app(app)
jwt = JWTManager(app)
CORS(app)
swagger = Swagger(app)

# ------------------ AUTH ------------------
# ------------------ USER ------------------
@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user
    ---
    tags:
      - User
    parameters:
      - in: body
        name: body
        description: 'User details'
        required: true
        schema:
          type: object
          required:
            - name
            - email
            - farm_type
            - location
            - size
            - phone
            - profile_image_url
          properties:
            name:
              type: string
              example: "Ada Farmer"
            email:
              type: string
              example: "ada@example.com"
            farm_type:
              type: string
              example: "poultry"
            location:
              type: string
              example: "Kaduna, NG"
            size:
              type: string
              example: "500 birds"
            phone:
              type: string
              example: "+2348012345678"
            profile_image_url:
              type: string
              example: "https://example.com/ada.jpg"
    responses:
      201:
        description: User created successfully
      400:
        description: Missing or invalid fields
      409:
        description: Duplicate email
    """
    data = request.get_json() or {}

    name = data.get('name')
    email = data.get('email')
    farm_type = data.get('farm_type')
    location = data.get('location')
    size = data.get('size')
    phone = data.get('phone')

    # Validate required fields
    if not all([name, email, farm_type, location, size, phone]):
        return jsonify({"message": "All fields are required"}), 400

    if Users.query.filter_by(email=email).first():
        return jsonify({"message": "Email already exists. Try logging in."}), 409

    user = Users(
        name=name,
        email=email,
        farm_type=farm_type,
        location=location,
        size=size,
        phone=phone
    )

    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created successfully", "user_id": user.id}), 201


@app.route('/api/user/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    """
    Partially Update User Profile
    ---
    tags:
      - User
    summary: Partially update the authenticated user's profile
    description: Allows the authenticated user to update one or more details like name, email, phone, location, farm_type, etc.
    consumes:
      - application/json
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token as: Bearer <your_token>'
        required: true
        schema:
          type: string
          example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6..."
      - in: body
        name: body
        required: true
        description: At least one field is required
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Ada Farmer Updated"
            email:
              type: string
              example: "ada_new@example.com"
            phone:
              type: string
              example: "+2348098765432"
            farm_type:
              type: string
              example: "cattle"
            location:
              type: string
              example: "Abuja, NG"
            size:
              type: string
              example: "700 cows"
            profile_image_url:
              type: string
              example: "https://example.com/new_ada.jpg"
    responses:
      200:
        description: User updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: User details updated successfully
            user:
              type: object
              properties:
                name:
                  type: string
                email:
                  type: string
                phone:
                  type: string
                farm_type:
                  type: string
                location:
                  type: string
                size:
                  type: string
                profile_image_url:
                  type: string
      400:
        description: No update data provided
      404:
        description: User not found
      409:
        description: Email already in use
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    if not data:
        return jsonify({"message": "No data provided"}), 400

    user = Users.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    updated = False

    # Handle email separately to check duplicates
    if 'email' in data and data['email']:
        existing_email = Users.query.filter(Users.email == data['email'], Users.id != user.id).first()
        if existing_email:
            return jsonify({"message": "Email already in use"}), 409
        user.email = data['email']
        updated = True

    # Generic update for other fields
    for field in ['name', 'phone', 'farm_type', 'location', 'size']:
        if field in data and data[field]:
            setattr(user, field, data[field])
            updated = True

    if not updated:
        return jsonify({"message": "No fields were updated"}), 204

    db.session.commit()

    return jsonify({
        "message": "User details updated successfully",
        "user": {
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "farm_type": user.farm_type,
            "location": user.location,
            "size": user.size,
        }
    }), 200


@app.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user profile
    ---
    tags:
      - User
    security:
      - Bearer: []
    parameters:
      - name: Authorization
        in: header
        description: 'JWT token as: Bearer <your_token>'
        required: true
        schema:
          type: string
          example: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    responses:
      200:
        description: User profile retrieved successfully
      404:
        description: User not found
    """
    user_id = get_jwt_identity()
    user = Users.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404
    
    return jsonify({
        "name": user.name,
        "email": user.email,
        "farm_type": user.farm_type,
        "location": user.location,
        "size": user.size,
        "phone": user.phone,
        "profile_image_url": user.profile_image_url
    }), 200


# ------------------ ANIMALS ------------------
@app.route('/api/animals', methods=['GET'])
def get_animals():
    """
    Get animals
    ---
    tags:
      - Animal
    responses:
      200:
        description: List of animals retrieved successfully
    """
    animals = Animal.query.all()
    return jsonify([{"name": a.name, "icon": a.icon} for a in animals]), 200


@app.route('/feeds/<animal>', methods=['GET'])
def get_feeds(animal):
    """
    Get feeds for animal
    ---
    tags:
      - Feed
    parameters:
      - name: animal
        in: path
        required: true
        description: 'Animal name e.g. cattle'
        schema:
          type: string
    responses:
      200:
        description: List of feeds for the animal
      404:
        description: Animal not found
    """
    animal_obj = Animal.query.filter(db.func.lower(Animal.name) == animal.lower()).first()
    if not animal_obj:
        return jsonify({"message": "Animal not found"}), 404
    feeds = Feed.query.filter_by(animal_id=animal_obj.id).all()
    return jsonify([{"name": f.feed_name, "instructions": json.loads(f.preparation)} for f in feeds]), 200



def seed_database():
    """
    Seed the database with initial animals and feed data.
    This will only insert data if the tables are empty.
    """
    with app.app_context():
        # Ensure tables exist
        create_tables()

        # Seed animals only if table is empty
        if Animal.query.count() == 0:
            seed_animals()
            print("✅ Animals table seeded")

        # Seed feeds only if table is empty
        if Feed.query.count() == 0:
            feed_cattle_seed()
            feed_poultry_seed()
            feed_goat_seed()
            print("✅ Feeds table seeded")

        db.session.commit()


if __name__ == '__main__':
    seed_database()
    app.run(debug=True)
