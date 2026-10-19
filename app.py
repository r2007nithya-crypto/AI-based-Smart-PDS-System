from flask import Flask, render_template, request, redirect, url_for, session,send_file
import io
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
import uuid
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import os
from dotenv import load_dotenv
from flask import request
import pandas as pd
from demand_prediction import predict_demand



app = Flask(__name__)

load_dotenv()


# Secret key for login sessions
app.secret_key = "smart_pds_secret_key_2026"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="nithya123@2007",
        database="smart_pds"
    )

    return connection


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        print("RATING POST RECEIVED")
        print("FORM DATA:", request.form)

        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                user_id,
                full_name,
                username,
                email,
                password_hash,
                role,
                is_active
            FROM users
            WHERE username = %s
        """

        cursor.execute(query, (username,))

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        # User not found
        if not user:

            return render_template(
                "login.html",
                error="Invalid username or password."
            )

        # Account inactive
        if not user["is_active"]:

            return render_template(
                "login.html",
                error="Your account is currently inactive."
            )

        # Check password
        if not check_password_hash(
            user["password_hash"],
            password
        ):

            return render_template(
                "login.html",
                error="Invalid username or password."
            )

        # Create login session
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        # Government/Admin
        if user["role"] == "ADMIN":

            return redirect(
                url_for("admin_dashboard")

            )

        # Citizen
        return redirect(
            url_for("citizen_dashboard")
        )

    return render_template("login.html")


# =========================================================
# CITIZEN REGISTRATION
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        language = request.form["language"]

        # -------------------------------------------------
        # CHECK PASSWORDS
        # -------------------------------------------------

        if password != confirm_password:

            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        # -------------------------------------------------
        # HASH PASSWORD
        # -------------------------------------------------

        password_hash = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        # -------------------------------------------------
        # INSERT USER
        # -------------------------------------------------

        query = """
            INSERT INTO users
            (
                full_name,
                username,
                email,
                password_hash,
                role,
                phone,
                preferred_language,
                is_active
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                'CITIZEN',
                %s,
                %s,
                1
            )
        """

        values = (
            full_name,
            username,
            email,
            password_hash,
            phone,
            language
        )

        try:

            cursor.execute(
                query,
                values
            )

            # Get newly created user ID
            user_id = cursor.lastrowid

            # -------------------------------------------------
            # CREATE CITIZEN PROFILE
            # -------------------------------------------------

            citizen_query = """
                INSERT INTO citizens
                (
                    user_id,
                    full_name
                )
                VALUES
                (
                    %s,
                    %s
                )
            """

            cursor.execute(
                citizen_query,
                (
                    user_id,
                    full_name
                )
            )

            # Save both records
            connection.commit()

        except mysql.connector.Error:

            connection.rollback()

            cursor.close()
            connection.close()

            return render_template(
                "register.html",
                error="Username or email already exists."
            )

        cursor.close()
        connection.close()

        # -------------------------------------------------
        # REGISTRATION SUCCESS
        # -------------------------------------------------

        return render_template(
            "register.html",
            success=(
                "Registration successful! "
                "Your Smart PDS citizen account has been created. "
                "You can now log in using your username and password."
            )
        )

    return render_template("register.html")
# =========================================================
# CITIZEN DASHBOARD
# =========================================================
@app.route("/citizen-dashboard")
def citizen_dashboard():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only citizens
    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            notification_id,
            title,
            message,
            notification_type,
            is_read,
            created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, (session["user_id"],))

    notifications = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "citizen_dashboard.html",
        name=session.get("full_name", "Citizen"),
        notifications=notifications
    )
@app.route("/delete-notification/<int:notification_id>", methods=["POST"])
def delete_notification(notification_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM notifications
        WHERE notification_id = %s
        AND user_id = %s
    """, (notification_id, session["user_id"]))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("citizen_dashboard"))
@app.route("/ai-assistant")
def ai_assistant():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    return render_template(
        "ai_assistant.html",
        name=session.get("full_name", "Citizen")
    )
# =========================================================
# ADMIN / GOVERNMENT DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only ADMIN
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Module 8 - Latest AI predictions
    cursor.execute("""
        SELECT
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            ap.prediction_month,
            ap.predicted_quantity_kg,
            ap.confidence_score
        FROM ai_predictions ap
        JOIN fair_price_shops fps
            ON ap.shop_id = fps.shop_id
        JOIN commodities c
            ON ap.commodity_id = c.commodity_id
        ORDER BY ap.prediction_month DESC
        LIMIT 5
    """)

    ai_predictions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_dashboard.html",
        name=session.get("full_name", "Administrator"),
        ai_predictions=ai_predictions
    )
@app.route("/admin/generate-demand-predictions")
def generate_demand_predictions():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only ADMIN
    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Get all active shops and commodities
        cursor.execute("""
            SELECT
                shop_id,
                commodity_id
            FROM shop_stock
        """)

        items = cursor.fetchall()

        # Generate prediction for each shop/commodity
        for item in items:

            prediction = predict_demand(
                connection,
                item["commodity_id"],
                item["shop_id"]
            )

            if prediction is None:
                continue

            # October 2026 prediction
            prediction_month = "2026-10-01"

            # Save / update prediction
            cursor.execute("""
                SELECT prediction_id
                FROM ai_predictions
                WHERE shop_id = %s
                  AND commodity_id = %s
                  AND prediction_month = %s
            """, (
                item["shop_id"],
                item["commodity_id"],
                prediction_month
            ))

            existing = cursor.fetchone()

            print(
                f"AI PREDICTION DEBUG | "
                f"Shop: {item['shop_id']} | "
                f"Commodity: {item['commodity_id']} | "
                f"Prediction: {prediction}"
            )

            if existing:

                cursor.execute("""
                    UPDATE ai_predictions
                    SET
                        predicted_quantity_kg = %s,
                        confidence_score = %s,
                        model_name = %s
                    WHERE prediction_id = %s
                """, (
                    prediction,
                    80.00,
                    "Linear Trend Model",
                    existing["prediction_id"]
                ))

            else:

                cursor.execute("""
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
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    item["shop_id"],
                    item["commodity_id"],
                    prediction_month,
                    prediction,
                    80.00,
                    "Linear Trend Model"
                ))

        connection.commit()

        return redirect(url_for("admin_dashboard"))

    finally:

        cursor.close()
        connection.close()
# --------------------------------------------------------
# Complaint Trend Analysis
# --------------------------------------------------------


# =========================================================
# RATION ENTITLEMENT
# =========================================================
@app.route("/entitlement")
def entitlement():

    # Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Only citizens
    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # ---------------------------------------------------------
        # FIND LOGGED-IN CITIZEN
        # ---------------------------------------------------------
        cursor.execute("""
            SELECT
                c.citizen_id,
                c.full_name
            FROM citizens c
            WHERE c.user_id = %s
        """, (session["user_id"],))

        citizen = cursor.fetchone()

        if not citizen:
            return "Citizen profile not found", 404

        citizen_id = citizen["citizen_id"]


        # ---------------------------------------------------------
        # FIND CITIZEN'S ACTIVE RATION CARD
        # ---------------------------------------------------------
        cursor.execute("""
            SELECT
                ration_card_id,
                card_number,
                card_type
            FROM ration_cards
            WHERE head_citizen_id = %s
              AND status = 'ACTIVE'
            LIMIT 1
        """, (citizen_id,))

        ration_card = cursor.fetchone()

        if not ration_card:

            return render_template(
                "entitlement.html",
                name=citizen["full_name"],
                ration_card=None,
                entitlements=[],
                collection_history=[]
            )


        ration_card_id = ration_card["ration_card_id"]


        # ---------------------------------------------------------
        # CURRENT MONTH ENTITLEMENT
        # ---------------------------------------------------------
        cursor.execute("""
            SELECT
                re.entitlement_id,
                re.month_year,
                c.commodity_name,
                c.unit,
                re.entitled_quantity
            FROM ration_entitlements re

            INNER JOIN commodities c
                ON re.commodity_id = c.commodity_id

            WHERE re.ration_card_id = %s

              AND re.month_year = DATE_FORMAT(
                    CURDATE(),
                    '%Y-%m-01'
                  )
                  AND c.is_active = 1

            ORDER BY c.commodity_name
        """, (ration_card_id,))

        entitlements = cursor.fetchall()


        # ---------------------------------------------------------
        # COLLECTION HISTORY
        # ---------------------------------------------------------
        cursor.execute("""
            SELECT
                rt.transaction_id,
                rt.transaction_date,
                c.commodity_name,
                c.unit,
                rt.quantity_kg,
                rt.verification_method,
                rt.status,
                fps.shop_name,
                fps.shop_code

            FROM ration_transactions rt

            INNER JOIN commodities c
                ON rt.commodity_id = c.commodity_id

            INNER JOIN fair_price_shops fps
                ON rt.shop_id = fps.shop_id

            WHERE rt.ration_card_id = %s

            ORDER BY rt.transaction_date DESC
        """, (ration_card_id,))

        collection_history = cursor.fetchall()


        # ---------------------------------------------------------
        # SEND DATA TO HTML
        # ---------------------------------------------------------
        return render_template(
            "entitlement.html",
            name=citizen["full_name"],
            ration_card=ration_card,
            entitlements=entitlements,
            collection_history=collection_history
        )

    finally:

        cursor.close()
        connection.close()
@app.route("/token-booking", methods=["GET", "POST"])
def token_booking():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    if request.method == "POST":

        shop = request.form["shop"]
        collection_date = request.form["collection_date"]
        time_slot = request.form["time_slot"]

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            token_number = "PDS-" + str(uuid.uuid4())[:8].upper()

            query = """
                INSERT INTO ration_tokens
                (
                    user_id,
                    shop_code,
                    collection_date,
                    time_slot,
                    token_number,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, 'BOOKED')
            """

            values = (
                session["user_id"],
                shop,
                collection_date,
                time_slot,
                token_number
            )

            cursor.execute(query, values)
            connection.commit()

            cursor.close()
            connection.close()

            return render_template(
                "token_booking.html",
                name=session.get("full_name", "Citizen"),
                success="Token booked successfully!",
                token_number=token_number,
                booked_shop=shop,
                booked_date=collection_date,
                booked_time=time_slot
            )

        except mysql.connector.Error:

            connection.rollback()

            cursor.close()
            connection.close()

            return render_template(
                "token_booking.html",
                name=session.get("full_name", "Citizen"),
                error="Unable to book token. Please try again."
            )

    return render_template(
        "token_booking.html",
        name=session.get("full_name", "Citizen")
    )

# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================
@app.route("/token-history")
def token_history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            token_number,
            shop_code,
            collection_date,
            time_slot,
            status
        FROM ration_tokens
        WHERE user_id = %s
        ORDER BY collection_date DESC
    """

    cursor.execute(query, (session["user_id"],))

    tokens = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "token_history.html",
        name=session.get("full_name", "Citizen"),
        tokens=tokens
    )
