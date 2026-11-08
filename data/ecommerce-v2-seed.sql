-- Load after 001_schema.sql into a separate, empty database.
BEGIN;
INSERT INTO ecommerce.customers VALUES
    (1,'Dana','KZ'),(2,'Arman','KZ'),(3,'Lea','DE'),(4,'Nora','US'),
    (5,'Ali','TR'),(6,'Grace','GB'),(7,'Eva','DE'),(8,'Sofia','RU');

INSERT INTO ecommerce.products VALUES
    (1,'Dock',120,65),(2,'Charger',30,12),(3,'Screen',450,310),
    (4,'Adapter',15,7),(5,'Headset',75,40),(6,'Camera',95,60),
    (7,'Stand',30,18),(8,'Pouch',10,4);

INSERT INTO ecommerce.orders VALUES
    (1,1,'2026-09-04','paid'),(2,2,'2026-10-01','paid'),
    (3,1,'2026-10-10','pending'),(4,3,'2026-10-10','paid'),
    (5,4,'2026-10-20','paid'),(6,5,'2026-11-01','cancelled'),
    (7,5,'2026-11-03','paid'),(8,2,'2026-11-14','paid'),
    (9,7,'2026-12-01','pending');

INSERT INTO ecommerce.order_items VALUES
    (1,1,2,110,65),(1,4,1,14,7),(2,2,3,28,12),
    (3,8,2,9,4),(4,3,1,410,300),(5,5,2,70,38),
    (6,6,1,95,60),(7,2,2,30,12),(7,7,1,28,18),
    (8,1,1,118,65),(8,6,2,92,60),(9,7,1,30,18);

INSERT INTO ecommerce.payments VALUES
    (1,1,150,'settled'),(2,1,84,'settled'),(3,2,84,'settled'),
    (4,4,410,'settled'),(5,5,140,'settled'),(6,5,20,'refunded'),
    (7,6,95,'refunded'),(8,7,88,'settled'),(9,8,302,'settled');
COMMIT;
