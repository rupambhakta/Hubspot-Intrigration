# slack.py

from datetime import datetime
import json
import httpx
from fastapi import Request
from typing import Dict, List, Optional
import redis
from .integration_item import IntegrationItem

# HubSpot OAuth Configuration
CLIENT_ID = "21c726d2-ed6d-4e44-b161-b028029eaff3"  # Replace with your HubSpot Client ID
CLIENT_SECRET = "042d4716-5ed4-4ae5-8700-af055d2c45e3"  # Replace with your HubSpot Client Secret
REDIRECT_URI = "http://localhost/integrations/hubspot/oauth2callback"
SCOPES = ["contacts", "companies", "deals"]  # Basic scopes for CRM access

# Redis Configuration
redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def authorize_hubspot(user_id: str, org_id: str):
    """Initialize HubSpot OAuth flow."""
    auth_url = (
        "https://app.hubspot.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={' '.join(SCOPES)}"
        "&state=" + f"{user_id}:{org_id}"
    )
    return {"auth_url": auth_url}

async def oauth2callback_hubspot(request: Request):
    """Handle OAuth callback from HubSpot."""
    params = dict(request.query_params)
    if "error" in params:
        return {"error": params["error"]}
    
    if "code" not in params:
        return {"error": "No code provided"}

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.hubapi.com/oauth/v1/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": params["code"]
            }
        )
        
        if token_response.status_code != 200:
            return {"error": "Failed to get access token"}

        token_data = token_response.json()
        
        # Store the credentials in Redis
        user_id, org_id = params["state"].split(":")
        credentials_key = f"hubspot:credentials:{user_id}:{org_id}"
        redis_client.set(credentials_key, json.dumps(token_data))
        
        return {"success": True}

async def get_hubspot_credentials(user_id: str, org_id: str):
    """Retrieve HubSpot credentials from Redis."""
    credentials_key = f"hubspot:credentials:{user_id}:{org_id}"
    credentials = redis_client.get(credentials_key)
    if not credentials:
        return {"error": "No credentials found"}
    return {"credentials": credentials.decode()}

async def create_integration_item_metadata_object(data: Dict, item_type: str) -> IntegrationItem:
    """Convert HubSpot object to IntegrationItem."""
    return IntegrationItem(
        id=str(data.get("id")),
        type=item_type,
        directory=False,
        name=data.get("properties", {}).get("name") or data.get("properties", {}).get("firstname", "") + " " + data.get("properties", {}).get("lastname", ""),
        creation_time=datetime.fromtimestamp(int(data.get("createdAt", 0)/1000)) if data.get("createdAt") else None,
        last_modified_time=datetime.fromtimestamp(int(data.get("updatedAt", 0)/1000)) if data.get("updatedAt") else None,
        url=f"https://app.hubspot.com/{item_type}/{data.get('id')}" if data.get("id") else None,
    )

async def get_items_hubspot(credentials: str):
    """Fetch items from HubSpot API."""
    try:
        creds = json.loads(credentials)
        access_token = creds.get("access_token")
        
        if not access_token:
            return {"error": "Invalid credentials"}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            # Create root folders
            root_items = [
                IntegrationItem(id="contacts", type="folder", directory=True, name="Contacts"),
                IntegrationItem(id="companies", type="folder", directory=True, name="Companies"),
                IntegrationItem(id="deals", type="folder", directory=True, name="Deals")
            ]
            
            # Fetch contacts
            contacts_response = await client.get(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers
            )
            if contacts_response.status_code == 200:
                contacts_data = contacts_response.json()
                contacts = [await create_integration_item_metadata_object(contact, "contacts") 
                          for contact in contacts_data.get("results", [])]
            else:
                contacts = []

            # Fetch companies
            companies_response = await client.get(
                "https://api.hubapi.com/crm/v3/objects/companies",
                headers=headers
            )
            if companies_response.status_code == 200:
                companies_data = companies_response.json()
                companies = [await create_integration_item_metadata_object(company, "companies") 
                           for company in companies_data.get("results", [])]
            else:
                companies = []

            # Fetch deals
            deals_response = await client.get(
                "https://api.hubapi.com/crm/v3/objects/deals",
                headers=headers
            )
            if deals_response.status_code == 200:
                deals_data = deals_response.json()
                deals = [await create_integration_item_metadata_object(deal, "deals") 
                        for deal in deals_data.get("results", [])]
            else:
                deals = []

            # Add items to their respective folders
            all_items = []
            for root_item in root_items:
                all_items.append(root_item.__dict__)
                if root_item.id == "contacts":
                    all_items.extend([contact.__dict__ for contact in contacts])
                elif root_item.id == "companies":
                    all_items.extend([company.__dict__ for company in companies])
                elif root_item.id == "deals":
                    all_items.extend([deal.__dict__ for deal in deals])

            return {"items": all_items}

    except Exception as e:
        return {"error": str(e)}