@app.route("/token/<token_number>")
def view_token(token_number):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            token_number,
            shop_code,
            collection_date,
            time_slot,
            status
        FROM ration_tokens
        WHERE token_number = %s
        AND user_id = %s
    """

    cursor.execute(
        query,
        (token_number, session["user_id"])
    )

    token = cursor.fetchone()

    cursor.close()
    connection.close()

    if not token:
        return "Token not found.", 404

    return render_template(
        "view_token.html",
        token=token,
        name=session.get("full_name", "Citizen")
    )
@app.route("/token/<token_number>/download")
def download_token(token_number):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            token_number,
            shop_code,
            collection_date,
            time_slot,
            status
        FROM ration_tokens
        WHERE token_number = %s
        AND user_id = %s
    """

    cursor.execute(
        query,
        (token_number, session["user_id"])
    )

    token = cursor.fetchone()

    cursor.close()
    connection.close()

    if not token:
        return "Token not found.", 404

    pdf_buffer = BytesIO()

    pdf = canvas.Canvas(pdf_buffer, pagesize=A4)

    width, height = A4

    pdf.setTitle("Smart PDS Ration Collection Token")

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(
        width / 2,
        height - 70,
        "SMART PUBLIC DISTRIBUTION SYSTEM"
    )

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(
        width / 2,
        height - 90,
        "Digital Ration Collection Token"
    )

    pdf.line(60, height - 110, width - 60, height - 110)

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(
        70,
        height - 155,
        "TOKEN NUMBER"
    )

    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(
        70,
        height - 185,
        token["token_number"]
    )

    pdf.setFont("Helvetica-Bold", 11)

    pdf.drawString(70, height - 240, "Citizen:")
    pdf.drawString(70, height - 280, "Fair Price Shop:")
    pdf.drawString(70, height - 320, "Collection Date:")
    pdf.drawString(70, height - 360, "Collection Time:")
    pdf.drawString(70, height - 400, "Status:")

    pdf.setFont("Helvetica", 11)

    pdf.drawString(
        190,
        height - 240,
        str(session.get("full_name", "Citizen"))
    )

    pdf.drawString(
        190,
        height - 280,
        str(token["shop_code"])
    )

    pdf.drawString(
        190,
        height - 320,
        str(token["collection_date"])
    )

    pdf.drawString(
        190,
        height - 360,
        str(token["time_slot"])
    )

    pdf.drawString(
        190,
        height - 400,
        str(token["status"])
    )

    pdf.setFont("Helvetica", 9)

    pdf.drawCentredString(
        width / 2,
        80,
        "Please carry your ration card when visiting the Fair Price Shop."
    )

    pdf.drawCentredString(
        width / 2,
        60,
        "Smart PDS — Academic Project"
    )

    pdf.save()

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{token['token_number']}.pdf",
        mimetype="application/pdf"
    )
@app.route("/token/<token_number>/cancel", methods=["POST"])
def cancel_token(token_number):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        UPDATE ration_tokens
        SET status = 'CANCELLED'
        WHERE token_number = %s
        AND user_id = %s
        AND status = 'BOOKED'
    """

    cursor.execute(
        query,
        (token_number, session["user_id"])
    )

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("token_history"))
@app.route("/admin/shops")
def admin_shops():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            fps.shop_id,
            fps.shop_code,
            fps.shop_name,
            d.district_name,
            t.taluk_name,
            fps.address,
            fps.total_beneficiaries,
            fps.is_active
        FROM fair_price_shops fps
        INNER JOIN districts d
            ON fps.district_id = d.district_id
        INNER JOIN taluks t
            ON fps.taluk_id = t.taluk_id
        ORDER BY fps.shop_code
    """

    cursor.execute(query)

    shops = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_shops.html",
        shops=shops
    )  
@app.route("/admin/stock", methods=["GET", "POST"])
def admin_stock():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # UPDATE STOCK
    if request.method == "POST":

        stock_id = request.form["stock_id"]
        new_quantity = float(request.form["quantity"])

        try:

            # Get existing stock information
            cursor.execute(
                """
                SELECT
                    shop_id,
                    commodity_id,
                    quantity_kg
                FROM shop_stock
                WHERE stock_id = %s
                """,
                (stock_id,)
            )

            current_stock = cursor.fetchone()

            if current_stock:

                old_quantity = float(
                    current_stock["quantity_kg"]
                )

                # Calculate stock change
                difference = new_quantity - old_quantity

                # Update current stock
                cursor.execute(
                    """
                    UPDATE shop_stock
                    SET quantity_kg = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE stock_id = %s
                    """,
                    (new_quantity, stock_id)
                )

                # Record transaction only if quantity changed
                if difference != 0:

                    cursor.execute(
                        """
                        INSERT INTO stock_transactions
                        (
                            shop_id,
                            commodity_id,
                            transaction_type,
                            quantity_kg,
                            transaction_date,
                            reference_note
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            'ADJUSTMENT',
                            %s,
                            NOW(),
                            %s
                        )
                        """,
                        (
                            current_stock["shop_id"],
                            current_stock["commodity_id"],
                            abs(difference),
                            "Manual stock adjustment by administrator"
                        )
                    )

                connection.commit()

        except mysql.connector.Error:

            connection.rollback()

        finally:

            cursor.close()
            connection.close()

        return redirect(url_for("admin_stock"))

    # LOW STOCK FILTER
    status = request.args.get("status")

    # GET STOCK DATA
    query = """
        SELECT
            ss.stock_id,
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            c.unit,
            ss.quantity_kg,
            ss.minimum_threshold_kg,
            ss.last_updated
        FROM shop_stock ss
        INNER JOIN fair_price_shops fps
            ON ss.shop_id = fps.shop_id
        INNER JOIN commodities c
            ON ss.commodity_id = c.commodity_id
    """

    if status == "low":

        query += """
            WHERE ss.quantity_kg <= ss.minimum_threshold_kg
        """

    query += """
        ORDER BY fps.shop_code, c.commodity_name
    """

    cursor.execute(query)

    stock = cursor.fetchall()

    low_stock_count = sum(
        1
        for item in stock
        if item["quantity_kg"] <= item["minimum_threshold_kg"]
    )

    cursor.close()
    connection.close()

    return render_template(
        "admin_stock.html",
        stock=stock,
        low_stock_count=low_stock_count
    )
