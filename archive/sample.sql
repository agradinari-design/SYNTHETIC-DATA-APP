CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    created_at TIMESTAMP
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    total_amount DECIMAL(10,2),
    status VARCHAR(20)
);
