from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from pymongo import MongoClient
from bcrypt import hashpw, gensalt, checkpw
from werkzeug.utils import secure_filename
import os, random, csv, io, dotenv

app = Flask(__name__)

dotenv.load_dotenv()

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

client = MongoClient(os.getenv('DATABASE_URI'))

db = client['wt_project']
products_collection = db["products"]
accounts_collection = db["accounts"]
recipes_collection = db["recipes"]

def create_admin_account():
    if accounts_collection.count_documents({"username": "admin"}) == 0:
        admin_user = {
            "username": "admin",
            "password": hashpw("admin_password".encode('utf-8'), gensalt()),
            "role": "admin"
        }
        accounts_collection.insert_one(admin_user)

create_admin_account()

@app.route('/')
def home():
    recipes = list(recipes_collection.find({}, {'_id': 0}))
    products = list(products_collection.find({}, {'_id': 0}))
    
    if recipes:
        recipe_of_the_day = random.choice(recipes)
    else:
        recipe_of_the_day = None

    if products:
        best_offer = random.choice(products)
    else:
        best_offer = None

    return render_template('home.html', recipe_of_the_day=recipe_of_the_day, best_offer=best_offer)


@app.route('/products')
def products():
    products = list(products_collection.find({}, {'_id': 0}))
    return render_template('products.html', products=products)

@app.route('/recipes')
def recipes():
    recipes = list(recipes_collection.find({}, {'_id': 0}))
    
    for recipe in recipes:
        image_path = os.path.join('static', 'img', 'recipes', recipe.get('image', ''))
        recipe['image_exists'] = os.path.exists(image_path) if 'image' in recipe else False
    
    return render_template('recipes.html', recipes=recipes)

@app.route('/recipes/<recipe_id>')
def recipe_detail(recipe_id):
    print(f"Recipe ID: {recipe_id}")
    recipe = recipes_collection.find_one({"name": recipe_id})
    if not recipe:
        flash("Recipe not found", "danger")
        return redirect(url_for('recipes'))
    return render_template('recipe_detail.html', recipe=recipe)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = accounts_collection.find_one({"username": username})
        if user and checkpw(password.encode('utf-8'), user['password']):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('account'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('account'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashpw(password.encode('utf-8'), gensalt())
        if accounts_collection.find_one({"username": username}):
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        accounts_collection.insert_one({'username': username, 'password': hashed_password, 'role': "user"})
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/account')
def account():
    if 'username' not in session:
        return render_template('account.html')
    
    user = accounts_collection.find_one({"username": session['username']})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('home'))

    cart_products = []
    total_price = 0
    if 'cart' in user:
        for product_name in user['cart']:
            product = products_collection.find_one({"name": product_name})
            if product:
                cart_products.append(product)
                total_price += product['price']

    return render_template(
        'account.html',
        cart=cart_products,
        total_price=total_price
    )

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin')
def admin():
    if 'username' not in session:
        flash('You must be logged in to access the admin page.', 'danger')
        return redirect(url_for('login'))

    username = session['username']
    user = accounts_collection.find_one({"username": username})

    if user and user.get('role') == 'admin':
        return render_template('admin.html')
    else:
        flash('You do not have permission to access the admin page.', 'danger')
        return redirect(url_for('home'))

@app.route('/api/products', methods=['GET'])
def get_products():
    products = list(products_collection.find({}, {'_id': 0}))
    return jsonify(products), 200

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.form
    name = data.get('name')
    price = float(data.get('price'))
    
    image_filename = 'default.png'

    if 'image' in request.files:
        image = request.files['image']
        
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join('static', 'img', 'products', image_filename))
        else:
            return jsonify({'error': 'Invalid image format'}), 400

    product_data = {
        'name': name,
        'price': price,
        'image': image_filename,
    }

    products_collection.insert_one(product_data)

    return jsonify({'message': 'Product added successfully!'}), 201