@app.route("/admin/stock-history")
def admin_stock_history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT
            st.stock_transaction_id,
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            c.unit,
            st.transaction_type,
            st.quantity_kg,
            st.transaction_date,
            st.reference_note
        FROM stock_transactions st
        INNER JOIN fair_price_shops fps
            ON st.shop_id = fps.shop_id
        INNER JOIN commodities c
            ON st.commodity_id = c.commodity_id
        ORDER BY st.transaction_date DESC
    """

    cursor.execute(query)

    transactions = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_stock_history.html",
        transactions=transactions
    )
@app.route("/citizen/stock")
def citizen_stock():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            c.unit,
            ss.quantity_kg,
            ss.minimum_threshold_kg,
            ss.last_updated
        FROM shop_stock ss
        INNER JOIN fair_price_shops fps
            ON ss.shop_id = fps.shop_id
        INNER JOIN commodities c
            ON ss.commodity_id = c.commodity_id
        ORDER BY fps.shop_code, c.commodity_name
    """)

    stock = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "citizen_stock.html",
        stock=stock
    )
@app.route("/citizen/rate-shop", methods=["GET", "POST"])
def citizen_rate_shop():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Find logged-in citizen
    cursor.execute("""
        SELECT citizen_id
        FROM citizens
        WHERE user_id = %s
    """, (session["user_id"],))

    citizen = cursor.fetchone()

    if not citizen:
        cursor.close()
        connection.close()
        return "Citizen profile not found", 404

    citizen_id = citizen["citizen_id"]

    # Get all Fair Price Shops
    cursor.execute("""
        SELECT
            shop_id,
            shop_code,
            shop_name
        FROM fair_price_shops
        ORDER BY shop_name
    """)

    shops = cursor.fetchall()

    # Submit rating
    if request.method == "POST":

        shop_id = request.form.get("shop_id")
        rating = request.form.get("rating")
        feedback = request.form.get("feedback", "").strip()

        if not shop_id or not rating:
            cursor.close()
            connection.close()
            return "Shop and rating are required", 400

        try:
            shop_id = int(shop_id)
            rating = int(rating)
        except ValueError:
            cursor.close()
            connection.close()
            return "Invalid shop or rating", 400

        if rating < 1 or rating > 5:
            cursor.close()
            connection.close()
            return "Rating must be between 1 and 5", 400

        # Save rating
        cursor.execute("""
            INSERT INTO ratings
            (
                citizen_id,
                shop_id,
                rating,
                feedback
            )
            VALUES
            (%s, %s, %s, %s)
        """, (
            citizen_id,
            shop_id,
            rating,
            feedback
        ))

        # Update shop performance rating score
        update_shop_rating_score(
            connection,
            shop_id
        )

        connection.commit()

        cursor.close()
        connection.close()

        return redirect(
            url_for(
                "citizen_rate_shop",
                success=1
            )
        )

    cursor.close()
    connection.close()

    success = request.args.get("success")

    return render_template(
        "citizen_rate_shop.html",
        shops=shops,
        success=success
    )


@app.route("/register-complaint", methods=["GET", "POST"])
def register_complaint():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Get available Fair Price Shops
    cursor.execute("""
        SELECT
            shop_id,
            shop_code,
            shop_name
        FROM fair_price_shops
        WHERE is_active = 1
        ORDER BY shop_code
    """)

    shops = cursor.fetchall()

    if request.method == "POST":

        shop_id = request.form["shop_id"]
        category = request.form["category"]
        description = request.form["description"]
        priority = request.form["priority"]

        complaint_number = "CMP-" + str(uuid.uuid4())[:8].upper()

        try:

            # Find citizen ID from logged-in user
            cursor.execute("""
                SELECT citizen_id
                FROM citizens
                WHERE user_id = %s
            """, (session["user_id"],))

            citizen = cursor.fetchone()

            if not citizen:

                cursor.close()
                connection.close()

                return render_template(
                    "register_complaint.html",
                    name=session.get("full_name", "Citizen"),
                    shops=shops,
                    error="Citizen profile not found."
                )

            citizen_id = citizen["citizen_id"]

            # Save complaint
            cursor.execute("""
                INSERT INTO complaints
                (
                    complaint_number,
                    citizen_id,
                    shop_id,
                    category,
                    description,
                    status,
                    priority,
                    created_at
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'SUBMITTED',
                    %s,
                    NOW()
                )
            """, (
                complaint_number,
                citizen_id,
                shop_id,
                category,
                description,
                priority
            ))

            connection.commit()

            cursor.close()
            connection.close()

            return render_template(
                "register_complaint.html",
                name=session.get("full_name", "Citizen"),
                shops=shops,
                success="Complaint submitted successfully!",
                complaint_number=complaint_number
            )

        except mysql.connector.Error:

            connection.rollback()

            cursor.close()
            connection.close()

            return render_template(
                "register_complaint.html",
                name=session.get("full_name", "Citizen"),
                shops=shops,
                error="Unable to submit complaint. Please try again."
            )

    cursor.close()
    connection.close()

    return render_template(
        "register_complaint.html",
        name=session.get("full_name", "Citizen"),
        shops=shops
    )
@app.route("/my-complaints")
def my_complaints():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.complaint_number,
            fps.shop_code,
            fps.shop_name,
            c.category,
            c.priority,
            c.status,
            c.created_at,
            c.resolved_at
        FROM complaints c
        INNER JOIN citizens ci
            ON c.citizen_id = ci.citizen_id
        INNER JOIN fair_price_shops fps
            ON c.shop_id = fps.shop_id
        WHERE ci.user_id = %s
        ORDER BY c.created_at DESC
    """, (session["user_id"],))

    complaints = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "my_complaints.html",
        name=session.get("full_name", "Citizen"),
        complaints=complaints
    )
@app.route("/admin/complaints")
def admin_complaints():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.complaint_id,
            c.complaint_number,
            ci.full_name,
            fps.shop_code,
            fps.shop_name,
            c.category,
            c.description,
            c.priority,
            c.status,
            c.created_at,
            c.resolved_at
        FROM complaints c
        INNER JOIN citizens ci
            ON c.citizen_id = ci.citizen_id
        INNER JOIN fair_price_shops fps
            ON c.shop_id = fps.shop_id
        ORDER BY c.created_at DESC
    """)

    complaints = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_complaints.html",
        complaints=complaints
    )
