
import streamlit as st
from PIL import Image
import pymysql
import geocoder
import socket
import secrets
import platform
from geopy.geocoders import Nominatim
import os
import time, datetime
import fitz
import google.generativeai as genai
import json
import base64
from io import BytesIO
import pandas as pd
import re
import phonenumbers
from phonenumbers import COUNTRY_CODE_TO_REGION_CODE
import pycountry
import pickle

#DATA NEEDED TO RUN THE APP FROM HOSTING SIDE 
api_keyy = ""

DB_HOST = '127.0.0.1'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'resume_data'


#credentials checking

def country_codes() :
    country_code_map = {}

    for code, regions in COUNTRY_CODE_TO_REGION_CODE.items():
        for region in regions:
            try:
                country = pycountry.countries.get(alpha_2=region)
                country_name = country.name
                country_code_map[f"{country_name} (+{code})"] = code
            except:
                continue
    sorted_country_options = sorted(country_code_map.keys())

    return sorted_country_options,country_code_map


def is_valid_number(phone_number):
    return phone_number.isdigit() and len(phone_number) == 10

def is_valid_gmail(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@gmail\.com$"
    return re.match(pattern, email) is not None

#database section

# Database configuration

def connect_to_mysql():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)



def connect_to_db():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)

def table_names() :
    user_table_name = "user_data"
    fback_table_name = "user_feedback"
    return user_table_name, fback_table_name



def init_db():
    try:
        conn = connect_to_mysql()
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME};")
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Database creation failed: {e}")
        return

    try:
        conn = connect_to_db()
        cur = conn.cursor()
        user_table,fback_table = table_names()
        user_data_sql = "CREATE TABLE IF NOT EXISTS " + user_table + """  (
            ID INT NOT NULL AUTO_INCREMENT,
            sec_token VARCHAR(20) NOT NULL,
            ip_add VARCHAR(50),
            host_name VARCHAR(50),
            dev_user VARCHAR(50),
            os_name_ver VARCHAR(50),
            latlong VARCHAR(50),
            city VARCHAR(50),
            state VARCHAR(50),
            country VARCHAR(50),
            act_name VARCHAR(50) NOT NULL,
            act_mail VARCHAR(50) NOT NULL,
            act_mob VARCHAR(20) NOT NULL,
            Name VARCHAR(500) NOT NULL,
            Email_ID VARCHAR(500) NOT NULL,
            resume_score INT NOT NULL,
            Timestamp VARCHAR(50) NOT NULL,
            Page_no INT NOT NULL,
            Predicted_Field VARCHAR(100) NOT NULL,
            User_level VARCHAR(20) NOT NULL,
            Actual_skills TEXT NOT NULL,
            Recommended_skills TEXT NOT NULL,
            pdf_name VARCHAR(100) NOT NULL,
            PRIMARY KEY (ID)
            );
        """

        user_feedback_sql = "CREATE TABLE IF NOT EXISTS " + fback_table + """ (
            ID INT NOT NULL AUTO_INCREMENT,
            feed_name VARCHAR(50) NOT NULL,
            feed_email VARCHAR(50) NOT NULL,
            feed_score VARCHAR(5) NOT NULL,
            comments VARCHAR(100) NULL,
            Timestamp VARCHAR(50) NOT NULL,
            PRIMARY KEY (ID)
        );
        """

        cur.execute(user_data_sql)
        cur.execute(user_feedback_sql)

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        st.error(f"Table creation failed: {e}")


