# DV360 Audience Data Manager: Stateless FastAPI Implementation

## 1. Project Overview
This implementation plan shifts from a stateful, session-based Node.js backend (with a full server-side OAuth 2.0 flow) to a **stateless FastAPI microservice**, paired seamlessly with the customized [dv360_audience_manager.html](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/dv360_audience_manager.html) frontend. 

By eliminating the server-side OAuth flow, we reduce infrastructure complexity. The user simply generates their Google OAuth 2.0 Access Token (e.g., via the OAuth 2.0 Playground) and pastes it into the Frontend UI. The UI reads the selected CSV, bundles the hashed data with the token, and pushes it to our stateless FastAPI layer to securely hit the Google Cloud endpoints.

---

## 2. Architecture & Tech Stack

*   **Repository Structure**:
    *   [integrate-dm-api/dv360_audience_manager.html](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/dv360_audience_manager.html) (Frontend UI)
    *   [integrate-dm-api/main.py](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/main.py) (FastAPI Server)
*   **Backend Framework**: FastAPI (Python) running on Uvicorn.
*   **Authentication Mechanism**: Stateless pass-through. The user pastes the `access_token` into the frontend UI, which is securely embedded in the `POST /upload-audience` request body payload.
*   **Data Processing**:
    *   **Frontend**: JavaScript `FileReader` loads the local CSV and extracts all columns (Email, Phone, First Name, Last Name, Zip, Country) directly in the browser into a JSON array of member objects. 
    *   **Backend**: Python receives the `member_list` array. Since the provided [Mar24.csv](file:///Users/ashleyngo/Downloads/repo/dm-api-test/Hashed_Audience_List_Mar24.csv) identifiers are already SHA-256 hashed, the backend constructs the dictionary shapes required by Google Ads *without* re-hashing them.
*   **Cross-Origin Policy**: CORSMiddleware is fully configured on the FastAPI app to allow `localhost` testing without browser fetch errors.

---

## 3. Core Integrated Workflows

### A. Stateless Authentication (Frontend to Backend)
1. **No OAuth Redirects**: The FastAPI server does NOT handle Google Consent screens or token exchanges.
2. **Access Token Injection**: The user inputs their temporary Access Token into the "Google OAuth Access Token" field within the [dv360_audience_manager.html](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/dv360_audience_manager.html) UI.
3. **Payload Construction**: The javascript function validates that a partner ID, access token, and CSV source exist before proceeding. 

### B. Payload Generation & Hashing (API Request)
1. **Frontend Parsing**: When clicking "Push to DV360", `FileReader()` splits the CSV rows, pulling all 6 columns of data (email, phone, names, address) and packages them into the `member_list` JSON array.
2. **Backend Parsing**: The [AudienceUpload](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/main.py#26-31) Pydantic model validates the incoming HTTP JSON payload against the multi-field [Member](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/main.py#18-25) structure.
3. **DV360 JSON Generation**: The backend maps the values directly into the `audienceMembers` payload structure expected by the **Data Manager API** utilizing the pre-hashed CSV fields. It automatically generates the required `.addressInfo` dictionaries and sets `adUserData: "GRANTED"` and `adPersonalization: "GRANTED"`.

### C. Data Ingestion (REST to Google Cloud API)
1. **REST Fulfillment**: The FastAPI application utilizes Python's `requests` module to execute `POST https://datamanager.googleapis.com/v1/audienceMembers:ingest`.
2. **Bearer Assignment**: Instead of locally sourced credentials, it explicitly injects the user's `access_token` into the `Authorization: Bearer` header.
3. **Response Monitoring**: The server pulls the `requestId` from the Google API Response. The FastAPI server successfully forwards this back to the frontend, which triggers the visual "Upload Complete!" state change.

---

## 4. Run Instructions

### 1. Install Dependencies
Make sure you have installed FastAPI and its prerequisites on your system:
```bash
pip install fastapi uvicorn requests pydantic
```

### 2. Boot the Server
Start the local FastAPI python server running inside your dedicated directory:
```bash
cd integrate-dm-api
uvicorn main:app --reload
```
You will see output stating `Application startup complete` ensuring the server is running on `http://localhost:8000/`.

### 3. Open the Frontend Application
Double-click [integrate-dm-api/dv360_audience_manager.html](file:///Users/ashleyngo/Downloads/repo/dm-api-test/integrate-dm-api/dv360_audience_manager.html) (or serve it directly) to launch the web app.

1. **Step 1:** Browse to insert your target mock Audiences CSV.
2. **Step 2:** Paste your valid *Google Access Token* and numeric *Partner ID*.
3. **Step 3:** Use a custom target audience or let it create a new ID randomly.
4. **Step 4:** Hit **Push to DV360**. Watch the loading bar dynamically track your upload progress through to the server response! 