@app.route("/admin/complaints/update/<int:complaint_id>", methods=["POST"])
def update_complaint_status(complaint_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    new_status = request.form["status"]

    allowed_statuses = [
        "SUBMITTED",
        "UNDER_REVIEW",
        "IN_PROGRESS",
        "RESOLVED",
        "REJECTED"
    ]

    if new_status not in allowed_statuses:
        return redirect(url_for("admin_complaints"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        # Update complaint status
        if new_status == "RESOLVED":

            cursor.execute("""
                UPDATE complaints
                SET status = %s,
                    resolved_at = NOW()
                WHERE complaint_id = %s
            """, (new_status, complaint_id))

        else:

            cursor.execute("""
                UPDATE complaints
                SET status = %s,
                    resolved_at = NULL
                WHERE complaint_id = %s
            """, (new_status, complaint_id))

        # Find citizen who submitted the complaint
        cursor.execute("""
            SELECT
                ci.user_id,
                c.complaint_number
            FROM complaints c
            INNER JOIN citizens ci
                ON c.citizen_id = ci.citizen_id
            WHERE c.complaint_id = %s
        """, (complaint_id,))

        citizen = cursor.fetchone()

        # Create in-app notification
        if citizen:

            cursor.execute("""
                INSERT INTO notifications
                (
                    user_id,
                    title,
                    message,
                    notification_type
                )
                VALUES (%s, %s, %s, %s)
            """, (
                citizen[0],
                "Complaint Status Updated",
                f"Your complaint {citizen[1]} is now {new_status.replace('_', ' ')}.",
                "COMPLAINT"
            ))

        connection.commit()

    except mysql.connector.Error:

        connection.rollback()

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("admin_complaints"))
@app.route("/home-delivery", methods=["GET", "POST"])
def home_delivery():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    if request.method == "POST":

        eligibility_reason = request.form.get("eligibility_reason")
        request_notes = request.form.get("request_notes", "")
        evidence_file = request.files.get("evidence_file")

        # Find citizen
        cursor.execute("""
            SELECT citizen_id
            FROM citizens
            WHERE user_id = %s
        """, (session["user_id"],))

        citizen = cursor.fetchone()

        if not citizen:
            cursor.close()
            connection.close()
            return "Citizen profile not found."

        citizen_id = citizen["citizen_id"]

        # Check eligibility
        cursor.execute("""
            SELECT senior_citizen,
                   disability_status,
                   bedridden_status
            FROM citizens
            WHERE citizen_id = %s
        """, (citizen_id,))

        eligibility = cursor.fetchone()

        eligible = False

        if eligibility_reason == "SENIOR_CITIZEN" and eligibility["senior_citizen"] == 1:
            eligible = True

        elif eligibility_reason == "DIFFERENTLY_ABLED" and eligibility["disability_status"] == 1:
            eligible = True

        elif eligibility_reason == "BEDRIDDEN" and eligibility["bedridden_status"] == 1:
            eligible = True

        if not eligible:
            cursor.close()
            connection.close()

            return render_template(
                "home_delivery.html",
                name=session.get("full_name", "Citizen"),
                error="You are not currently verified as eligible for this home delivery category."
            )

        # Find ration card and shop
        cursor.execute("""
            SELECT
                rc.ration_card_id,
                rt.shop_id
            FROM ration_cards rc
            LEFT JOIN ration_transactions rt
                ON rt.ration_card_id = rc.ration_card_id
            WHERE rc.head_citizen_id = %s
              AND rc.status = 'ACTIVE'
            ORDER BY rt.transaction_date DESC
            LIMIT 1
        """, (citizen_id,))

        pds_data = cursor.fetchone()

        if not pds_data or not pds_data["shop_id"]:
            cursor.close()
            connection.close()

            return render_template(
                "home_delivery.html",
                name=session.get("full_name", "Citizen"),
                error="Your ration card or Fair Price Shop information is not available."
            )

        ration_card_id = pds_data["ration_card_id"]
        shop_id = pds_data["shop_id"]

        # Generate request number
        request_number = "DEL-" + str(uuid.uuid4())[:8].upper()

        # Store uploaded filename
        filename = None

        if evidence_file and evidence_file.filename:
            filename = evidence_file.filename

        # Save request
        cursor.execute("""
            INSERT INTO delivery_requests
            (
                request_number,
                citizen_id,
                ration_card_id,
                shop_id,
                eligibility_reason,
                request_notes,
                evidence_file,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING')
        """, (
            request_number,
            citizen_id,
            ration_card_id,
            shop_id,
            eligibility_reason,
            request_notes,
            filename
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return render_template(
            "home_delivery.html",
            name=session.get("full_name", "Citizen"),
            success="Home delivery request submitted successfully.",
            request_number=request_number
        )

    cursor.close()
    connection.close()

    return render_template(
        "home_delivery.html",
        name=session.get("full_name", "Citizen")
    )
@app.route("/admin/delivery-requests")
def admin_delivery_requests():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.delivery_request_id,
            d.request_number,
            c.full_name,
            d.eligibility_reason,
            d.request_notes,
            d.evidence_file,
            d.status,
            d.admin_remarks,
            d.requested_at
        FROM delivery_requests d
        INNER JOIN citizens c
            ON d.citizen_id = c.citizen_id
        ORDER BY d.requested_at DESC
    """)

    requests = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_delivery_requests.html",
        requests=requests
    )
@app.route("/admin/delivery-requests/<int:request_id>/approve", methods=["POST"])
def approve_delivery_request(request_id):

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE delivery_requests
        SET
            status = 'APPROVED',
            approved_at = NOW(),
            admin_remarks = 'Request approved by administrator'
        WHERE delivery_request_id = %s
          AND status = 'PENDING'
    """, (request_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("admin_delivery_requests"))


@app.route("/admin/delivery-requests/<int:request_id>/reject", methods=["POST"])
def reject_delivery_request(request_id):

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE delivery_requests
        SET
            status = 'REJECTED',
            admin_remarks = 'Request rejected by administrator'
        WHERE delivery_request_id = %s
          AND status = 'PENDING'
    """, (request_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("admin_delivery_requests"))
@app.route("/my-delivery-requests")
def my_delivery_requests():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.request_number,
            d.eligibility_reason,
            d.status,
            d.admin_remarks,
            d.requested_at,
            d.approved_at,
            d.delivered_at,
            fps.shop_name
        FROM delivery_requests d
        INNER JOIN citizens c
            ON d.citizen_id = c.citizen_id
        LEFT JOIN fair_price_shops fps
            ON d.shop_id = fps.shop_id
        WHERE c.user_id = %s
        ORDER BY d.requested_at DESC
    """, (session["user_id"],))

    requests = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "my_delivery_requests.html",
        name=session.get("full_name", "Citizen"),
        requests=requests
    )
@app.route("/ai-assistant/ask", methods=["POST"])
def ai_assistant_ask():

    if "user_id" not in session:
        return {"answer": "Please login first."}, 401

    if session.get("role") != "CITIZEN":
        return {"answer": "Access denied."}, 403

    data = request.get_json()
    question = data.get("question", "").strip().lower()

    if not question:
        return {"answer": "Please enter a question."}


    # =====================================================
    # RATION TOKEN
    # =====================================================

    if (
        "token" in question
        or "ration token" in question
        or "book token" in question
        or "token booking" in question
        or "டோக்கன்" in question
        or "டோக்கன் பதிவு" in question
    ):

        answer = (
            "You can book a ration token from the Ration Token "
            "service in your Citizen Dashboard. Select an available "
            "collection slot and confirm your booking."
        )


    # =====================================================
    # COMPLAINT
    # =====================================================

    elif (
        "complaint" in question
        or "complain" in question
        or "grievance" in question
        or "problem with ration" in question
        or "புகார்" in question
        or "குறை" in question
    ):

        answer = (
            "You can register a PDS complaint from the Complaints "
            "service. After submission, you will receive a unique "
            "Complaint ID that can be used to track the status."
        )


    # =====================================================
    # HOME DELIVERY
    # =====================================================

    elif (
        "home delivery" in question
        or "door delivery" in question
        or "delivery" in question
        or "deliver ration" in question
        or "delivery eligibility" in question
        or "வீட்டு விநியோகம்" in question
        or "வீட்டு டெலிவரி" in question
    ):

        answer = (
            "Home delivery is available for eligible citizens such as "
            "senior citizens, differently-abled persons and bedridden "
            "persons. Requests are reviewed and approved by the "
            "administrator."
        )


    # =====================================================
    # STOCK / SHOP
    # =====================================================

    elif (
        "stock" in question
        or "shop stock" in question
        or "ration shop" in question
        or "fair price shop" in question
        or "fps" in question
        or "பங்கு" in question
        or "ரேஷன் கடை" in question
    ):

        answer = (
            "You can check Fair Price Shop and commodity stock "
            "information through the Shop & Stock service."
        )


    # =====================================================
    # PERSONALIZED RATION ENTITLEMENT
    # =====================================================

    elif (
        "entitlement" in question
        or "monthly ration" in question
        or "ration quantity" in question
        or "how much ration" in question
        or "ration amount" in question
        or "my ration" in question
        or "என் ரேஷன்" in question
        or "ஒதுக்கீடு" in question
        or "ரேஷன்" in question
    ):

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT
                    rc.card_number,
                    c.commodity_name,
                    c.unit,
                    re.entitled_quantity,
                    re.month_year
                FROM citizens ci
                JOIN ration_cards rc
                    ON ci.citizen_id = rc.head_citizen_id
                JOIN ration_entitlements re
                    ON rc.ration_card_id = re.ration_card_id
                JOIN commodities c
                    ON re.commodity_id = c.commodity_id
                WHERE ci.user_id = %s
                AND c.is_active = 1
                ORDER BY re.month_year DESC
                LIMIT 10
            """, (session["user_id"],))

            entitlements = cursor.fetchall()


            if entitlements:

                answer = (
                    "Here is your ration entitlement:\n\n"
                )

                for item in entitlements:

                    answer += (
                        f"• {item['commodity_name']}: "
                        f"{item['entitled_quantity']} "
                        f"{item['unit']}\n"
                    )

            else:

                answer = (
                    "I could not find entitlement data for your "
                    "ration card. Please check the Ration Entitlement "
                    "section in your Citizen Dashboard."
                )


        except Exception as e:

            print("AI ENTITLEMENT ERROR:", e)

            answer = (
                "I could not retrieve your entitlement information "
                "right now. Please try again or check the Ration "
                "Entitlement section."
            )


        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()


    # =====================================================
    # DEFAULT
    # =====================================================

    else:

        answer = (
            "I can help you with Tamil Nadu PDS services such as "
            "ration entitlement, ration tokens, complaints, shop "
            "stock and home delivery. Please ask a PDS-related question."
        )


    return {"answer": answer}
@app.route("/shop-rating", methods=["GET", "POST"])
def shop_rating():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Find logged-in citizen
    cursor.execute("""
        SELECT citizen_id
        FROM citizens
        WHERE user_id = %s
    """, (session["user_id"],))

    citizen = cursor.fetchone()

    if not citizen:
        cursor.close()
        connection.close()
        return "Citizen profile not found."

    if request.method == "POST":

        shop_id = request.form["shop_id"]
        rating = request.form["rating"]
        feedback = request.form.get("feedback", "").strip()

        cursor.execute("""
            INSERT INTO ratings
            (citizen_id, shop_id, rating, feedback)
            VALUES (%s, %s, %s, %s)
        """, (
            citizen["citizen_id"],
            shop_id,
            rating,
            feedback
        ))

        connection.commit()

        cursor.close()
        connection.close()

        return render_template(
            "shop_rating.html",
            name=session.get("full_name", "Citizen"),
            success="Thank you! Your rating and feedback have been submitted."
        )

    # Load active shops
    cursor.execute("""
        SELECT shop_id, shop_code, shop_name
        FROM fair_price_shops
        WHERE is_active = 1
        ORDER BY shop_name
    """)

    shops = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "shop_rating.html",
        name=session.get("full_name", "Citizen"),
        shops=shops
    )
@app.route("/admin-ratings")
def admin_ratings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            r.rating_id,
            r.rating,
            r.feedback,
            r.created_at,
            fps.shop_code,
            fps.shop_name,
            c.full_name
        FROM ratings r
        JOIN fair_price_shops fps
            ON r.shop_id = fps.shop_id
        JOIN citizens c
            ON r.citizen_id = c.citizen_id
        ORDER BY r.created_at DESC
    """)

    ratings = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "admin_ratings.html",
        ratings=ratings
    )