def insert_data(sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
                act_name, act_mail, act_mob, name, email, res_score, timestamp, no_of_pages,
                reco_field, cand_level, skills, recommended_skills, pdf_name):
    try:
        user_table_name,_ = table_names()
        conn = connect_to_db()
        cur = conn.cursor()

        insert_sql = "INSERT INTO " + user_table_name + """ (
                sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country,
                act_name, act_mail, act_mob, Name, Email_ID, resume_score, Timestamp, Page_no,
                Predicted_Field, User_level, Actual_skills, Recommended_skills, pdf_name
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

        rec_values = (
            str(sec_token), str(ip_add), host_name, dev_user, os_name_ver, str(latlong), city, state, country,
            act_name, act_mail, act_mob, name, email, str(res_score), timestamp, str(no_of_pages),
            reco_field, cand_level, skills, recommended_skills, pdf_name
        )

        cur.execute(insert_sql, rec_values)
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        st.error(f"Failed to insert user data: {e}")

def insertf_data(feed_name,feed_email,feed_score,comments,Timestamp):
    try:
        _,DBf_table_name = table_names()
        conn = connect_to_db()
        cur = conn.cursor()
        insertfeed_sql = "INSERT INTO " + DBf_table_name + """ 
            (feed_name, feed_email, feed_score, comments, Timestamp) 
            VALUES (%s, %s, %s, %s, %s)
        """
        rec_values = (feed_name, feed_email, feed_score, comments, Timestamp)

        cur.execute(insertfeed_sql, rec_values)
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        st.error(f"Failed to insert user data: {e}")



def get_image_base64(image_path):
    img = Image.open(image_path)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded

def init_app_iface() :

    st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon='./logo/tabLogo.png',
    )

    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: #007BFF;
            color: white;
            font-size: 16px;
            border-radius: 8px;
            padding: 0.5em 1em;
            border: none;
            transition: background-color 0.3s ease;
        }

        div.stButton > button:first-child:hover {
            background-color: #0056b3;
            color: white;
        }

        div.stButton > button:first-child:focus {
            background-color: #0056b3;
            color: white;
            outline: none;
        }

        div.stButton > button:first-child:active {
            background-color: #004494;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)



    logo_base64 = get_image_base64('./logo/appLogo.png')

    st.markdown(
        f"""
        <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 20px;'>
            <img src='data:image/png;base64,{logo_base64}' width='120' />
            <h1 style='color: #2c3e50; margin: 0;'>Resume Analyzer</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.markdown("<h2 style='color:#4CAF50;'>🔎 Navigation</h2>", unsafe_allow_html=True)
    activities = ["User", "Feedback", "About", "Admin"]
    choice = st.sidebar.selectbox("Choose an option:", activities)

    return choice

def header_visibility(visible = True) :
    if visible == False : 
        st.markdown("""
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """,
            unsafe_allow_html=True
)
        
#model section

class LLM_model :
    def __init__(self):
        genai.configure(api_key=api_keyy)

        self.model_version = genai.GenerativeModel("models/gemini-2.0-flash")

llm = LLM_model()
model = llm.model_version

        
#resume parsing and analysis section

def read_pdf(uploaded_file) :
    pdf_bytes = uploaded_file.read()
    return fitz.open(stream=pdf_bytes, filetype="pdf")


def extract_text(pdf_doc) :

    resume_text = ""

    for i in range(pdf_doc.page_count) :
        resume_text += pdf_doc[i].get_text()

    return resume_text

def analyze_resume(resume_text) :
    prompt = f"""
        `You are a highly skilled resume parser. Analyze the resume text provided and extract structured information. Your output must be a **valid JSON string** that can be parsed by Python's `json.loads()` without any syntax errors or formatting issues.

        ### Output Format (JSON string):
        Return a JSON object with the following fields:

        - "name": (string) Full name of the candidate.
        - "email": (string) Valid email address.
        - "socialmedia_handles": (dictionary) Dictionary of recognized social media platforms as keys (e.g., "LinkedIn", "GitHub", "Twitter", "Portfolio") and their corresponding profile links or usernames as values. If none are found, return an empty dictionary.
        - "phone": (string) Phone number in international or local format.
        - "skills": (list of strings) All relevant technical and soft skills explicitly mentioned in the resume.
        - "education": (list of dictionaries) College-level degrees only. Each dictionary should contain:
            - "degree": (string)
            - "institution": (string)
            - "grade": (string or null if not mentioned)
            - "year": (string, e.g., "2019 - 2023")
        - "experience": (list of dictionaries) Work experience and internships. Each dictionary should include:
            - "company": (string)
            - "role": (string)
            - "duration": (string, e.g., "June 2021 - August 2022")
        - "cand_level": (string) Candidate level based on experience:
            - "Fresher" → No work or internship experience.
            - "Intermediate" → Has internship experience.
            - "Experienced" → Has held full-time professional roles.
        - "field": (string) The most suitable job or industry domain for the candidate, inferred from the combination of their education, projects, roles, and skills. Choose **only one** from well-defined domains such as:
            "Software Development", "Data Science", "AI/ML", "Cybersecurity", "UI/UX Design", "DevOps", "Cloud Computing", "Embedded Systems", "Business Analytics", "Digital Marketing", "Finance", etc.
        - "highlighted-skills": (list of strings) Subset of `"skills"` that were directly relevant in identifying the recommended `"field"`.
        - "recommended_skills": (list of strings) Important skills or tools the candidate lacks or should improve on to become more competitive in the recommended `"field"`.

        ### Requirements:
        - Do not include any additional explanation or formatting such as markdown or comments.
        - The entire response must be a **single, clean JSON string** only.
        - Avoid including irrelevant or guessed values. Only extract what is present or clearly implied in the resume.

        ### Resume Text:
        {resume_text}
    """


    response = model.generate_content(prompt)

    textt = response.text

    textt = textt.strip().removeprefix("```json").removesuffix("```").strip()

    return json.loads(textt)

