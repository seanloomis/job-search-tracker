import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime, timedelta
import json

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="Job Search Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# GOOGLE SHEETS CONNECTION
# ============================================
@st.cache_resource
def get_gsheet_connection():
    """Connect to Google Sheets using service account credentials"""
    try:
        # Credentials will be stored in Streamlit secrets
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(st.secrets["sheet_id"]).worksheet("Opportunities")
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

@st.cache_data(ttl=60)
def load_data():
    """Load data from Google Sheets with caching"""
    sheet = get_gsheet_connection()
    if sheet is None:
        return pd.DataFrame()
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Clean and format
    if not df.empty:
        df['Date Added'] = pd.to_datetime(df['Date Added'], errors='coerce')
        df['Last Action'] = pd.to_datetime(df['Last Action'], errors='coerce')
    
    return df

def update_company(row_num, column, value):
    """Update a single cell in the sheet"""
    sheet = get_gsheet_connection()
    if sheet:
        # Column mapping
        cols = {
            'Priority': 1, 'Company Name': 2, 'Industry': 3, 'Type': 4,
            'Location': 5, 'Job Link': 6, 'Website': 7, 'Contact Person/Role': 8,
            'Status': 9, 'Date Added': 10, 'Last Action': 11, 'Notes': 12
        }
        sheet.update_cell(row_num + 2, cols[column], value)  # +2 for header and 0-indexing
        st.cache_data.clear()

def add_company(company_data):
    """Add a new company to the sheet"""
    sheet = get_gsheet_connection()
    if sheet:
        sheet.append_row(company_data)
        st.cache_data.clear()

