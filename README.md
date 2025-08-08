# Project for Web Technologies course at University

### Description
This web app allows users to browse supermarket products, create a shopping list, and view recipe recommendations. Users can add recipe ingredients automatically to their shopping list based on available store items. This is the most convenient approach for the usual grocery shoppers and also for home cooks.

### Core functionalities
* Create account for exclusive benefits.
* Browse and search products.
* Add products/ingredients to a shopping list.
* View recipes and add ingredients automatically to the shopping list.
* Admin can control the products in the database manually adding or using a CSV for large amounts of data.

### Technology stack
* Backend: Python (Flask)
* Database: MongoDB
* Frontend: HTML, CSS, JavaScript

### Installation guide
1. **Clone the repository**
    ```bash
    git clone https://github.com/denisghera/grocery-web-app.git
    cd grocery-web-app
    ```

2. **Install Python dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3. **Set up environment variables**
    - Create a `.env` file in the project root with the following content:
      ```
      SECRET_KEY = 'your_secret_key_here'
      MONGODB_URI = 'mongodb+srv://<db-username>:<db-password>@<cluster-url>/?retryWrites=true&w=majority&appName=<cluster-name>'
      ```
    - Ensure your MongoDB cluster has a database named `wt_project` and the collections: `products`, `accounts`, `recipes`.

4. **Run the application**
    ```bash
    flask run
    ```

5. **Add your data**
    - Access the hidden page `/admin` and start adding products
        > **Note:** Predefined product images are stored in `/static/img/products/`. If no image is selected, a default one will be used.
    - For now, **recipes** need to be manually added in the Database, containing a `name`, `title`, optional `image` (filename), `description`, a list of `ingredients`, and a list of `steps`
        > **Note:** Similar to product, there are some predefined recipe images stored in `/static/img/recipes/`, and a default one as well.