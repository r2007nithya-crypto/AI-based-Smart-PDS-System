import mysql.connector
import pandas as pd


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya123@2007",
        database="smart_pds"
    )


def get_shop_stock_data():
    connection = get_db_connection()

    query = """
        SELECT
            ss.shop_id,
            fps.shop_code,
            fps.shop_name,
            ss.commodity_id,
            c.commodity_name,
            ss.quantity_kg,
            ss.minimum_threshold_kg
        FROM shop_stock ss
        JOIN fair_price_shops fps
            ON ss.shop_id = fps.shop_id
        JOIN commodities c
            ON ss.commodity_id = c.commodity_id
        WHERE fps.is_active = 1
    """

    df = pd.read_sql(query, connection)
    connection.close()

    return df


def get_complaint_data():
    connection = get_db_connection()

    query = """
        SELECT
            shop_id,
            COUNT(*) AS complaint_count
        FROM complaints
        GROUP BY shop_id
    """

    df = pd.read_sql(query, connection)
    connection.close()

    return df


def generate_recommendations():
    stock_df = get_shop_stock_data()
    complaint_df = get_complaint_data()

    recommendations = []

    if not stock_df.empty:

        for _, row in stock_df.iterrows():

            shop_id = int(row["shop_id"])
            shop_name = row["shop_name"]
            commodity_name = row["commodity_name"]
            quantity = float(row["quantity_kg"])
            threshold = float(row["minimum_threshold_kg"])

            # Stock shortage recommendation
            if quantity < threshold:

                recommendations.append({
                    "recommendation_type": "STOCK",
                    "district_id": None,
                    "shop_id": shop_id,
                    "title": "Low Stock Alert",
                    "recommendation_text":
                        f"{shop_name} has low {commodity_name} stock "
                        f"({quantity:.2f} KG). Consider replenishing stock.",
                    "priority": "HIGH"
                })

            # Stock monitoring recommendation
            elif quantity <= threshold * 1.5:

                recommendations.append({
                    "recommendation_type": "STOCK",
                    "district_id": None,
                    "shop_id": shop_id,
                    "title": "Stock Monitoring Required",
                    "recommendation_text":
                        f"{shop_name} has {commodity_name} stock of "
                        f"{quantity:.2f} KG, which is approaching the "
                        f"reorder level.",
                    "priority": "MEDIUM"
                })

    # Complaint-based recommendations
    if not complaint_df.empty:

        for _, row in complaint_df.iterrows():

            shop_id = int(row["shop_id"])
            complaint_count = int(row["complaint_count"])

            if complaint_count >= 5:

                recommendations.append({
                    "recommendation_type": "COMPLAINT",
                    "district_id": None,
                    "shop_id": shop_id,
                    "title": "High Complaint Activity",
                    "recommendation_text":
                        f"Shop {shop_id} has received {complaint_count} "
                        f"complaints. Administrative review is recommended.",
                    "priority": "HIGH"
                })

            elif complaint_count >= 3:

                recommendations.append({
                    "recommendation_type": "COMPLAINT",
                    "district_id": None,
                    "shop_id": shop_id,
                    "title": "Complaint Monitoring",
                    "recommendation_text":
                        f"Shop {shop_id} has received {complaint_count} "
                        f"complaints. Monitor complaint trends and service quality.",
                    "priority": "MEDIUM"
                })

    return recommendations


def save_recommendations(recommendations):

    if not recommendations:
        return

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        INSERT INTO ai_recommendations
        (
            recommendation_type,
            district_id,
            shop_id,
            title,
            recommendation_text,
            priority,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    for recommendation in recommendations:

        cursor.execute(
            query,
            (
                recommendation["recommendation_type"],
                recommendation["district_id"],
                recommendation["shop_id"],
                recommendation["title"],
                recommendation["recommendation_text"],
                recommendation["priority"],
                "NEW"
            )
        )

    connection.commit()
    cursor.close()
    connection.close()


if __name__ == "__main__":

    print("=" * 60)
    print("AI-BASED SMART PDS")
    print("AI RECOMMENDATION ENGINE")
    print("=" * 60)

    recommendations = generate_recommendations()

    if not recommendations:

        print()
        print("No recommendations generated.")

    else:

        print()
        print("GENERATED RECOMMENDATIONS")
        print()

        for recommendation in recommendations:

            print("Type:",
                  recommendation["recommendation_type"])

            print("Shop:",
                  recommendation["shop_id"])

            print("Title:",
                  recommendation["title"])

            print("Priority:",
                  recommendation["priority"])

            print("Recommendation:",
                  recommendation["recommendation_text"])

            print("-" * 60)

        save_recommendations(recommendations)

        print()
        print("Recommendations saved successfully.")