# ============================================
# CUSTOM CSS
# ============================================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .high-priority {
        color: #d62728;
        font-weight: bold;
    }
    .medium-priority {
        color: #ff7f0e;
        font-weight: bold;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.85rem;
        font-weight: bold;
    }
    .status-new { background: #e3f2fd; color: #1976d2; }
    .status-researching { background: #fff3e0; color: #f57c00; }
    .status-applied { background: #f3e5f5; color: #7b1fa2; }
    .status-interviewing { background: #e8f5e9; color: #388e3c; }
    .status-offer { background: #c8e6c9; color: #2e7d32; }
</style>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("### 🎯 Job Search Tracker")
    st.markdown("---")
    
    # Filters
    st.markdown("#### Filters")
    df = load_data()
    
    if not df.empty:
        industries = ["All"] + sorted(df['Industry'].unique().tolist())
        selected_industry = st.selectbox("Industry", industries)
        
        priorities = ["All"] + sorted(df['Priority'].unique().tolist())
        selected_priority = st.selectbox("Priority", priorities)
        
        statuses = ["All"] + sorted(df['Status'].unique().tolist())
        selected_status = st.selectbox("Status", statuses)
        
        view_mode = st.radio("View", ["Kanban Board", "Table View", "Calendar"])
    
    st.markdown("---")
    st.markdown("#### Quick Actions")
    if st.button("➕ Add Company", use_container_width=True):
        st.session_state.show_add_form = True
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.markdown(f"**Last updated:** {datetime.now().strftime('%H:%M')}")

# ============================================
# MAIN CONTENT
# ============================================

st.markdown('<p class="main-header">🎯 Job Search Command Center</p>', unsafe_allow_html=True)

# Load data
df = load_data()

if df.empty:
    st.warning("No data found. Make sure your Google Sheet is properly connected.")
    st.stop()

# Apply filters
filtered_df = df.copy()
if selected_industry != "All":
    filtered_df = filtered_df[filtered_df['Industry'] == selected_industry]
if selected_priority != "All":
    filtered_df = filtered_df[filtered_df['Priority'] == selected_priority]
if selected_status != "All":
    filtered_df = filtered_df[filtered_df['Status'] == selected_status]

# ============================================
# METRICS ROW
# ============================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Companies", len(df))

with col2:
    applied = len(df[df['Status'] == 'Applied'])
    st.metric("Applied", applied)

with col3:
    interviewing = len(df[df['Status'] == 'Interviewing'])
    st.metric("Interviewing", interviewing)

with col4:
    high_priority = len(df[df['Priority'] == 'High'])
    st.metric("High Priority", high_priority)

with col5:
    # Companies needing follow-up (applied 5+ days ago, no last action)
    needs_followup = 0
    for _, row in df.iterrows():
        if row['Status'] == 'Applied' and pd.notna(row['Date Added']):
            days_since = (datetime.now() - row['Date Added']).days
            if days_since >= 5 and (pd.isna(row['Last Action']) or (datetime.now() - row['Last Action']).days >= 5):
                needs_followup += 1
    st.metric("Need Follow-up", needs_followup, delta=f"-{needs_followup}" if needs_followup > 0 else None)

st.markdown("---")

# ============================================
# VIEW MODES
# ============================================

if view_mode == "Kanban Board":
    # Kanban board view
    statuses_ordered = ['To Research', 'Researching', 'Applied', 'Interviewing', 'Offer', 'Rejected']
    
    cols = st.columns(len(statuses_ordered))
    
    for idx, status in enumerate(statuses_ordered):
        with cols[idx]:
            status_df = filtered_df[filtered_df['Status'] == status]
            st.markdown(f"### {status}")
            st.markdown(f"**{len(status_df)} companies**")
            
            for _, row in status_df.iterrows():
                with st.expander(f"{row['Company Name']}"):
                    priority_class = "high-priority" if row['Priority'] == 'High' else "medium-priority"
                    st.markdown(f"<span class='{priority_class}'>{row['Priority']} Priority</span>", unsafe_allow_html=True)
                    st.write(f"**Industry:** {row['Industry']}")
                    st.write(f"**Type:** {row['Type']}")
                    st.write(f"**Location:** {row['Location']}")
                    
                    if row['Job Link']:
                        st.markdown(f"[Job Posting]({row['Job Link']})")
                    if row['Website']:
                        st.markdown(f"[Company Website]({row['Website']})")
                    
                    if row['Notes']:
                        st.info(row['Notes'])
                    
                    # Quick actions
                    new_status = st.selectbox(
                        "Change Status",
                        statuses_ordered,
                        index=statuses_ordered.index(status),
                        key=f"status_{row['Company Name']}"
                    )
                    if new_status != status:
                        if st.button(f"Update", key=f"update_{row['Company Name']}"):
                            row_num = df[df['Company Name'] == row['Company Name']].index[0]
                            update_company(row_num, 'Status', new_status)
                            update_company(row_num, 'Last Action', datetime.now().strftime('%Y-%m-%d'))
                            st.success(f"Updated {row['Company Name']}")
                            st.rerun()

elif view_mode == "Table View":
    # Table view with editing
    st.markdown("### All Companies")
    
    # Display dataframe with sorting
    display_cols = ['Priority', 'Company Name', 'Industry', 'Type', 'Location', 'Status', 'Date Added', 'Last Action']
    display_df = filtered_df[display_cols].copy()
    
    # Format dates
    if not display_df.empty:
        display_df['Date Added'] = display_df['Date Added'].dt.strftime('%Y-%m-%d')
        display_df['Last Action'] = display_df['Last Action'].dt.strftime('%Y-%m-%d')
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=600
    )
    
    # Detail view for selected company
    st.markdown("---")
    st.markdown("### Company Details")
    
    company_names = filtered_df['Company Name'].tolist()
    selected_company = st.selectbox("Select company to view/edit", company_names)
    
    if selected_company:
        company_row = filtered_df[filtered_df['Company Name'] == selected_company].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Priority:** {company_row['Priority']}")
            st.write(f"**Industry:** {company_row['Industry']}")
            st.write(f"**Type:** {company_row['Type']}")
            st.write(f"**Location:** {company_row['Location']}")
            st.write(f"**Status:** {company_row['Status']}")
        
        with col2:
            if company_row['Job Link']:
                st.markdown(f"[Job Posting]({company_row['Job Link']})")
            if company_row['Website']:
                st.markdown(f"[Company Website]({company_row['Website']})")
            st.write(f"**Contact:** {company_row['Contact Person/Role']}")
            st.write(f"**Date Added:** {company_row['Date Added']}")
            st.write(f"**Last Action:** {company_row['Last Action']}")
        
        st.markdown("**Notes:**")
        st.write(company_row['Notes'])

elif view_mode == "Calendar":
    # Calendar view - upcoming deadlines and follow-ups
    st.markdown("### Timeline View")
    
    # Create timeline of actions
    timeline_data = []
    
    for _, row in filtered_df.iterrows():
        if pd.notna(row['Date Added']):
            timeline_data.append({
                'Date': row['Date Added'],
                'Event': f"Added: {row['Company Name']}",
                'Type': 'Added'
            })
        
        if pd.notna(row['Last Action']):
            timeline_data.append({
                'Date': row['Last Action'],
                'Event': f"Action: {row['Company Name']}",
                'Type': 'Action'
            })
        
        # Add follow-up reminders
        if row['Status'] == 'Applied' and pd.notna(row['Date Added']):
            followup_date = row['Date Added'] + timedelta(days=7)
            timeline_data.append({
                'Date': followup_date,
                'Event': f"Follow-up: {row['Company Name']}",
                'Type': 'Reminder'
            })
    
    if timeline_data:
        timeline_df = pd.DataFrame(timeline_data)
        timeline_df = timeline_df.sort_values('Date', ascending=False)
        
        st.dataframe(timeline_df, use_container_width=True, height=600)

# ============================================
# ADD COMPANY FORM (Modal-style)
# ============================================
if 'show_add_form' in st.session_state and st.session_state.show_add_form:
    with st.form("add_company_form"):
        st.markdown("### ➕ Add New Company")
        
        col1, col2 = st.columns(2)
        
        with col1:
            company_name = st.text_input("Company Name *")
            industry = st.selectbox("Industry", ["HealthTech", "MedTech", "FinTech", "SaaS", "Other"])
            job_type = st.selectbox("Type", ["Full-time", "Freelance", "Both"])
            location = st.text_input("Location")
        
        with col2:
            priority = st.selectbox("Priority", ["High", "Medium", "Low"])
            status = st.selectbox("Status", ["To Research", "Researching", "Applied"])
            job_link = st.text_input("Job Link (URL)")
            website = st.text_input("Website (URL)")
        
        contact = st.text_input("Contact Person/Role")
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Add Company")
        
        if submitted:
            if company_name:
                today = datetime.now().strftime('%Y-%m-%d')
                new_company = [
                    priority, company_name, industry, job_type, location,
                    job_link, website, contact, status, today, '', notes
                ]
                add_company(new_company)
                st.success(f"✅ Added {company_name}")
                st.session_state.show_add_form = False
                st.rerun()
            else:
                st.error("Company name is required")
    
    if st.button("Cancel"):
        st.session_state.show_add_form = False
        st.rerun()

# ============================================
# DAILY INSIGHTS
# ============================================
st.markdown("---")
st.markdown("### 📊 Today's Insights")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 🔥 Hot Leads")
    high_priority_new = df[(df['Priority'] == 'High') & (df['Status'].isin(['To Research', 'Researching']))]
    if not high_priority_new.empty:
        for _, row in high_priority_new.head(3).iterrows():
            st.markdown(f"- **{row['Company Name']}** ({row['Industry']})")
    else:
        st.info("No high-priority leads to research")

with col2:
    st.markdown("#### ⚡ Need Follow-up")
    for _, row in df.iterrows():
        if row['Status'] == 'Applied' and pd.notna(row['Date Added']):
            days_since = (datetime.now() - row['Date Added']).days
            if days_since >= 5:
                st.markdown(f"- **{row['Company Name']}** ({days_since} days)")

with col3:
    st.markdown("#### 🎯 Today's Goal")
    st.markdown("- Apply to 2-3 companies")
    st.markdown("- Send 3 network messages")
    st.markdown("- Follow up on 2 applications")
    
    if st.button("✅ I completed today's goals!"):
        st.balloons()
        st.success("Amazing work! Keep the momentum going! 🚀")
