import mysql.connector
import pandas as pd
import numpy as np


def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya123@2007",
        database="smart_pds"
    )

    return connection


def get_distribution_data(shop_id, commodity_id):

    connection = get_db_connection()

    query = """
        SELECT
            stock_transaction_id,
            transaction_date,
            quantity_kg
        FROM stock_transactions
        WHERE shop_id = %s
          AND commodity_id = %s
          AND transaction_type = 'DISTRIBUTED'
        ORDER BY transaction_date ASC
    """

    df = pd.read_sql(
        query,
        connection,
        params=(shop_id, commodity_id)
    )

    connection.close()

    return df


def detect_anomaly(shop_id, commodity_id):

    df = get_distribution_data(
        shop_id,
        commodity_id
    )

    if df.empty:
        return None

    if len(df) < 3:
        return None

    quantities = (
        df["quantity_kg"]
        .astype(float)
        .to_numpy()
    )

    mean_quantity = np.mean(quantities)

    standard_deviation = np.std(quantities)

    latest_quantity = quantities[-1]

    latest_transaction_id = 1

    if standard_deviation == 0:

        anomaly_score = 0

    else:

        anomaly_score = (
            abs(latest_quantity - mean_quantity)
            / standard_deviation
        )

    if anomaly_score >= 2:

        anomaly_type = "UNUSUAL_DISTRIBUTION_PATTERN"

        review_status = "PENDING_REVIEW"

        description = (
            f"Latest distribution of {latest_quantity:.2f} KG "
            f"is unusually different from the historical average "
            f"of {mean_quantity:.2f} KG."
        )

    else:

        anomaly_type = "NORMAL_DISTRIBUTION_PATTERN"

        review_status = "REVIEWED"

        description = (
            f"Latest distribution of {latest_quantity:.2f} KG "
            f"is within the expected historical distribution pattern. "
            f"Historical average is {mean_quantity:.2f} KG."
        )

    return {
        "transaction_id": latest_transaction_id,
        "anomaly_type": anomaly_type,
        "anomaly_score": round(
            float(anomaly_score), 4
        ),
        "description": description,
        "review_status": review_status
    }


def save_anomaly_result(shop_id, result):

    connection = get_db_connection()

    cursor = connection.cursor()

    query = """
        INSERT INTO anomaly_results
        (
            shop_id,
            transaction_id,
            anomaly_type,
            anomaly_score,
            description,
            detection_date,
            review_status
        )
        VALUES
        (%s, %s, %s, %s, %s, NOW(), %s)
    """

    values = (
        shop_id,
        result["transaction_id"],
        result["anomaly_type"],
        result["anomaly_score"],
        result["description"],
        result["review_status"]
    )

    cursor.execute(query, values)

    connection.commit()

    cursor.close()

    connection.close()


if __name__ == "__main__":

    print("=" * 60)
    print("AI-BASED SMART PDS")
    print("ANOMALY DETECTION")
    print("=" * 60)

    shop_id = 1
    commodity_id = 1

    result = detect_anomaly(
        shop_id,
        commodity_id
    )

    if result is None:

        print()
        print("Not enough historical data.")

    else:

        print()
        print("Anomaly Type:",
              result["anomaly_type"])

        print("Anomaly Score:",
              result["anomaly_score"])

        print("Transaction ID:",
              result["transaction_id"])

        print("Review Status:",
              result["review_status"])

        print()
        print("Description:")
        print(result["description"])

        save_anomaly_result(
            shop_id,
            result
        )

        print()
        print("Anomaly result saved successfully.")