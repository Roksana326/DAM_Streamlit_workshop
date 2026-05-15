import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# Page setup
# =========================================================
st.set_page_config(
    page_title="Uber Ride Analytics Dashboard",
    layout="wide"
)

DATA_PATH = "ncr_ride_bookings.csv"


# =========================================================
# Load and prepare data
# =========================================================
#region Przygotowanie danych
rides = pd.read_csv(DATA_PATH)

rides["Date"] = pd.to_datetime(rides["Date"])

rides["Is Completed"] = rides["Booking Status"] == "Completed"
rides["Is Cancelled"] = rides["Booking Status"].str.contains("Cancelled", na=False)
rides["Is Incomplete"] = rides["Booking Status"].str.contains("Incomplete", na=False)
rides["Is No Driver Found"] = rides["Booking Status"].str.contains("No Driver", na=False)
rides["Is Not Completed"] = ~rides["Is Completed"]
#endregion

# =========================================================
# Header
# =========================================================
st.title("Uber Ride Analytics Dashboard")
st.caption("A Streamlit dashboard for monitoring bookings, revenue, cancellations, service quality and ratings.")


# =========================================================
# Sidebar filters
# =========================================================
st.sidebar.header("Dashboard controls")
st.sidebar.caption("Global filters applied across all tabs.")

original_rides = rides.copy()

selected_date_range = st.sidebar.date_input(
    "Date range",
    value=(original_rides["Date"].min().date(), original_rides["Date"].max().date()),
    min_value=original_rides["Date"].min().date(),
    max_value=original_rides["Date"].max().date(),
)

vehicle_options = ["All"] + sorted(original_rides["Vehicle Type"].unique())
selected_vehicle = st.sidebar.selectbox("Vehicle type", vehicle_options)

if len(selected_date_range) == 2:
    start_date, end_date = selected_date_range
    rides = rides[
        (rides["Date"] >= pd.to_datetime(start_date))
        & (rides["Date"] <= pd.to_datetime(end_date))
    ]

if selected_vehicle != "All":
    rides = rides[rides["Vehicle Type"] == selected_vehicle]

completed_rides = rides[rides["Is Completed"]]
not_completed_rides = rides[rides["Is Not Completed"]]

if completed_rides.empty:
    st.warning("Selected filters contain no completed rides. Some charts may be unavailable.")
    

# =========================================================
# Tabs
# =========================================================
tab_full, tab_cancellations, tab_ratings = st.tabs(
    ["Overview", "Cancellations & issues", "Ratings & time"]
)


# =========================================================
# Tab 1: Overview
# =========================================================
#region Przygotowanie danych do zakładki
total_bookings = round(len(rides),0)
success_rate = round(rides["Is Completed"].mean() * 100,2)
cancellation_rate = round(rides["Is Cancelled"].mean() * 100,2)
total_revenue = round(completed_rides["Booking Value"].sum()/1000,0)
avg_distance = round(completed_rides["Ride Distance"].mean(),2)

daily_bookings = rides.groupby("Date").size().reset_index(name="Bookings")

status_overview = rides["Booking Status"].value_counts().reset_index()
status_overview.columns = ["Status", "Bookings"]

revenue_by_vehicle = (
    completed_rides
    .groupby("Vehicle Type")["Booking Value"]
    .sum()
    .reset_index()
    .sort_values("Booking Value", ascending=False)
)

revenue_by_payment = (
    completed_rides
    .groupby("Payment Method")["Booking Value"]
    .sum()
    .reset_index()
    .sort_values("Booking Value", ascending=False)
)
#endregion

with tab_full:
    st.subheader("Overview")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Bookings", total_bookings)
    col2.metric("Success rate", str(success_rate) + "%")
    col3.metric("Cancellation rate", str(cancellation_rate) + "%")
    col4.metric("Revenue", "₹" + str(total_revenue) + "tys")
    col5.metric("Avg distance", str(round(avg_distance,2)) + "km")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Bookings over time")
        fig = px.line(daily_bookings, x="Date", y="Bookings")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### Booking status overview")
        fig = px.pie(status_overview, names="Status", values="Bookings", hole=0.35)
        st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Revenue by vehicle type")
        fig = px.bar(revenue_by_vehicle, x="Vehicle Type", y="Booking Value")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### Revenue by payment method")
        fig = px.bar(revenue_by_payment, x="Payment Method", y="Booking Value")
        st.plotly_chart(fig, use_container_width=True)

    
    st.markdown("#### Ride distance vs booking value")
    st.caption("Each point is one completed ride. Bubble size represents booking value.")
    fig = px.scatter(
        completed_rides,
        x="Ride Distance",
        y="Booking Value",
        hover_data=["Payment Method", "Pickup Location", "Drop Location"],
    )
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# Tab 2: Cancellations & issues
# =========================================================
#region Przygotowanie danych do zakładki
cancellation_rate = round(rides["Is Cancelled"].mean() * 100,2)
incomplete_rate = round(rides["Is Incomplete"].mean() * 100,2)
no_driver_rate = round(rides["Is No Driver Found"].mean() * 100,2)