def recommend_courses(skills) :
    skills_str = ", ".join(skills)

    prompt = f"""
        You are an expert AI course advisor with deep knowledge of current educational resources. Based on the user's listed skills, suggest structured, practical, and high-quality online courses to help them advance further.

        ### Input:
        The user possesses the following skills:
        {skills_str}

        ### Output Format (JSON string):
        Return a **valid JSON object** that maps each skill to a list of 2–3 top recommended online courses.

        Each course entry must be a dictionary with the following fields:
        - "corresponding skill": (string) The specific skill this course relates to.
        - "title": (string) The exact name of the course.
        - "link": (string) A working, publicly accessible URL to the course on reputable platforms like Coursera, edX, Udemy, LinkedIn Learning, or similar.

        Ensure the courses are:
        - Beginner-friendly if the skill is fundamental.
        - Advanced or specialized if the skill is more specific.
        - Preferably well-reviewed, up-to-date, and structured for progressive learning.
    """

    response = model.generate_content(prompt)

    textt = response.text

    textt = textt.strip().removeprefix("```json").removesuffix("```").strip()

    return json.loads(textt)
    

#user section

def display_analysis(resume_data) :
    st.markdown("<h2 style='color:#4CAF50;'>📄 Resume Analysis</h2>", unsafe_allow_html=True)
    st.success(f"Hello, {resume_data['name']} 👋")


    st.markdown("<h3 style='margin-top:30px;'>👤 Basic Information</h3>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Name:** {resume_data['name']}")
        st.markdown(f"**Email:** {resume_data['email']}")
        st.markdown(f"**Contact:** {resume_data['phone']}")
    with col2:
        st.markdown(f"**Degree:** {resume_data['education'][0]['degree']}")
        st.markdown(f"**Resume Pages:** {resume_data.get('total_pages', 'N/A')}")
        st.markdown(
            f"<h5 style='color:#fba171;'>📌 Candidate Level: {resume_data['cand_level']}</h5>",
            unsafe_allow_html=True
        )

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h3>💼 Job Field Recommendation</h3>", unsafe_allow_html=True)
    st.success(f"✅ Based on our analysis, you're best suited for **{resume_data['field']}** roles.")


    st.markdown("<h4>🌟 Highlighted Skills That Point to This Field:</h4>", unsafe_allow_html=True)
    st.markdown(
        "<ul style='list-style-type:circle; padding-left:20px; color:#444;'>"
        + "".join([f"<li>{skill}</li>" for skill in resume_data.get("highlighted-skills", [])])
        + "</ul>", unsafe_allow_html=True)

    st.markdown("<h4 style='color:#1ed760;'>🚀 Skills You Should Consider Adding or Improving:</h4>", unsafe_allow_html=True)
    st.markdown(
        "<ul style='list-style-type:circle; padding-left:20px; color:#444;'>"
        + "".join([f"<li>{skill}</li>" for skill in resume_data.get("recommended_skills", [])])
        + "</ul>", unsafe_allow_html=True)
    
def display_courses(recommended_courses):
    st.markdown("<h3 style='margin-top:30px; color:#4CAF50;'>📚 Recommended Courses(for recommended skills)</h3>", unsafe_allow_html=True)

    for skill, courses in recommended_courses.items():
        st.markdown(f"<h4 style='margin-top:20px; color:#2c3e50;'>🔧 Skill: {skill}</h4>", unsafe_allow_html=True)

        course_titles = []
        course_links = []

        for course in courses:
            title = course.get("title", "N/A")
            link = course.get("link", "#")
            visible_link = f"{link}"
            course_titles.append(title)
            course_links.append(visible_link)

        df = pd.DataFrame({
            "Course Title": course_titles,
            "Accessible Link": course_links
        })

        df.index = [''] * len(df)
        st.table(df)





