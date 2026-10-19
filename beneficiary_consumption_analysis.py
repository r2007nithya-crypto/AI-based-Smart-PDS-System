import mysql.connector
import pandas as pd


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya123@2007",
        database="smart_pds"
    )


def get_consumption_data():
    connection = get_db_connection()

    query = """
        SELECT
            rt.ration_card_id,
            rt.commodity_id,
            c.commodity_name,
            rt.quantity_kg,
            rt.transaction_date
        FROM ration_transactions rt
        JOIN commodities c
            ON rt.commodity_id = c.commodity_id
        WHERE rt.status = 'COMPLETED'
        ORDER BY rt.transaction_date ASC
    """

    df = pd.read_sql(query, connection)
    connection.close()

    return df


def analyze_consumption():
    df = get_consumption_data()

    if df.empty:
        return None

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    # Total consumption by beneficiary and commodity
    beneficiary_analysis = (
        df.groupby(
            ["ration_card_id", "commodity_id", "commodity_name"]
        )["quantity_kg"]
        .sum()
        .reset_index(name="total_consumption")
        .sort_values("total_consumption", ascending=False)
    )

    # Monthly consumption
    monthly_analysis = (
        df.assign(
            consumption_month=df["transaction_date"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby(
            ["ration_card_id", "commodity_name", "consumption_month"]
        )["quantity_kg"]
        .sum()
        .reset_index(name="total_consumption")
        .sort_values("consumption_month")
    )

    # Total consumption by commodity
    commodity_analysis = (
        df.groupby(
            ["commodity_id", "commodity_name"]
        )["quantity_kg"]
        .sum()
        .reset_index(name="total_consumption")
        .sort_values("total_consumption", ascending=False)
    )

    total_consumption = df["quantity_kg"].sum()

    most_consumed_commodity = commodity_analysis.iloc[0]["commodity_name"]
    most_consumed_quantity = commodity_analysis.iloc[0]["total_consumption"]

    return {
        "total_consumption": total_consumption,
        "most_consumed_commodity": most_consumed_commodity,
        "most_consumed_quantity": most_consumed_quantity,
        "demand_indicators": generate_demand_indicator(df),
        "beneficiary_analysis": beneficiary_analysis,
        "monthly_analysis": monthly_analysis,
        "commodity_analysis": commodity_analysis
    }
def generate_demand_indicator(df):
    commodity_analysis = (
        df.groupby(
            ["commodity_id", "commodity_name"]
        )["quantity_kg"]
        .sum()
        .reset_index(name="total_consumption")
        .sort_values("total_consumption", ascending=False)
    )

    indicators = []

    for _, row in commodity_analysis.iterrows():

        quantity = float(row["total_consumption"])

        if quantity >= 20:
            demand_level = "HIGH"
        elif quantity >= 10:
            demand_level = "MEDIUM"
        else:
            demand_level = "LOW"

        indicators.append({
            "commodity_id": row["commodity_id"],
            "commodity_name": row["commodity_name"],
            "total_consumption": quantity,
            "demand_level": demand_level
        })

    return pd.DataFrame(indicators)

if __name__ == "__main__":

    print("=" * 60)
    print("AI-BASED SMART PDS")
    print("BENEFICIARY CONSUMPTION & DEMAND ANALYSIS")
    print("=" * 60)

    result = analyze_consumption()

    if result is None:
        print()
        print("No completed consumption data found.")

    else:
        print()

        print("Total Consumption:",
              result["total_consumption"], "KG")

        print("Most Consumed Commodity:",
              result["most_consumed_commodity"])

        print("Most Consumed Quantity:",
              result["most_consumed_quantity"], "KG")

        print()

        print("BENEFICIARY CONSUMPTION ANALYSIS")
        print(result["beneficiary_analysis"].to_string(index=False))

        print()

        print("MONTHLY CONSUMPTION ANALYSIS")
        print(result["monthly_analysis"].to_string(index=False))

        print()

        print("COMMODITY CONSUMPTION ANALYSIS")
        
        print(result["commodity_analysis"].to_string(index=False))

        print()
        print("DEMAND INDICATORS")
        print(result["demand_indicators"].to_string(index=False))
        print(result["commodity_analysis"].to_string(index=False))