@app.route('/api/products/<string:name>', methods=['PUT'])
def update_product(name):
    data = request.json
    if not data:
        return jsonify({'error': 'Invalid data'}), 400
    result = products_collection.update_one({"name": name}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify({'message': 'Product updated successfully!'}), 200

@app.route('/api/products/<string:name>', methods=['DELETE'])
def delete_product(name):
    result = products_collection.delete_one({"name": name})
    if result.deleted_count == 0:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify({'message': 'Product deleted successfully!'}), 200

@app.route('/add_to_cart/<product_name>', methods=['POST'])
def add_to_cart(product_name):
    if 'username' not in session:
        flash("Please log in to add items to your shopping list.", "warning")
        return redirect(url_for('login'))

    user = accounts_collection.find_one({"username": session['username']})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('products'))

    accounts_collection.update_one(
        {"username": session['username']},
        {"$addToSet": {"cart": product_name}} 
    )

    flash(f"{product_name} has been added to your shopping list.", "success")
    return redirect(url_for('products'))

@app.route('/api/products/<string:name>/image', methods=['PUT'])
def update_product_image(name):
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    image = request.files['image']
    
    if image:
        image_filename = secure_filename(image.filename)
        
        image.save(os.path.join('static', 'img', 'products', image_filename))
        
        products_collection.update_one(
            {'name': name},
            {'$set': {'image': image_filename}}
        )
        
        return jsonify({'message': 'Product image updated successfully!'}), 200
    else:
        return jsonify({'error': 'Invalid image format'}), 400

@app.route('/add_ingredients_to_cart', methods=['POST'])
def add_ingredients_to_cart():
    if 'username' not in session:
        flash("Please log in to add ingredients to your shopping list.", "warning")
        return redirect(url_for('login'))

    data = request.form.get('ingredients')
    
    if not data:
        flash("No ingredients selected.", "error")
        return redirect(request.referrer)

    ingredients_list = [ingredient.strip() for ingredient in data.split(',')]

    available_products = products_collection.find(
        {'name': {'$in': ingredients_list}}, 
        {'_id': 0, 'name': 1}
    )
    available_product_names = {product['name'] for product in available_products}

    missing_ingredients = [ingredient for ingredient in ingredients_list if ingredient not in available_product_names]

    user = accounts_collection.find_one({"username": session['username']})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('home'))

    for ingredient in ingredients_list:
        if ingredient in available_product_names:
            accounts_collection.update_one(
                {"username": session['username']},
                {"$addToSet": {"cart": ingredient}}
            )
            flash(f"{ingredient} has been added to your shopping list.", "success")

    if missing_ingredients:
        missing_ingredients_msg = '<br>'.join(missing_ingredients)
        flash(f"The following items are not part of our offer: <br>{missing_ingredients_msg}", "warning")

    return redirect(request.referrer)

@app.route('/remove_from_cart/<product_name>', methods=['POST'])
def remove_from_cart(product_name):
    if 'username' not in session:
        flash("Please log in to modify your shopping list.", "warning")
        return redirect(url_for('login'))

    user = accounts_collection.find_one({"username": session['username']})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('home'))

    accounts_collection.update_one(
        {"username": session['username']},
        {"$pull": {"cart": product_name}}
    )

    flash(f"{product_name} has been removed from your shopping list.", "success")
    return redirect(url_for('account'))

@app.route('/api/products/csv', methods=['POST'])
def upload_csv():
    if 'csv' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['csv']
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file type. Only CSV files are allowed.'}), 400

    try:
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        products_to_insert = []

        for row in csv_reader:
            name = row['ProductName'].strip()
            price = float(row['Price'].strip())
            product_data = {
                'name': name,
                'price': price,
                'image': 'default.png',
            }
            products_to_insert.append(product_data)

        if products_to_insert:
            products_collection.insert_many(products_to_insert)
            return jsonify({'message': f'{len(products_to_insert)} products added successfully!'}), 201
        else:
            return jsonify({'error': 'No valid product data found in CSV.'}), 400

    except Exception as e:
        print(f"Error processing CSV: {e}")
        return jsonify({'error': 'An error occurred while processing the CSV file.'}), 500
    

if __name__ == "__main__":
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        client.close()