def run() :
    
    choice = init_app_iface()
    header_visibility()

    if choice == 'User' :
        act_name = st.text_input('Name*')
        act_mail = st.text_input('Mail*')
        sorted_country_options,country_code_map = country_codes()
        selected_country = st.selectbox("Select your country", sorted_country_options)
        selected_code = country_code_map[selected_country]
        act_mob  = st.text_input('Mobile Number*')
        act_mob = act_mob.replace(" ","")

        st.markdown('''<h5 style='text-align: left; color: #021659;'> Upload Your Resume for analysis</h5>''',unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader("Choose your Resume", type=["pdf"])

        if st.button("Submit & Analyze"):
            if not act_name or not act_mail or not act_mob :
                st.warning("🚨 Please fill in all the required fields (Name, Mail, Mobile Number).\n If you have used autofill, consider clicking 'enter' at each section to register details.")
            elif not is_valid_gmail(act_mail) :
                st.warning("🚨 The mail ID entered is not correct.")
            elif not is_valid_number(act_mob) :
                st.warning("🚨 The mobile number entered is not correct.")
            elif uploaded_file is None:
                st.warning("📄 Please upload your resume before submitting.")
            else:
                with st.spinner('Analyzing the resume...'):
                    try:

                        save_image_path = './Uploaded_Resumes/'+uploaded_file.name
                        pdf_name = uploaded_file.name

                        pdf_doc = read_pdf(uploaded_file)
                        resume_text = extract_text(pdf_doc)
                        resume_data = analyze_resume(resume_text)
                        resume_data['total_pages'] = pdf_doc.page_count


                        sec_token = secrets.token_urlsafe(12)
                        host_name = socket.gethostname()
                        ip_add = socket.gethostbyname(host_name)
                        dev_user = os.getlogin()
                        os_name_ver = platform.system() + " " + platform.release()
                        g = geocoder.ip('me')
                        latlong = g.latlng
                        geolocator = Nominatim(user_agent="http")
                        location = geolocator.reverse(latlong, language='en')
                        address = location.raw['address']
                        city = address.get('city', '')
                        state = address.get('state', '')
                        country = address.get('country', '')
                        ts = time.time()
                        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                        timestamp = str(cur_date+'_'+cur_time)
                        insert_data(sec_token, ip_add, host_name, dev_user, os_name_ver, latlong, city, state, country, act_name, act_mail, str(selected_code) + " " + act_mob, resume_data['name'], resume_data['email'], 10, timestamp, resume_data['total_pages'], resume_data['field'], resume_data['cand_level'], pickle.dumps(resume_data['skills']), pickle.dumps(resume_data['recommended_skills']), pdf_name)
                        display_analysis(resume_data)

                    except Exception as e:
                        st.error(f"❌ Something went wrong during analysis: {e}")
                with st.spinner('recommending courses...') :
                    try :
                        recommended_courses = recommend_courses(resume_data['recommended_skills'])
                        display_courses(recommended_courses)
                    except Exception as e:
                        st.error(f"❌ Something went wrong during analysis: {e}")
    elif(choice == 'About') :
        html_content = """
        <div style="padding: 20px; border-radius: 10px; background-color: #f9f9f9; border: 1px solid #ddd;">
            <h2 style="color:#2c3e50;">💼 About Resume Analyzer</h2>
            <p style="font-size: 16px; color: #333;">
                <strong>Resume Analyzer</strong> is an AI-powered web application that helps candidates understand and improve their resumes by offering the following features:
            </p>

            <ul style="font-size: 16px; color: #444; line-height: 1.8;">
                <li>📄 <strong>Resume Upload:</strong> Upload your resume in PDF format for instant analysis.</li>
                <li>🧠 <strong>AI Analysis:</strong> Uses Gemini 2.0 Flash to extract your name, email, phone, education, experience, skills, and more.</li>
                <li>🎯 <strong>Field Prediction:</strong> Recommends the most suitable job domain based on your resume content.</li>
                <li>💡 <strong>Skill Insights:</strong> Highlights your strengths and suggests relevant skills to improve.</li>
                <li>📚 <strong>Course Recommendations:</strong> Provides curated online courses mapped to your skill gaps.</li>
                <li>🗺️ <strong>Geolocation Capture:</strong> Captures user location and system information during resume submission.</li>
                <li>🔐 <strong>Admin Portal:</strong> Allows administrators to view collected user data and feedback securely.</li>
            </ul>

            <p style="font-size: 16px; color: #333;">
                This tool is built with ❤️ using <strong>Python, Streamlit, MySQL, Google Gemini API</strong> and integrates modern libraries for resume parsing, user geolocation, and secure data storage.
            </p>

            <p style="font-size: 16px; color: #2c3e50; font-style: italic;">
                Empowering candidates to level up their careers with personalized AI insights.
            </p>
            <p>
                Don't forget to give us your feedback :) - chpkm
            </p>
        </div>
        """

        st.components.v1.html(html_content, height=600, scrolling=True)

    elif(choice == 'Feedback') :
        st.markdown("<h2 style='color:#4CAF50;'>📝 We Value Your Feedback</h2>", unsafe_allow_html=True)
        feed_name = st.text_input("Your Name*")
        feed_email = st.text_input("Your Email*")
        feed_score = st.radio("Rate Your Experience (1=Bad, 5=Excellent)*", ["1", "2", "3", "4", "5"], horizontal=True)
        comments = st.text_area("Any Suggestions or Comments (Optional)")

        if st.button("Submit Feedback"):
            if not feed_name or not feed_email or not feed_score:
                st.warning("⚠️ Please fill in all the required fields.")
            elif not is_valid_gmail(feed_email):
                st.warning("⚠️ Please enter a valid Gmail address.")
            else:
                try:
                    ts = time.time()
                    cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                    cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    timestamp = str(cur_date + '_' + cur_time)

                    insertf_data(feed_name, feed_email, feed_score, comments, timestamp)
                    st.success("✅ Thank you for your feedback!")

                except Exception as e:
                    st.error(f"❌ Failed to submit feedback: {e}")

    elif(choice == 'Admin') :
        st.subheader("🔐 Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if "admin_logged_in" not in st.session_state:
            st.session_state.admin_logged_in = False

        if not st.session_state.admin_logged_in:
            if st.button("Login"):
                if username == "admin" and password == "admin123":
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials.")
        else :
            st.success("✅ Logged in as Admin")

            tab1, tab2 = st.tabs(["📊 User Data", "📝 Feedback"])

            with tab1:
                try:
                    conn = connect_to_db()
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM user_data")
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]

                    resume_df = pd.DataFrame(rows, columns=col_names)

                    # Decode pickled fields safely
                    def safe_unpickle(val):
                        try:
                            return pickle.loads(val) if isinstance(val, bytes) else val
                        except:
                            return val

                    resume_df['Actual_skills'] = resume_df['Actual_skills'].apply(safe_unpickle)
                    resume_df['Recommended_skills'] = resume_df['Recommended_skills'].apply(safe_unpickle)

                    # Ensure 'Predicted_Field' and 'User_level' are strings
                    resume_df['Predicted_Field'] = resume_df['Predicted_Field'].astype(str)
                    resume_df['User_level'] = resume_df['User_level'].astype(str)

                    st.dataframe(resume_df, use_container_width=True)

                    cur.close()
                    conn.close()

                except Exception as e:
                    st.error(f"Error loading user data: {e}")

            with tab2:
                try:
                    conn = connect_to_db()
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM user_feedback")
                    rows = cur.fetchall()
                    col_names = [desc[0] for desc in cur.description]

                    feedback_df = pd.DataFrame(rows, columns=col_names)
                    st.dataframe(feedback_df, use_container_width=True)

                    cur.close()
                    conn.close()

                except Exception as e:
                    st.error(f"Error loading feedback: {e}")
                    st.markdown("---")

            # Search resume profiles by skills
            st.markdown("### 🧠 Search Resume Profiles by Skills")

            skill_input = st.text_input("Enter skill(s) to search for resume matches (comma-separated) and press enter", placeholder="e.g., Python, SQL, React")

            if skill_input:
                search_skills = [s.strip().lower() for s in skill_input.split(",") if s.strip()]

                def skill_match(row_skills):
                    candidate_skills = [s.lower() for s in row_skills]
                    return all(
                        any(search_skill in cand_skill for cand_skill in candidate_skills)
                        for search_skill in search_skills
                    )
                
                matching_df = resume_df[resume_df['Actual_skills'].apply(skill_match)]

                if not matching_df.empty:
                    st.success(f"✅ Found {len(matching_df)} matching profiles.")
                    st.dataframe(matching_df, use_container_width=True)
                else:
                    st.warning("🔍 No profiles matched the given skill(s).")

    else:
        st.error('Something went wrong..')

init_db()
run()