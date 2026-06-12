"""Product master / catalog seed data."""

PRODUCTS = [
    # Beverages
    {"sku_id": "BEV001", "name": "Sparkling Water 500ml", "category": "Beverages", "brand": "AquaFizz", "package_size": "500ml", "list_price": 1.50, "launch_date": "2021-01-15"},
    {"sku_id": "BEV002", "name": "Orange Juice 1L", "category": "Beverages", "brand": "SunPress", "package_size": "1L", "list_price": 3.20, "launch_date": "2020-06-01"},
    {"sku_id": "BEV003", "name": "Green Tea 12-pack", "category": "Beverages", "brand": "LeafCo", "package_size": "12x330ml", "list_price": 8.99, "launch_date": "2022-03-10"},
    {"sku_id": "BEV004", "name": "Energy Drink 250ml", "category": "Beverages", "brand": "VoltUp", "package_size": "250ml", "list_price": 2.10, "launch_date": "2021-09-01"},
    {"sku_id": "BEV005", "name": "Cold Brew Coffee 330ml", "category": "Beverages", "brand": "BrewHouse", "package_size": "330ml", "list_price": 3.75, "launch_date": "2023-01-20"},
    {"sku_id": "BEV006", "name": "Coconut Water 400ml", "category": "Beverages", "brand": "TropicPure", "package_size": "400ml", "list_price": 2.80, "launch_date": "2022-07-05"},
    {"sku_id": "BEV007", "name": "Lemonade 2L", "category": "Beverages", "brand": "SunPress", "package_size": "2L", "list_price": 2.50, "launch_date": "2020-04-01"},
    {"sku_id": "BEV008", "name": "Sports Drink 750ml", "category": "Beverages", "brand": "VoltUp", "package_size": "750ml", "list_price": 2.25, "launch_date": "2021-05-15"},

    # Snacks
    {"sku_id": "SNK001", "name": "Potato Chips 150g", "category": "Snacks", "brand": "CrunchCo", "package_size": "150g", "list_price": 2.99, "launch_date": "2020-01-01"},
    {"sku_id": "SNK002", "name": "Granola Bar 6-pack", "category": "Snacks", "brand": "NutriBar", "package_size": "6x40g", "list_price": 5.49, "launch_date": "2021-02-14"},
    {"sku_id": "SNK003", "name": "Popcorn 100g", "category": "Snacks", "brand": "CrunchCo", "package_size": "100g", "list_price": 1.99, "launch_date": "2020-08-01"},
    {"sku_id": "SNK004", "name": "Mixed Nuts 200g", "category": "Snacks", "brand": "NutriBar", "package_size": "200g", "list_price": 6.99, "launch_date": "2022-01-10"},
    {"sku_id": "SNK005", "name": "Dark Chocolate 85g", "category": "Snacks", "brand": "CocoBliss", "package_size": "85g", "list_price": 3.49, "launch_date": "2021-11-01"},
    {"sku_id": "SNK006", "name": "Rice Cakes 130g", "category": "Snacks", "brand": "NutriBar", "package_size": "130g", "list_price": 2.79, "launch_date": "2023-03-01"},
    {"sku_id": "SNK007", "name": "Beef Jerky 80g", "category": "Snacks", "brand": "RanchDry", "package_size": "80g", "list_price": 4.99, "launch_date": "2022-05-20"},
    {"sku_id": "SNK008", "name": "Trail Mix 250g", "category": "Snacks", "brand": "NutriBar", "package_size": "250g", "list_price": 5.99, "launch_date": "2020-09-15"},

    # Personal Care
    {"sku_id": "PRC001", "name": "Shampoo 300ml", "category": "Personal Care", "brand": "HairLux", "package_size": "300ml", "list_price": 7.99, "launch_date": "2020-02-01"},
    {"sku_id": "PRC002", "name": "Body Lotion 200ml", "category": "Personal Care", "brand": "SkinSoft", "package_size": "200ml", "list_price": 6.49, "launch_date": "2021-03-15"},
    {"sku_id": "PRC003", "name": "Toothpaste 100g", "category": "Personal Care", "brand": "BrightSmile", "package_size": "100g", "list_price": 3.29, "launch_date": "2020-01-01"},
    {"sku_id": "PRC004", "name": "Deodorant 150ml", "category": "Personal Care", "brand": "FreshGuard", "package_size": "150ml", "list_price": 4.99, "launch_date": "2020-06-10"},
    {"sku_id": "PRC005", "name": "Face Wash 150ml", "category": "Personal Care", "brand": "SkinSoft", "package_size": "150ml", "list_price": 5.99, "launch_date": "2022-09-01"},
    {"sku_id": "PRC006", "name": "Conditioner 300ml", "category": "Personal Care", "brand": "HairLux", "package_size": "300ml", "list_price": 7.49, "launch_date": "2020-02-01"},
    {"sku_id": "PRC007", "name": "Sunscreen SPF50 100ml", "category": "Personal Care", "brand": "SkinSoft", "package_size": "100ml", "list_price": 9.99, "launch_date": "2023-04-01"},

    # Household
    {"sku_id": "HSH001", "name": "Dish Soap 500ml", "category": "Household", "brand": "CleanHome", "package_size": "500ml", "list_price": 3.49, "launch_date": "2020-01-01"},
    {"sku_id": "HSH002", "name": "Laundry Detergent 1kg", "category": "Household", "brand": "WashPro", "package_size": "1kg", "list_price": 9.99, "launch_date": "2020-03-01"},
    {"sku_id": "HSH003", "name": "All-Purpose Cleaner 750ml", "category": "Household", "brand": "CleanHome", "package_size": "750ml", "list_price": 4.29, "launch_date": "2021-01-15"},
    {"sku_id": "HSH004", "name": "Paper Towels 3-roll", "category": "Household", "brand": "SoftSheet", "package_size": "3 rolls", "list_price": 5.99, "launch_date": "2020-01-01"},
    {"sku_id": "HSH005", "name": "Trash Bags 30-pack", "category": "Household", "brand": "WasteSeal", "package_size": "30 bags", "list_price": 7.49, "launch_date": "2020-05-01"},
    {"sku_id": "HSH006", "name": "Fabric Softener 1L", "category": "Household", "brand": "WashPro", "package_size": "1L", "list_price": 6.99, "launch_date": "2021-08-01"},

    # Dairy
    {"sku_id": "DAI001", "name": "Whole Milk 1L", "category": "Dairy", "brand": "FarmFresh", "package_size": "1L", "list_price": 1.89, "launch_date": "2020-01-01"},
    {"sku_id": "DAI002", "name": "Greek Yogurt 500g", "category": "Dairy", "brand": "CreamTop", "package_size": "500g", "list_price": 4.49, "launch_date": "2020-07-01"},
    {"sku_id": "DAI003", "name": "Cheddar Cheese 250g", "category": "Dairy", "brand": "FarmFresh", "package_size": "250g", "list_price": 5.29, "launch_date": "2020-01-01"},
    {"sku_id": "DAI004", "name": "Butter 250g", "category": "Dairy", "brand": "CreamTop", "package_size": "250g", "list_price": 3.99, "launch_date": "2020-02-01"},
    {"sku_id": "DAI005", "name": "Oat Milk 1L", "category": "Dairy", "brand": "PlantBlend", "package_size": "1L", "list_price": 2.99, "launch_date": "2022-01-01"},
    {"sku_id": "DAI006", "name": "Cream Cheese 200g", "category": "Dairy", "brand": "CreamTop", "package_size": "200g", "list_price": 3.49, "launch_date": "2021-04-01"},
]