cancelled_count = rides["Is Cancelled"].sum()
incomplete_count = rides["Is Incomplete"].sum()
no_driver_count = rides["Is No Driver Found"].sum()

issue_status = not_completed_rides["Booking Status"].value_counts().reset_index()
issue_status.columns = ["Booking Status", "Bookings"]
#endregion

with tab_cancellations:
    st.subheader("Cancellations & issues")

    col1, col2, col3 = st.columns(3)
    col1.metric("Cancellation rate", str(cancellation_rate) + "%")
    col2.metric("Incomplete rate", str(incomplete_rate) + "%")
    col3.metric("No driver rate", str(no_driver_rate) + "%")

    st.divider()
    
    issue_type = st.radio(
        "Issue focus",
        ["All issues", "Customer cancellations", "Driver cancellations", "Incomplete rides"],
        horizontal=True,
    )

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Non-successful bookings")
        fig = px.bar(issue_status, x="Bookings", y="Booking Status", orientation="h")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        if issue_type == "Customer cancellations":
            st.markdown("#### Customer cancellation reasons")
            data = rides["Reason for cancelling by Customer"].dropna().value_counts().reset_index()
            data.columns = ["Reason", "Count"]
            fig = px.pie(data, names="Reason", values="Count", hole=0.35)
            st.plotly_chart(fig, use_container_width=True)

        elif issue_type == "Driver cancellations":
            st.markdown("#### Driver cancellation reasons")
            data = rides["Driver Cancellation Reason"].dropna().value_counts().reset_index()
            data.columns = ["Reason", "Count"]
            fig = px.pie(data, names="Reason", values="Count", hole=0.35)
            st.plotly_chart(fig, use_container_width=True)

        elif issue_type == "Incomplete rides":
            st.markdown("#### Incomplete ride reasons")
            data = rides["Incomplete Rides Reason"].dropna().value_counts().reset_index()
            data.columns = ["Reason", "Count"]
            fig = px.pie(data, names="Reason", values="Count", hole=0.35)
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.markdown("#### Issue breakdown")
            data = pd.DataFrame({
                "Issue type": ["Cancelled", "Incomplete", "No driver found"],
                "Count": [cancelled_count, incomplete_count, no_driver_count]
            })
            fig = px.pie(data, names="Issue type", values="Count", hole=0.35)
            st.plotly_chart(fig, use_container_width=True)


# =========================================================
# Tab 3: Ratings & time
# =========================================================
#region Przygotowanie danych do zakładki
avg_customer_rating = round(completed_rides["Customer Rating"].mean(),2)
avg_driver_rating = round(completed_rides["Driver Ratings"].mean(),2)
avg_vtat = round(rides["Avg VTAT"].mean(),2)
avg_ctat = round(completed_rides["Avg CTAT"].mean(),2)

rating_pairs = completed_rides.groupby(["Driver Ratings", "Customer Rating"]).size().reset_index(name="Number of rides")
#endregion

with tab_ratings:
    st.subheader("Ratings & time")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg customer rating", avg_customer_rating)
    col2.metric("Avg driver rating", avg_driver_rating)
    col3.metric("Avg VTAT", str(avg_vtat) + " min")
    col4.metric("Avg CTAT", str(avg_ctat) + " min")


    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Customer rating distribution")
        fig = px.histogram(completed_rides, x="Customer Rating", nbins=20)
        fig.update_xaxes(range=[2.8, 5.2])
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### Driver rating distribution")
        fig = px.histogram(completed_rides, x="Driver Ratings", nbins=20)
        fig.update_xaxes(range=[2.8, 5.2])
        st.plotly_chart(fig, use_container_width=True)

    metric_focus = st.selectbox("Time metric focus", ["Avg VTAT", "Avg CTAT"])

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Driver rating vs customer rating")
        fig = px.scatter(
            rating_pairs,
            x="Driver Ratings",
            y="Customer Rating",
            size="Number of rides",
            hover_data=["Number of rides"],
        )
        fig.update_xaxes(range=[2.8, 5.2])
        fig.update_yaxes(range=[2.8, 5.2])
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown(f"#### {metric_focus} by customer rating")
        fig = px.box(completed_rides, x="Customer Rating", y=metric_focus)
        fig.update_xaxes(range=[2.8, 5.2])
        st.plotly_chart(fig, use_container_width=True)