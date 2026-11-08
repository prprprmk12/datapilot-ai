INSERT INTO ecommerce.customers VALUES (1,'Aida','KZ'),(2,'Ivan','KZ'),(3,'Maya','DE'),(4,'Sam','GB');
INSERT INTO ecommerce.products VALUES (1,'Keyboard',100,60),(2,'Mouse',50,20),(3,'Monitor',300,220),(4,'Cable',10,3);
INSERT INTO ecommerce.orders VALUES (1,1,'2026-10-01','paid'),(2,2,'2026-10-10','paid'),(3,3,'2026-10-20','paid'),(4,1,'2026-09-15','paid'),(5,4,'2026-10-22','cancelled'),(6,2,'2026-11-01','pending');
INSERT INTO ecommerce.order_items VALUES (1,1,2,100,60),(1,2,1,50,20),(2,3,1,300,220),(2,4,3,10,3),(3,2,4,50,20),(4,1,1,90,60),(5,3,2,300,220),(6,4,1,10,3);
INSERT INTO ecommerce.payments VALUES (1,1,250,'settled'),(2,2,330,'settled'),(3,3,200,'settled'),(4,4,90,'settled'),(5,5,600,'refunded');