@app.route("/admin/shop-performance")
def admin_shop_performance():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            fps.shop_id,
            fps.shop_code,
            fps.shop_name,

            (
                SELECT AVG(r.rating) / 5 * 100
                FROM ratings r
                WHERE r.shop_id = fps.shop_id
            ) AS rating_score,

            (
                SELECT AVG(
                    LEAST(
                        (ss.quantity_kg /
                        NULLIF(ss.minimum_threshold_kg, 0)) * 100,
                        100
                    )
                )
                FROM shop_stock ss
                WHERE ss.shop_id = fps.shop_id
            ) AS stock_score,

            (
                SELECT AVG(
                    CASE
                        WHEN c.status = 'RESOLVED' THEN 100
                        WHEN c.status = 'REJECTED' THEN 100
                        WHEN c.status = 'IN_PROGRESS' THEN 70
                        WHEN c.status = 'UNDER_REVIEW' THEN 50
                        WHEN c.status = 'SUBMITTED' THEN 30
                        ELSE 0
                    END
                )
                FROM complaints c
                WHERE c.shop_id = fps.shop_id
            ) AS complaint_score

        FROM fair_price_shops fps
        WHERE fps.is_active = 1
        ORDER BY fps.shop_id
    """)

    shops = cursor.fetchall()

    for shop in shops:

        rating = shop["rating_score"]
        stock = shop["stock_score"]
        complaint = shop["complaint_score"]

        scores = []
        weights = []

        # Rating score
        if rating is not None:
            scores.append(float(rating))
            weights.append(0.40)

        # Stock score
        if stock is not None:
            scores.append(float(stock))
            weights.append(0.30)

        # Complaint score
        if complaint is not None:
            scores.append(float(complaint))
            weights.append(0.30)

        # Overall score
        if rating is None and complaint is None:

            if stock is not None:
                overall = float(stock)
            else:
                overall = 0

        elif scores:

            overall = sum(
                score * weight
                for score, weight in zip(scores, weights)
            ) / sum(weights)

        else:
            overall = 0

        # Display rating
        if rating is not None:
            shop["rating_score"] = round(float(rating), 2)
        else:
            shop["rating_score"] = None

        # Display stock
        if stock is not None:
            shop["stock_score"] = round(float(stock), 2)
        else:
            shop["stock_score"] = None

        # Display complaint
        if complaint is not None:
            shop["complaint_score"] = round(float(complaint), 2)
        else:
            shop["complaint_score"] = None

        # Display overall
        shop["overall_score"] = round(overall, 2)

        # Performance level
        if rating is None and complaint is None:

            shop["performance_level"] = "Insufficient Data"

        elif overall >= 80:

            shop["performance_level"] = "Excellent"

        elif overall >= 60:

            shop["performance_level"] = "Good"

        elif overall >= 40:

            shop["performance_level"] = "Needs Improvement"

        else:

            shop["performance_level"] = "Poor"

    cursor.close()
    connection.close()

    return render_template(
        "admin_shop_performance.html",
        shops=shops
    )
@app.route("/admin/demand-prediction")
def admin_demand_prediction():

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # --------------------------------------------------------
    # Prediction records
    # --------------------------------------------------------

    prediction_query = """
        SELECT
            ap.prediction_id,
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            c.unit,
            ap.prediction_month,
            ap.predicted_quantity_kg,
            ap.confidence_score,
            ap.model_name,
            ap.created_at
        FROM ai_predictions ap
        JOIN fair_price_shops fps
            ON ap.shop_id = fps.shop_id
        JOIN commodities c
            ON ap.commodity_id = c.commodity_id
        ORDER BY
            ap.prediction_month DESC,
            ap.created_at DESC
    """

    cursor.execute(prediction_query)
    predictions = cursor.fetchall()


    # --------------------------------------------------------
    # Historical distribution data
    # --------------------------------------------------------

    history_query = """
        SELECT
            DATE_FORMAT(transaction_date, '%Y-%m') AS month,
            SUM(quantity_kg) AS quantity
        FROM stock_transactions
        WHERE shop_id = 1
          AND commodity_id = 1
          AND transaction_type = 'DISTRIBUTED'
        GROUP BY DATE_FORMAT(transaction_date, '%Y-%m')
        ORDER BY month ASC
    """

    cursor.execute(history_query)
    history = cursor.fetchall()


    cursor.close()
    connection.close()


    # Convert database values into chart-friendly lists

    history_labels = [
        row["month"]
        for row in history
    ]

    history_values = [
        float(row["quantity"])
        for row in history
    ]


    return render_template(
        "admin_demand_prediction.html",
        predictions=predictions,
        history_labels=history_labels,
        history_values=history_values
    )
@app.route("/admin/decision-support")
def admin_decision_support():

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    selected_shop_id = request.args.get("shop_id", type=int)

    # --------------------------------------------------------
    # GET FAIR PRICE SHOP LIST
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            shop_id,
            shop_code,
            shop_name
        FROM fair_price_shops
        WHERE is_active = 1
        ORDER BY shop_name
    """)

    shops = cursor.fetchall()

    # --------------------------------------------------------
    # AI DEMAND PREDICTIONS
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            ap.prediction_id,
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            ap.prediction_month,
            ap.predicted_quantity_kg,
            ap.confidence_score,
            ap.model_name,
            ap.created_at
        FROM ai_predictions ap
        JOIN fair_price_shops fps
            ON ap.shop_id = fps.shop_id
        JOIN commodities c
            ON ap.commodity_id = c.commodity_id
        ORDER BY
            ap.prediction_month DESC,
            ap.created_at DESC
        LIMIT 10
    """)

    predictions = cursor.fetchall()

    # --------------------------------------------------------
    # UNUSUAL PATTERN / ANOMALY RESULTS
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            anomaly_id,
            shop_id,
            transaction_id,
            anomaly_type,
            anomaly_score,
            description,
            detection_date,
            review_status
        FROM anomaly_results
        ORDER BY detection_date DESC
        LIMIT 10
    """)

    anomalies = cursor.fetchall()

    # --------------------------------------------------------
    # AI RECOMMENDATIONS
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            recommendation_id,
            recommendation_type,
            district_id,
            shop_id,
            title,
            recommendation_text,
            priority,
            status,
            created_at
        FROM ai_recommendations
        ORDER BY created_at DESC
        LIMIT 10
    """)

    recommendations = cursor.fetchall()

    # --------------------------------------------------------
    # FAIR PRICE SHOP PERFORMANCE
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            score_id,
            shop_id,
            evaluation_month,
            rating_score,
            stock_score,
            complaint_score,
            service_score,
            overall_score,
            performance_level,
            calculated_at
        FROM shop_scores
        ORDER BY evaluation_month DESC
        LIMIT 10
    """)

    shop_scores = cursor.fetchall()

    # --------------------------------------------------------
    # COMPLAINT TREND ANALYSIS
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            DATE_FORMAT(created_at, '%Y-%m') AS month,
            COUNT(*) AS complaint_count
        FROM complaints
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month ASC
    """)

    complaint_trends = cursor.fetchall()

    # --------------------------------------------------------
    # BENEFICIARY CONSUMPTION & DEMAND ANALYSIS
    # --------------------------------------------------------

    if selected_shop_id:

        cursor.execute("""
            SELECT
                rt.ration_card_id,
                rt.shop_id,
                rt.commodity_id,
                c.commodity_name,
                COUNT(*) AS transaction_count,
                SUM(rt.quantity_kg) AS total_consumption_kg,
                ROUND(AVG(rt.quantity_kg), 2) AS average_consumption_kg
            FROM ration_transactions rt
            JOIN commodities c
                ON rt.commodity_id = c.commodity_id
            WHERE rt.status = 'COMPLETED'
              AND rt.shop_id = %s
            GROUP BY
                rt.ration_card_id,
                rt.shop_id,
                rt.commodity_id,
                c.commodity_name
            ORDER BY
                rt.ration_card_id,
                total_consumption_kg DESC
        """, (selected_shop_id,))

    else:

        cursor.execute("""
            SELECT
                rt.ration_card_id,
                rt.shop_id,
                rt.commodity_id,
                c.commodity_name,
                COUNT(*) AS transaction_count,
                SUM(rt.quantity_kg) AS total_consumption_kg,
                ROUND(AVG(rt.quantity_kg), 2) AS average_consumption_kg
            FROM ration_transactions rt
            JOIN commodities c
                ON rt.commodity_id = c.commodity_id
            WHERE rt.status = 'COMPLETED'
            GROUP BY
                rt.ration_card_id,
                rt.shop_id,
                rt.commodity_id,
                c.commodity_name
            ORDER BY
                rt.ration_card_id,
                total_consumption_kg DESC
        """)

    beneficiary_consumption = cursor.fetchall()

    # --------------------------------------------------------
    # CLOSE DATABASE
    # --------------------------------------------------------

    cursor.close()
    connection.close()

    return render_template(
        "admin_decision_support.html",
        predictions=predictions,
        anomalies=anomalies,
        recommendations=recommendations,
        shop_scores=shop_scores,
        complaint_trends=complaint_trends,
        beneficiary_consumption=beneficiary_consumption,
        shops=shops,
        selected_shop_id=selected_shop_id
    )
@app.route("/admin/reports")
def admin_reports():

    print("ADMIN REPORTS ROUTE CALLED")

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    report_type = request.args.get("type", "")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    district = request.args.get("district")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # --------------------------------------------------------
    # GET ALL DISTRICTS
    # --------------------------------------------------------

    cursor.execute("""
        SELECT
            district_id,
            district_name
        FROM districts
        ORDER BY district_name
    """)

    districts = cursor.fetchall()

    # --------------------------------------------------------
    # EMPTY REPORT DATA
    # --------------------------------------------------------

    stock_report = []
    complaint_report = []
    rating_report = []
    token_report = []

    ai_prediction_report = []
    anomaly_report = []
    recommendation_report = []

    performance_report = []

    # --------------------------------------------------------
    # STOCK REPORT
    # --------------------------------------------------------

    if report_type == "stock":

        query = """
            SELECT
                fps.shop_code,
                fps.shop_name,
                d.district_name,
                c.commodity_name,
                ss.quantity_kg,
                ss.minimum_threshold_kg,
                ss.last_updated

            FROM shop_stock ss

            LEFT JOIN fair_price_shops fps
                ON ss.shop_id = fps.shop_id

            LEFT JOIN districts d
                ON fps.district_id = d.district_id

            LEFT JOIN commodities c
                ON ss.commodity_id = c.commodity_id

            WHERE 1=1
        """

        params = []

        # DISTRICT FILTER
        if district:
            query += """
                AND d.district_name = %s
            """
            params.append(district)

        query += """
            ORDER BY
                d.district_name,
                fps.shop_code,
                c.commodity_name
        """

        cursor.execute(query, params)

        stock_report = cursor.fetchall()

    # --------------------------------------------------------
    # COMPLAINT REPORT
    # --------------------------------------------------------

    elif report_type == "complaints":
        query = """
            SELECT
                c.complaint_number,
                c.category,
                c.description,
                c.status,
                c.priority,
                c.created_at,
                c.resolved_at,
                fps.shop_code,
                fps.shop_name
            FROM complaints c
            LEFT JOIN fair_price_shops fps
                ON c.shop_id = fps.shop_id
            WHERE 1=1
        """

        params = []

        if from_date:
            query += " AND DATE(c.created_at) >= %s"
            params.append(from_date)

        if to_date:
            query += " AND DATE(c.created_at) <= %s"
            params.append(to_date)

        if district:
            query += """
                AND fps.district_id = (
                    SELECT district_id
                    FROM districts
                    WHERE district_name = %s
                )
            """
            params.append(district)

        query += """
            ORDER BY c.created_at DESC
        """

        cursor.execute(query, params)

        complaint_report = cursor.fetchall()

    # --------------------------------------------------------
    # RATING REPORT
    # --------------------------------------------------------

    elif report_type == "ratings":

        query = """
            SELECT
                fps.shop_code,
                fps.shop_name,
                r.rating,
                r.feedback,
                r.created_at
            FROM ratings r
            LEFT JOIN fair_price_shops fps
                ON r.shop_id = fps.shop_id
            WHERE 1=1
        """

        params = []

        if from_date:
            query += " AND DATE(r.created_at) >= %s"
            params.append(from_date)

        if to_date:
            query += " AND DATE(r.created_at) <= %s"
            params.append(to_date)

        if district:
            query += """
                AND fps.district_id = (
                    SELECT district_id
                    FROM districts
                    WHERE district_name = %s
                )
            """
            params.append(district)

        query += """
            ORDER BY r.created_at DESC
        """

        cursor.execute(query, params)

        rating_report = cursor.fetchall()

    # --------------------------------------------------------
    # TOKEN REPORT
    # --------------------------------------------------------

    elif report_type == "tokens":

        query = """
            SELECT
                rt.token_number,
                rt.shop_code,
                rt.collection_date,
                rt.time_slot,
                rt.status,
                rt.created_at
            FROM ration_tokens rt
            WHERE 1=1
        """

        params = []

        if from_date:
            query += " AND rt.collection_date >= %s"
            params.append(from_date)

        if to_date:
            query += " AND rt.collection_date <= %s"
            params.append(to_date)

        query += """
            ORDER BY
                rt.collection_date DESC,
                rt.created_at DESC
        """

        cursor.execute(query, params)

        token_report = cursor.fetchall()

    # --------------------------------------------------------
    # AI REPORT
    # --------------------------------------------------------

    elif report_type == "ai":

        cursor.execute("""
            SELECT
                fps.shop_code,
                fps.shop_name,
                c.commodity_name,
                ap.prediction_month,
                ap.predicted_quantity_kg,
                ap.confidence_score,
                ap.model_name,
                ap.created_at
            FROM ai_predictions ap
            LEFT JOIN fair_price_shops fps
                ON ap.shop_id = fps.shop_id
            LEFT JOIN commodities c
                ON ap.commodity_id = c.commodity_id
            ORDER BY
                ap.prediction_month DESC,
                ap.created_at DESC
        """)

        ai_prediction_report = cursor.fetchall()

        cursor.execute("""
            SELECT
                anomaly_id,
                shop_id,
                transaction_id,
                anomaly_type,
                anomaly_score,
                description,
                detection_date,
                review_status
            FROM anomaly_results
            ORDER BY detection_date DESC
        """)

        anomaly_report = cursor.fetchall()

        cursor.execute("""
            SELECT
                recommendation_id,
                recommendation_type,
                district_id,
                shop_id,
                title,
                recommendation_text,
                priority,
                status,
                created_at
            FROM ai_recommendations
            ORDER BY created_at DESC
        """)

        recommendation_report = cursor.fetchall()

    # --------------------------------------------------------
    # SHOP PERFORMANCE
    # --------------------------------------------------------

    elif report_type == "performance":

        query = """
            SELECT
                ss.score_id,
                fps.shop_code,
                fps.shop_name,
                ss.evaluation_month,
                ss.rating_score,
                ss.stock_score,
                ss.complaint_score,
                ss.service_score,
                ss.overall_score,
                ss.performance_level,
                ss.calculated_at
            FROM shop_scores ss
            LEFT JOIN fair_price_shops fps
                ON ss.shop_id = fps.shop_id
            WHERE 1=1
        """

        params = []

        if from_date:
            query += " AND ss.evaluation_month >= %s"
            params.append(from_date)

        if to_date:
            query += " AND ss.evaluation_month <= %s"
            params.append(to_date)

        if district:
            query += """
                AND fps.district_id = (
                    SELECT district_id
                    FROM districts
                    WHERE district_name = %s
                )
            """
            params.append(district)

        query += """
            ORDER BY
                ss.evaluation_month DESC,
                ss.calculated_at DESC
        """

        cursor.execute(query, params)

        performance_report = cursor.fetchall()

    # --------------------------------------------------------
    # CLOSE DATABASE
    # --------------------------------------------------------

    cursor.close()
    connection.close()

    # --------------------------------------------------------
    # RENDER TEMPLATE
    # --------------------------------------------------------

    return render_template(
        "admin_reports.html",
        stock_report=stock_report,
        complaint_report=complaint_report,
        rating_report=rating_report,
        token_report=token_report,
        ai_prediction_report=ai_prediction_report,
        anomaly_report=anomaly_report,
        recommendation_report=recommendation_report,
        performance_report=performance_report,
        report_type=report_type,
        districts=districts
    )


@app.route("/admin/reports/export/excel")
def export_report_excel():

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    report_type = request.args.get("type", "")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    data = []

    if report_type == "stock":

        cursor.execute("""
            SELECT
                fps.shop_code AS Shop_Code,
                fps.shop_name AS Shop_Name,
                c.commodity_name AS Commodity,
                ss.quantity_kg AS Quantity_KG,
                ss.minimum_threshold_kg AS Minimum_Threshold_KG,
                ss.last_updated AS Last_Updated
            FROM shop_stock ss
            JOIN fair_price_shops fps
                ON ss.shop_id = fps.shop_id
            JOIN commodities c
                ON ss.commodity_id = c.commodity_id
            ORDER BY fps.shop_code, c.commodity_name
        """)

        data = cursor.fetchall()

    elif report_type == "complaints":

        cursor.execute("""
            SELECT
                cp.complaint_number AS Complaint_Number,
                fps.shop_code AS Shop_Code,
                fps.shop_name AS Shop_Name,
                cp.category AS Category,
                cp.description AS Description,
                cp.priority AS Priority,
                cp.status AS Status,
                cp.created_at AS Created_At,
                cp.resolved_at AS Resolved_At
            FROM complaints cp
            LEFT JOIN fair_price_shops fps
                ON cp.shop_id = fps.shop_id
            ORDER BY cp.created_at DESC
        """)

        data = cursor.fetchall()

    elif report_type == "ratings":

        cursor.execute("""
            SELECT
                r.rating_id AS Rating_ID,
                r.citizen_id AS Citizen_ID,
                fps.shop_code AS Shop_Code,
                fps.shop_name AS Shop_Name,
                r.rating AS Rating,
                r.feedback AS Feedback,
                r.created_at AS Created_At
            FROM ratings r
            LEFT JOIN fair_price_shops fps
                ON r.shop_id = fps.shop_id
            ORDER BY r.created_at DESC
        """)

        data = cursor.fetchall()

    elif report_type == "tokens":

        cursor.execute("""
            SELECT
                rt.token_number AS Token_Number,
                rt.user_id AS User_ID,
                rt.shop_code AS Shop_Code,
                rt.collection_date AS Collection_Date,
                rt.time_slot AS Time_Slot,
                rt.status AS Status,
                rt.created_at AS Created_At
            FROM ration_tokens rt
            ORDER BY rt.collection_date DESC, rt.created_at DESC
        """)

        data = cursor.fetchall()

    elif report_type == "performance":

        cursor.execute("""
            SELECT
                fps.shop_code AS Shop_Code,
                fps.shop_name AS Shop_Name,
                ss.evaluation_month AS Evaluation_Month,
                ss.rating_score AS Rating_Score,
                ss.stock_score AS Stock_Score,
                ss.complaint_score AS Complaint_Score,
                ss.service_score AS Service_Score,
                ss.overall_score AS Overall_Score,
                ss.performance_level AS Performance_Level
            FROM shop_scores ss
            LEFT JOIN fair_price_shops fps
                ON ss.shop_id = fps.shop_id
            ORDER BY ss.evaluation_month DESC
        """)

        data = cursor.fetchall()

    elif report_type == "ai":

        cursor.execute("""
            SELECT
                ap.prediction_id AS Prediction_ID,
                fps.shop_code AS Shop_Code,
                fps.shop_name AS Shop_Name,
                c.commodity_name AS Commodity,
                ap.prediction_month AS Prediction_Month,
                ap.predicted_quantity_kg AS Predicted_Quantity_KG,
                ap.confidence_score AS Confidence_Score,
                ap.model_name AS Model_Name
            FROM ai_predictions ap
            LEFT JOIN fair_price_shops fps
                ON ap.shop_id = fps.shop_id
            LEFT JOIN commodities c
                ON ap.commodity_id = c.commodity_id
            ORDER BY ap.prediction_month DESC
        """)

        data = cursor.fetchall()

    cursor.close()
    connection.close()



    
        

    if not data:
        return "No report data available."

    df = pd.DataFrame(data)

    file_path = "pds_report.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"{report_type}_report.xlsx"
    )
@app.route("/admin/reports/export/pdf")
def export_report_pdf():

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    report_type = request.args.get("type", "")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    data = []
    title = "PDS Report"

    if report_type == "performance":

        title = "Shop Performance Report"

        cursor.execute("""
            SELECT
                fps.shop_code AS shop_code,
                fps.shop_name AS shop_name,
                ss.evaluation_month AS evaluation_month,
                ss.rating_score AS rating_score,
                ss.stock_score AS stock_score,
                ss.complaint_score AS complaint_score,
                ss.service_score AS service_score,
                ss.overall_score AS overall_score,
                ss.performance_level AS performance_level
            FROM shop_scores ss
            LEFT JOIN fair_price_shops fps
                ON ss.shop_id = fps.shop_id
            ORDER BY ss.evaluation_month DESC
        """)

        data = cursor.fetchall()

    elif report_type == "stock":

        title = "Stock Report"

        cursor.execute("""
            SELECT
                fps.shop_code AS shop_code,
                fps.shop_name AS shop_name,
                c.commodity_name AS commodity,
                ss.quantity_kg AS quantity_kg,
                ss.minimum_threshold_kg AS minimum_threshold_kg
            FROM shop_stock ss
            JOIN fair_price_shops fps
                ON ss.shop_id = fps.shop_id
            JOIN commodities c
                ON ss.commodity_id = c.commodity_id
            ORDER BY fps.shop_code, c.commodity_name
        """)

        data = cursor.fetchall()

    elif report_type == "complaints":

        title = "Complaint Report"

        cursor.execute("""
            SELECT
                cp.complaint_number AS complaint_number,
                fps.shop_code AS shop_code,
                cp.category AS category,
                cp.priority AS priority,
                cp.status AS status,
                cp.created_at AS created_at
            FROM complaints cp
            LEFT JOIN fair_price_shops fps
                ON cp.shop_id = fps.shop_id
            ORDER BY cp.created_at DESC
        """)

        data = cursor.fetchall()

    elif report_type == "ratings":

        title = "Rating & Feedback Report"

        cursor.execute("""
            SELECT
                fps.shop_code AS shop_code,
                r.rating AS rating,
                r.feedback AS feedback,
                r.created_at AS created_at
            FROM ratings r
            LEFT JOIN fair_price_shops fps
                ON r.shop_id = fps.shop_id
            ORDER BY r.created_at DESC
        """)

        data = cursor.fetchall()

    elif report_type == "tokens":

        title = "Token & Distribution Report"

        cursor.execute("""
            SELECT
                rt.token_number AS token_number,
                rt.shop_code AS shop_code,
                rt.collection_date AS collection_date,
                rt.time_slot AS time_slot,
                rt.status AS status
            FROM ration_tokens rt
            ORDER BY rt.collection_date DESC
        """)

        data = cursor.fetchall()

    cursor.close()
    connection.close()

    if not data:
        return "No report data available."

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER

    pdf_buffer = io.BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4),
        rightMargin=25,
        leftMargin=25,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.alignment = TA_CENTER

    elements = []

    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 15))

    columns = list(data[0].keys())

    table_data = [columns]

    for row in data:
        table_data.append([
            str(row[column]) if row[column] is not None else ""
            for column in columns
        ])

    table = Table(
        table_data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ])
    )

    elements.append(table)

    document.build(elements)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{report_type}_report.pdf",
        mimetype="application/pdf"
    )
@app.route("/citizen/service-history")
def citizen_service_history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "CITIZEN":
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT citizen_id
        FROM citizens
        WHERE user_id = %s
    """, (session["user_id"],))

    citizen = cursor.fetchone()

    if not citizen:
        cursor.close()
        connection.close()
        return "Citizen profile not found", 404

    citizen_id = citizen["citizen_id"]

    # Ration collection history
    cursor.execute("""
        SELECT
            rt.transaction_id,
            rt.transaction_date,
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            rt.quantity_kg,
            rt.verification_method,
            rt.status
        FROM ration_transactions rt
        INNER JOIN ration_cards rc
            ON rt.ration_card_id = rc.ration_card_id
        INNER JOIN fair_price_shops fps
            ON rt.shop_id = fps.shop_id
        INNER JOIN commodities c
            ON rt.commodity_id = c.commodity_id
        WHERE rc.head_citizen_id = %s
        ORDER BY rt.transaction_date DESC
    """, (citizen_id,))

    collections = cursor.fetchall()

    # Token history
    cursor.execute("""
        SELECT
            token_id,
            shop_code,
            collection_date,
            time_slot,
            token_number,
            status,
            created_at
        FROM ration_tokens
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (session["user_id"],))

    tokens = cursor.fetchall()

    # Complaint history
    cursor.execute("""
        SELECT
            complaint_number,
            category,
            description,
            status,
            priority,
            created_at,
            resolved_at
        FROM complaints
        WHERE citizen_id = %s
        ORDER BY created_at DESC
    """, (citizen_id,))

    complaints = cursor.fetchall()

    # Home delivery history
    cursor.execute("""
        SELECT
            delivery_request_id,
            request_number,
            eligibility_reason,
            request_notes,
            status,
            admin_remarks,
            requested_at,
            approved_at,
            delivered_at
        FROM delivery_requests
        WHERE citizen_id = %s
        ORDER BY requested_at DESC
    """, (citizen_id,))

    deliveries = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "citizen_service_history.html",
        collections=collections,
        tokens=tokens,
        complaints=complaints,
        deliveries=deliveries
    )
def update_shop_rating_score(connection, shop_id):
    cursor = connection.cursor(dictionary=True)

    try:
        # Get average rating for this shop
        cursor.execute("""
            SELECT
                AVG(rating) AS average_rating
            FROM ratings
            WHERE shop_id = %s
        """, (shop_id,))

        result = cursor.fetchone()

        if not result or result["average_rating"] is None:
            rating_score = 0.00
        else:
            # Convert 1–5 rating into 0–100 score
            rating_score = (
                float(result["average_rating"]) / 5
            ) * 100

        rating_score = round(
            max(0, min(100, rating_score)),
            2
        )

        # Check whether this shop already has a score
        cursor.execute("""
            SELECT score_id
            FROM shop_scores
            WHERE shop_id = %s
              AND evaluation_month = DATE_FORMAT(
                  CURDATE(),
                  '%Y-%m-01'
              )
        """, (shop_id,))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
                UPDATE shop_scores
                SET rating_score = %s
                WHERE score_id = %s
            """, (
                rating_score,
                existing["score_id"]
            ))

        else:

            cursor.execute("""
                INSERT INTO shop_scores
                (
                    shop_id,
                    evaluation_month,
                    rating_score,
                    stock_score,
                    complaint_score,
                    service_score,
                    overall_score,
                    performance_level
                )
                VALUES
                (
                    %s,
                    DATE_FORMAT(CURDATE(), '%Y-%m-01'),
                    %s,
                    0.00,
                    0.00,
                    0.00,
                    %s,
                    %s
                )
            """, (
                shop_id,
                rating_score,
                rating_score,
                "AVERAGE"
            ))

        connection.commit()

    finally:
        cursor.close()
