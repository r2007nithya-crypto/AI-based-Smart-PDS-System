import pandas as pd
from sklearn.linear_model import LinearRegression


def prepare_demand_data(connection, shop_id=None):

    query = """
        SELECT
            DATE_FORMAT(transaction_date, '%Y-%m') AS month,
            commodity_id,
            SUM(
                CASE
                    WHEN transaction_type = 'DISTRIBUTED'
                    THEN quantity_kg
                    ELSE 0
                END
            ) AS distributed_quantity
        FROM stock_transactions
        WHERE 1 = 1
    """

    params = []

    if shop_id is not None:
        query += " AND shop_id = %s"
        params.append(shop_id)

    query += """
        GROUP BY
            DATE_FORMAT(transaction_date, '%Y-%m'),
            commodity_id
        ORDER BY
            month,
            commodity_id
    """

    df = pd.read_sql(
        query,
        connection,
        params=params
    )

    if df.empty:
        return pd.DataFrame()

    df["month"] = pd.to_datetime(df["month"])

    df["distributed_quantity"] = pd.to_numeric(
        df["distributed_quantity"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "month",
            "distributed_quantity"
        ]
    )

    return df


def predict_demand(
    connection,
    commodity_id,
    shop_id=1
):

    query = """
        SELECT
            DATE_FORMAT(transaction_date, '%Y-%m') AS month,
            SUM(
                CASE
                    WHEN transaction_type = 'DISTRIBUTED'
                    THEN quantity_kg
                    ELSE 0
                END
            ) AS demand
        FROM stock_transactions
        WHERE shop_id = %s
          AND commodity_id = %s
        GROUP BY
            DATE_FORMAT(transaction_date, '%Y-%m')
        ORDER BY month
    """

    df = pd.read_sql(
        query,
        connection,
        params=(
            shop_id,
            commodity_id
        )
    )

    if df.empty:
        return None

    df["month"] = pd.to_datetime(
        df["month"]
    )

    df["demand"] = pd.to_numeric(
        df["demand"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "month",
            "demand"
        ]
    )

    # Need at least 3 months of history
    if len(df) < 3:
        return None

    # Convert months into sequential numbers
    df["month_number"] = range(
        1,
        len(df) + 1
    )

    X = df[["month_number"]]
    y = df["demand"]

    # Train Linear Regression model
    model = LinearRegression()

    model.fit(
        X,
        y
    )

    # Predict next month
    next_month = len(df) + 1

    next_month_data = pd.DataFrame(
        {
            "month_number": [next_month]
        }
    )

    prediction = model.predict(
        next_month_data
    )[0]

    # Never return a negative demand
    prediction = max(
        0,
        prediction
    )

    return round(
        float(prediction),
        2
    )