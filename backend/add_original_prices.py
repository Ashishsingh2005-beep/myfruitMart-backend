import json
import random

# Read the products
with open('product.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Add originalPrice to each product (15-40% higher than current price)
for product in products:
    if 'originalPrice' not in product:
        current_price = product['price']
        # Calculate original price (20-35% more than current price)
        discount_percent = random.randint(20, 35)
        original_price = int(current_price * (100 + discount_percent) / 100)
        product['originalPrice'] = original_price

# Save back
with open('product.json', 'w', encoding='utf-8') as f:
    json.dump(products, f, indent=4, ensure_ascii=False)

print(f"Added originalPrice to {len(products)} products!")
print("Sample products:")
for i, p in enumerate(products[:5]):
    discount = int((1 - p['price']/p['originalPrice']) * 100)
    print(f"  {p['name']}: Rs.{p['originalPrice']} -> Rs.{p['price']} ({discount}% OFF)")