def generate_stock_recommendations(connection):

    recommendation_connection = get_db_connection()
    cursor = recommendation_connection.cursor(dictionary=True)

    # Get the latest prediction for every shop + commodity
    cursor.execute("""
        SELECT
            ap.shop_id,
            ap.commodity_id,
            ap.prediction_month,
            ap.predicted_quantity_kg,
            fps.shop_code,
            fps.shop_name,
            c.commodity_name,
            ss.quantity_kg AS current_stock
        FROM ai_predictions ap

        INNER JOIN fair_price_shops fps
            ON ap.shop_id = fps.shop_id

        INNER JOIN commodities c
            ON ap.commodity_id = c.commodity_id

        LEFT JOIN shop_stock ss
            ON ap.shop_id = ss.shop_id
            AND ap.commodity_id = ss.commodity_id

        INNER JOIN (
            SELECT
                shop_id,
                commodity_id,
                MAX(prediction_id) AS latest_prediction_id
            FROM ai_predictions
            GROUP BY shop_id, commodity_id
        ) latest
            ON ap.prediction_id = latest.latest_prediction_id

        WHERE ap.predicted_quantity_kg > COALESCE(ss.quantity_kg, 0)
    """)

    records = cursor.fetchall()

    for row in records:

        current_stock = float(row["current_stock"] or 0)
        predicted_demand = float(row["predicted_quantity_kg"] or 0)

        stock_gap = predicted_demand - current_stock

        if stock_gap <= 0:
            continue

        # Priority based on stock gap
        if current_stock == 0 or current_stock < predicted_demand * 0.30:
            priority = "HIGH"
        elif current_stock < predicted_demand * 0.60:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        title = "Stock Replenishment Review"

        recommendation_text = (
            f"{row['shop_name']} ({row['shop_code']}) has "
            f"{current_stock:.2f} KG of {row['commodity_name']} stock "
            f"against predicted demand of {predicted_demand:.2f} KG. "
            f"The potential stock gap is {stock_gap:.2f} KG. "
            f"Consider reviewing replenishment requirements."
        )

        # Avoid duplicate recommendation
        cursor.execute("""
            SELECT recommendation_id
            FROM ai_recommendations
            WHERE shop_id = %s
              AND recommendation_type = 'STOCK'
              AND title = %s
              AND status = 'NEW'
              AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            LIMIT 1
        """, (
            row["shop_id"],
            title
        ))

        existing = cursor.fetchone()

        if not existing:

            cursor.execute("""
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
                SELECT
                    'STOCK',
                    fps.district_id,
                    %s,
                    %s,
                    %s,
                    %s,
                    'NEW'
                FROM fair_price_shops fps
                WHERE fps.shop_id = %s
            """, (
                row["shop_id"],
                title,
                recommendation_text,
                priority,
                row["shop_id"]
            ))

    recommendation_connection.commit()
    cursor.close()
    recommendation_connection.close()

@app.route("/admin/delivery-requests/<int:request_id>/status", methods=["POST"])
def update_delivery_status(request_id):

    if "user_id" not in session or session.get("role") != "ADMIN":
        return redirect(url_for("login"))

    new_status = request.form.get("status")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        if new_status == "OUT_FOR_DELIVERY":

            cursor.execute("""
                UPDATE delivery_requests
                SET status = 'OUT_FOR_DELIVERY',
                    admin_remarks = 'Ration delivery is out for delivery'
                WHERE delivery_request_id = %s
                  AND status = 'APPROVED'
            """, (request_id,))

        elif new_status == "DELIVERED":

            cursor.execute("""
                UPDATE delivery_requests
                SET status = 'DELIVERED',
                    delivered_at = NOW(),
                    admin_remarks = 'Ration delivery completed successfully'
                WHERE delivery_request_id = %s
                  AND status = 'OUT_FOR_DELIVERY'
            """, (request_id,))

        else:
            return redirect(url_for("admin_delivery_requests"))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("admin_delivery_requests"))



if __name__ == "__main__":

    app.run(
        debug=True
    )