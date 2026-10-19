import mysql.connector
import pandas as pd


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya123@2007",
        database="smart_pds"
    )


def get_complaint_data():
    connection = get_db_connection()

    query = """
        SELECT
            complaint_id,
            shop_id,
            category,
            status,
            priority,
            created_at
        FROM complaints
        ORDER BY created_at ASC
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df


def analyze_complaint_trends():
    df = get_complaint_data()

    if df.empty:
        return None

    df["created_at"] = pd.to_datetime(df["created_at"])

    category_analysis = (
        df.groupby("category")
        .size()
        .reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )

    monthly_analysis = (
        df.assign(
            complaint_month=df["created_at"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby("complaint_month")
        .size()
        .reset_index(name="complaint_count")
        .sort_values("complaint_month")
    )

    status_analysis = (
        df.groupby("status")
        .size()
        .reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )

    priority_analysis = (
        df.groupby("priority")
        .size()
        .reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )

    shop_analysis = (
        df.groupby("shop_id")
        .size()
        .reset_index(name="complaint_count")
        .sort_values("complaint_count", ascending=False)
    )

    total_complaints = len(df)

    high_priority_count = len(
        df[df["priority"] == "HIGH"]
    )

    medium_priority_count = len(
        df[df["priority"] == "MEDIUM"]
    )

    low_priority_count = len(
        df[df["priority"] == "LOW"]
    )

    most_common_category = (
        category_analysis.iloc[0]["category"]
    )

    most_common_category_count = int(
        category_analysis.iloc[0]["complaint_count"]
    )

    return {
        "total_complaints": total_complaints,
        "high_priority_count": high_priority_count,
        "medium_priority_count": medium_priority_count,
        "low_priority_count": low_priority_count,
        "most_common_category": most_common_category,
        "most_common_category_count": most_common_category_count,
        "category_analysis": category_analysis,
        "monthly_analysis": monthly_analysis,
        "status_analysis": status_analysis,
        "priority_analysis": priority_analysis,
        "shop_analysis": shop_analysis
    }


if __name__ == "__main__":

    print("=" * 60)
    print("AI-BASED SMART PDS")
    print("COMPLAINT TREND ANALYSIS")
    print("=" * 60)

    result = analyze_complaint_trends()

    if result is None:

        print()
        print("No complaint data found.")

    else:

        print()
        print("Total Complaints:",
              result["total_complaints"])

        print("High Priority Complaints:",
              result["high_priority_count"])

        print("Medium Priority Complaints:",
              result["medium_priority_count"])

        print("Low Priority Complaints:",
              result["low_priority_count"])

        print("Most Common Category:",
              result["most_common_category"])

        print("Category Complaint Count:",
              result["most_common_category_count"])

        print()
        print("CATEGORY ANALYSIS")
        print(result["category_analysis"].to_string(index=False))

        print()
        print("MONTHLY ANALYSIS")
        print(result["monthly_analysis"].to_string(index=False))

        print()
        print("STATUS ANALYSIS")
        print(result["status_analysis"].to_string(index=False))

        print()
        print("PRIORITY ANALYSIS")
        print(result["priority_analysis"].to_string(index=False))

        print()
        print("SHOP ANALYSIS")
        print(result["shop_analysis"].to_string(index=False))