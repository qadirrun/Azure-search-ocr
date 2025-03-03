import requests
import os
from requests.auth import HTTPBasicAuth
from auth_token import get_token
import time
import streamlit as st
from azure.storage.blob import BlobServiceClient

# Azure AD App details (replace with your values)
client_id = CLIENT_ID
client_secret = CLIENT_SECRET
tenant_id = TENANT_ID
AZURE_STORAGE_ACCOUNT = AZURE_STORAGE_ACCOUNT
AZURE_CONTAINER_NAME = AZURE_CONTAINER_NAME
AZURE_CONNECTION_STRING = AZURE_CONNECTION_STRING

# Your SharePoint Online Site URL
site_url = SITE_URL

def get_site_id(client_id, client_secret, tenant_id, site_url):
    """Fetch the SharePoint Site ID"""
    access_token = get_token(client_id, client_secret, tenant_id)
    if not access_token:
        return None

    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    response = requests.get(site_url, headers=headers)

    if response.status_code == 200:
        return response.json().get("id")
    else:
        print("Failed to fetch site ID:", response.text)
        return None        

def get_drive_id(client_id, client_secret, tenant_id, site_url):
    """Fetch the SharePoint Drive ID"""
    site_id = get_site_id(client_id, client_secret, tenant_id, site_url)
    if not site_id:
        return None

    access_token = get_token(client_id, client_secret, tenant_id)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
    drive_response = requests.get(drive_url, headers=headers)

    if drive_response.status_code == 200:
        return drive_response.json().get("id")
    else:
        print("Failed to get drive ID:", drive_response.text)
        return None

def get_file_url(file_name):
    """Search for a file in SharePoint and return its URL"""
    drive_id = get_drive_id(client_id, client_secret, tenant_id, site_url)
    if not drive_id:
        return None

    access_token = get_token(client_id, client_secret, tenant_id)
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    search_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/search(q='{file_name}')"
    response = requests.get(search_url, headers=headers)

    if response.status_code == 200:
        search_results = response.json()
        if "value" in search_results and len(search_results["value"]) > 0:
            # Ensure exact file name match (including extension)
            for file in search_results["value"]:
                if file["name"].lower() == file_name.lower():  # Exact match check
                    return file["webUrl"]
        else:
            print("File not found.")
            return None
    else:
        print("Error searching for file:", response.text)
        return None
    
def upload_file(file_content, file_name):
    """Upload a file to SharePoint and return its URL"""

    drive_id = get_drive_id(client_id, client_secret, tenant_id, site_url)
    if not drive_id:
        return None

    access_token = get_token(client_id, client_secret, tenant_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/octet-stream"
    }

    upload_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{file_name}:/content"


    upload_response = requests.put(upload_url, headers=headers, data=file_content)

    if upload_response.status_code in [200, 201]:
        uploaded_file = upload_response.json()
        print("File Uploaded Successfully!")
        return uploaded_file["webUrl"]
    else:
        print("Error uploading file:", upload_response.text)
        return None
    
def run_search_indexer(service, indexer, api_key):
    """Triggers Azure AI Search Indexer to run."""
    url = f"https://{service}.search.windows.net/indexers/{indexer}/run?api-version=2023-11-01"

    
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }

    response = requests.post(url, headers=headers)

    if response.status_code == 202:
        return {"success": True, "message": "Indexer triggered successfully!"}
    else:
        return {"success": False, "message": f"Failed to trigger indexer: {response.text}"}

def check_blob_exists(file_name, max_wait=120, post_detect_wait=30):
    """Waits until the file is available in Azure Blob Storage before triggering the indexer."""
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)

    wait_time = 0
    status_placeholder = st.empty()  # Create a placeholder for updating text

    while wait_time < max_wait:
        status_placeholder.write(f"🔍 Checking if file '{file_name}' exists in Azure Blob Storage... ({wait_time}s)")
        
        blob_list = container_client.list_blobs(name_starts_with=file_name)
        for blob in blob_list:
            if blob.name == file_name:
                status_placeholder.success(f"✅ File '{file_name}' detected in Azure Blob Storage!")
                
                # ✅ ADD EXTRA WAIT TIME AFTER DETECTION
                st.write(f"⏳ Waiting {post_detect_wait} seconds to ensure full file processing...")
                time.sleep(post_detect_wait)
                
                return f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{file_name}"

        time.sleep(5)  # Wait for 5 seconds before checking again
        wait_time += 5

    status_placeholder.error(f"❌ File '{file_name}' not found within {max_wait} seconds.")
    return None  # File not found within max_wait time
    
