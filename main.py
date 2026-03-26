import hashlib
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import hashlib
import re

app = FastAPI(title="DV360 Data Manager Pass-Through (Stateless)")

@app.get("/")
async def root():
    return {"message": "Server is running"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local testing, allow all origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Member(BaseModel):
    email: str
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

class AudienceUpload(BaseModel):
    access_token: str
    partner_id: Optional[str] = None
    advertiser_id: Optional[str] = None
    user_list_id: str
    member_list: List[Member]

def is_sha256(s: str) -> bool:
    return bool(re.match(r'^[a-fA-F0-9]{64}$', s.strip()))

def format_and_hash(val: str, field_type: str = 'string') -> str:
    if not val:
        return val
    val = val.strip()
    if is_sha256(val):
        return val.lower()
        
    if field_type in ['email', 'first_name', 'last_name']:
        val = val.lower()
        
    return hashlib.sha256(val.encode('utf-8')).hexdigest()

@app.post("/upload-audience")
async def upload_to_dm(request: AudienceUpload):
    try:
        # 1. Prepare the Data 
        audience_members = []
        for mem in request.member_list:
            
            identifiers = []
            
            if mem.email:
                identifiers.append({ "emailAddress": format_and_hash(mem.email, 'email') })
            if mem.phone:
                identifiers.append({ "phoneNumber": format_and_hash(mem.phone, 'phone') })
                
            if mem.first_name and mem.last_name:
                address_info = {
                    "givenName": format_and_hash(mem.first_name, 'first_name'),
                    "familyName": format_and_hash(mem.last_name, 'last_name'),
                }
                if mem.zip_code:
                    address_info["postalCode"] = mem.zip_code.strip()
                if mem.country:
                    address_info["regionCode"] = mem.country.strip()
                    
                identifiers.append({ "address": address_info })

            member_payload = {
                "userData": {
                    "userIdentifiers": identifiers
                }
            }
            audience_members.append(member_payload)

        # 2. Build the Payload for Data Manager API
        destination = {
            "productDestinationId": request.user_list_id
        }
        
        if request.partner_id and request.advertiser_id:
             destination["operatingAccount"] = {
                 "accountType": "DISPLAY_VIDEO_ADVERTISER",
                 "accountId": request.advertiser_id
             }
             destination["loginAccount"] = {
                 "accountType": "DISPLAY_VIDEO_PARTNER",
                 "accountId": request.partner_id
             }
        elif request.advertiser_id:
             destination["operatingAccount"] = {
                 "accountType": "DISPLAY_VIDEO_ADVERTISER",
                 "accountId": request.advertiser_id
             }
        elif request.partner_id:
             destination["operatingAccount"] = {
                 "accountType": "DISPLAY_VIDEO_PARTNER",
                 "accountId": request.partner_id
             }
        else:
             raise HTTPException(status_code=400, detail="Either partner_id or advertiser_id must be provided")

        payload = {
            "destinations": [destination],
            "audienceMembers": audience_members,
            "encoding": "HEX",
            "termsOfService": {
                "customerMatchTermsOfServiceStatus": "ACCEPTED"
            },
            "consent": {
                "adUserData": "CONSENT_GRANTED",
                "adPersonalization": "CONSENT_GRANTED"
            }
        }

        # 3. Execute the Ingestion request via REST
        headers = {
            "Authorization": f"Bearer {request.access_token}",
            "Content-Type": "application/json"
        }
        
        endpoint = "https://datamanager.googleapis.com/v1/audienceMembers:ingest"
        
        response = requests.post(endpoint, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
            
        response_data = response.json()
        print("\n" + "="*50)
        print(f"SUCCESS: API request submitted successfully!")
        print(f"Status Code: {response.status_code}")
        print("="*50 + "\n")

        # 4. Return the requestId to the user so they can monitor status
        return {
            "status": "success", 
            "request_id": response_data.get("requestId"),
            "message": "Data successfully submitted. Use the request_id to check status."
        }

    except HTTPException as e:
        raise e
    except requests.exceptions.RequestException as e:
        import traceback
        print("\n" + "!" * 50)
        print("REQUEST EXCEPTION OCCURRED:")
        print(traceback.format_exc())
        print("!" * 50 + "\n")
        raise HTTPException(status_code=500, detail=f"Request to Data Manager API failed: {str(e)}")
    except Exception as e:
        import traceback
        print("\n" + "!" * 50)
        print("EXCEPTION OCCURRED:")
        print(traceback.format_exc())
        print("!" * 50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
