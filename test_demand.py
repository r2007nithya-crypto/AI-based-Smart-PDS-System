from app import get_db_connection
from demand_prediction import predict_demand


connection = get_db_connection()

try:

    print("Testing Stock Demand Prediction...")
    print("--------------------------------")

    for shop_id in [1, 2, 3]:

        for commodity_id in [1, 2, 3]:

            prediction = predict_demand(
                connection,
                commodity_id,
                shop_id
            )

            print(
                f"Shop {shop_id} | "
                f"Commodity {commodity_id} | "
                f"Predicted Demand: {prediction} kg"
            )

finally:

    connection.close()