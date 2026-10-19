import mysql.connector
import pandas as pd
import numpy as np

# ============================================================
# AI-BASED SMART PDS
# STOCK DEMAND PREDICTION
# ============================================================


# ============================================================
# 1. DATABASE CONNECTION
# ============================================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya123@2007",
        database="smart_pds"
    )


# ============================================================
# 2. GET HISTORICAL DISTRIBUTION DATA
# ============================================================

def get_distribution_data(shop_id, commodity_id):

    connection = get_db_connection()

    query = """
        SELECT
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


# ============================================================
# 3. PREDICT NEXT MONTH DEMAND
# ============================================================

def predict_demand(shop_id, commodity_id):

    df = get_distribution_data(
        shop_id,
        commodity_id
    )

    # No data
    if df.empty:
        return None

    # Minimum 3 historical records required
    if len(df) < 3:
        return None

    # Convert quantity values to numbers
    quantities = (
        df["quantity_kg"]
        .astype(float)
        .to_numpy()
    )

    # Create time sequence
    x = np.arange(
        1,
        len(quantities) + 1
    )

    # Calculate linear trend
    slope, intercept = np.polyfit(
        x,
        quantities,
        1
    )

    # Predict next month
    next_month = len(quantities) + 1

    predicted_quantity = (
        slope * next_month
    ) + intercept

    # Demand cannot be negative
    predicted_quantity = max(
        0,
        predicted_quantity
    )

    return round(
        float(predicted_quantity),
        2
    )


# ============================================================
# 4. SAVE PREDICTION TO DATABASE
# ============================================================

def save_prediction(
    shop_id,
    commodity_id,
    predicted_quantity
):

    connection = get_db_connection()

    cursor = connection.cursor()

    # Next month
    prediction_month = (
        pd.Timestamp.today()
        .replace(day=1)
        + pd.DateOffset(months=1)
    ).date()

    # Prototype confidence indicator
    confidence_score = 80.00

    model_name = "Linear Trend Model"

    query = """
        INSERT INTO ai_predictions
        (
            shop_id,
            commodity_id,
            prediction_month,
            predicted_quantity_kg,
            confidence_score,
            model_name
        )
        VALUES
        (%s, %s, %s, %s, %s, %s)
    """

    values = (
        shop_id,
        commodity_id,
        prediction_month,
        predicted_quantity,
        confidence_score,
        model_name
    )

    cursor.execute(
        query,
        values
    )

    connection.commit()

    cursor.close()

    connection.close()


# ============================================================
# 5. MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("AI-BASED SMART PDS")
    print("STOCK DEMAND PREDICTION")
    print("=" * 60)

    # --------------------------------------------------------
    # Demo shop and commodity
    # --------------------------------------------------------

    shop_id = 1
    commodity_id = 1

    print()
    print("Shop ID      :", shop_id)
    print("Commodity ID :", commodity_id)

    print()
    print("Loading historical distribution data...")

    # --------------------------------------------------------
    # Load historical data
    # --------------------------------------------------------

    historical_data = get_distribution_data(
        shop_id,
        commodity_id
    )

    # --------------------------------------------------------
    # Check data
    # --------------------------------------------------------

    if historical_data.empty:

        print()
        print("No historical distribution data found.")

    elif len(historical_data) < 3:

        print()
        print("Not enough historical data.")
        print("At least 3 records are required.")

    else:

        print()
        print("Historical Distribution Records:")
        print("-" * 60)

        print(
            historical_data.to_string(
                index=False
            )
        )

        # ----------------------------------------------------
        # Generate prediction
        # ----------------------------------------------------

        prediction = predict_demand(
            shop_id,
            commodity_id
        )

        print()
        print("-" * 60)

        print(
            "Predicted Next Month Demand :",
            prediction,
            "KG"
        )

        # ----------------------------------------------------
        # Save prediction
        # ----------------------------------------------------

        save_prediction(
            shop_id,
            commodity_id,
            prediction
        )

        print()
        print(
            "Prediction saved successfully."
        )

    print()
    print("=" * 60)
    print("PROCESS COMPLETED")
    print("=" * 60)