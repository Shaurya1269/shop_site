create table users(
    id serial primary key,
    name varchar(100) not null,
    email varchar(100) not null unique,
    password_hash text not null,
    created_at timestamp default current_timestamp
);

create table shops(
    id serial primary key,
    user_id integer not null,
    shop_name varchar(100) not null,
    slug varchar(150) unique not null,
    created_at timestamp default current_timestamp,
    foreign key (user_id) references users(id) on delete cascade
);

create table products(
    id serial primary key,
    shop_id integer not null,
    name varchar(200) not null,
    description text,
    price numeric(10, 2) not null,
    stock integer default 0,
    image_url text,
    created_at timestamp default current_timestamp,
    foreign key (shop_id) references shops(id) on delete cascade
);

create table orders(
    id serial primary key,
    shop_id integer not null,
    customer_name varchar(100) not null,
    phone varchar(20) not null,
    address text not null,
    created_at timestamp default current_timestamp,
    foreign key (shop_id) references shops(id) on delete cascade
);


create table order_items(
    id serial primary key,
    order_id integer not null,
    product_id integer not null,
    quantity integer not null,
    price numeric(10, 2) not null,
    foreign key (order_id) references orders(id) on delete cascade,
    foreign key (product_id) references products(id) on delete cascade
)