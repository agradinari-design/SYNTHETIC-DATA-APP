CREATE TABLE restaurants (
    restaurant_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    cuisine_type VARCHAR(50),
    address VARCHAR(200)
);

CREATE TABLE menu_items (
    item_id SERIAL PRIMARY KEY,
    restaurant_id INT REFERENCES restaurants(restaurant_id),
    item_name VARCHAR(100),
    price DECIMAL(8,2)
);

CREATE TABLE reviews (
    review_id SERIAL PRIMARY KEY,
    restaurant_id INT REFERENCES restaurants(restaurant_id),
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    review_date DATE
);
