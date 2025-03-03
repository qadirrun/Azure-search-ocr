import streamlit as st
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import pandas as pd
from fetch import get_file_url,upload_file,run_search_indexer,check_blob_exists
from objcr import doc_ocr
from PIL import Image
import io

# Set your Azure Search details here
search_endpoint = SEARCH_ENDPOINT
index_name = INDEX_NAME
indexer = INDEXER_NAME
api_key = API_KEY
service = AZURE_SERVICE_NAME

# Initialize SearchClient
search_client = SearchClient(
    endpoint=search_endpoint,
    index_name=index_name,
    credential=AzureKeyCredential(api_key),
)

st.set_page_config(layout="wide")

# Streamlit UI for user input
st.title('Azure AI Search')
st.markdown('### Index Search using Azure AI Search')

# Sidebar selection
# option = st.sidebar.("Choose an action:", ["📤 Upload File", "🔎 Search File"])

if "mode" not in st.session_state:
    st.session_state.mode = "Search File"  # Default mode

# Sidebar UI
# Sidebar UI with styled buttons
st.sidebar.markdown("<h2 style='text-align: center;'>Navigation</h2>", unsafe_allow_html=True)
# st.sidebar.markdown("---")  # Divider for better UI spacing

# Styled buttons
upload_clicked = st.sidebar.button("📤 Upload", use_container_width=True)
search_clicked = st.sidebar.button("🔎 Search", use_container_width=True)

# Update session state based on button click
if upload_clicked:
    st.session_state.mode = "Upload File"
if search_clicked:
    st.session_state.mode = "Search File"

st.sidebar.markdown("---")  # Divider for clarity
# st.sidebar.write(f"### Selected Mode: **{st.session_state.mode}**")

option = st.session_state.mode

# **Upload Section**
if option == "Upload File":
    st.header("Upload File")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt", "xlsx", "jpg", "jpeg", "png"])
    
    if uploaded_file:
        st.success(f"Uploaded: {uploaded_file.name}")
        
        # Read file content
        file_content = uploaded_file.read()
        file_name = uploaded_file.name
        file_extension = file_name.split(".")[-1].lower()
        
        # Check if the file is an Excel file
        if file_name.lower().endswith(".xlsx"):
            st.write("Uploading Excel file to SharePoint... ⏳")
        else:
            st.write("Processing document with OCR... ⏳")
            
            if file_extension in ["jpg", "jpeg", "png"]:
                image = Image.open(io.BytesIO(file_content))
                pdf_bytes = io.BytesIO()
                image.convert("RGB").save(pdf_bytes, format="PDF")  # Convert image to PDF
                file_content = pdf_bytes.getvalue()  # Get the new PDF content
                file_name = file_name.rsplit(".", 1)[0] + ".pdf"  # Change file extension to .pdf
                
            with open(file_name, "wb") as f:
                # content = f.read()
                upload_file(file_content,file_name)
                f.write(file_content)  # Save the uploaded file to disk

            processed_file_path = doc_ocr(file_name)  # Call OCR function

            if processed_file_path:
                st.success(f"OCR processing completed for {file_name}. Uploading to SharePoint... ⏳")
                with open(processed_file_path, "rb") as f:
                    file_content = f.read()  # Read the processed file content for upload
                file_name = processed_file_path.split("/")[-1]  # Get the new file name
        
        # Upload file to SharePoint
        # st.write("Uploading to SharePoint... ⏳")
        file_url = upload_file(file_content, file_name)
        
        if file_url:
            st.success("✅ File uploaded successfully!")
            # st.write(f"🔗 [View File in Sharepoint Sites]({file_url})")

            # Wait until file is available in Blob Storage
            st.write(f"⏳ Waiting for {file_name} to be detected in Azure Blob Storage...")
            file_url = check_blob_exists(file_name)
            
            if file_url:
                # st.success("✅ File uploaded successfully!")
                # st.write(f"🔗 [View File in SharePoint]({file_url})")
                
                # Rerun the Azure AI Search indexer
                st.write("Triggering Azure AI Search indexer... ⏳")
                indexer_status = run_search_indexer(service, indexer, api_key)
                
                if indexer_status["success"]:
                    st.success(indexer_status["message"])
                else:
                    st.error(indexer_status["message"])
            else:
                st.error("❌ File not found in Blob Storage within the wait time!")
        else:
            st.error("❌ Failed to upload file.")
# vendor_name_query = st.text_input("ENTER SEARCH", "Walmart")  # Default vendor for demo

# Perform the search when the user hits 'Search'
# **Search Section**
elif option == "Search File":
    st.header("Azure AI Search")
    vendor_name_query = st.text_input("Enter search query")  # Default search term   
     
    if st.button("Search"):
        if vendor_name_query:
            # Perform search
            results = list(search_client.search(vendor_name_query))
            result_count = len(results)
            
            if result_count == 0:
                st.warning(f"No results found for: {vendor_name_query}")
            else:
                st.write(f"Search results for: {vendor_name_query}")
                st.write(f"Found {result_count} result(s).")
                
                # Create tabs dynamically
                tab_labels = [f"{result['metadata_storage_name'].split('.')[0]}" for result in results]
                tabs = st.tabs(tab_labels)

                
                # Process each result separately
                # for i, result in enumerate(results):
                for i, (tab, result) in enumerate(zip(tabs, results)):
                    with tab:
                    # Split the result into lines
                        lines = result['content'].split("\n")
                        storage = result['metadata_storage_path'].split("\n")
                        name = result['metadata_storage_name'].split("\n")[0].split(".")[0]
                        
                        fields = {}
                        items = []
                        
                        for line in lines[2:]:  # Skip the first two lines (Sheet1 and header line)
                            line = line.strip()

                            if "\t" in line:  # Only process lines with tab character
                                field, value = line.split("\t", 1)  # Split by tab character
                                if "Items[" in field:  # Check if it's an item field (e.g., Items[0].Description)
                                    # Extract the item index and field name
                                    item_index = int(field.split("[")[1].split("]")[0])  # Extract index from Items[0]
                                    item_field = field.split("].")[1]  # Extract field name (Description, ProductCode, etc.)
                                    
                                    # Ensure the item list is long enough to hold the current index
                                    while len(items) <= item_index:
                                        items.append({})
                                    
                                    # Add the value to the corresponding item
                                    items[item_index][item_field] = value
                                else:
                                    # If it's not an item, just add it to the fields
                                    fields[field] = value
                        storage_url = "https://softech3600.sharepoint.com/sites/resit/Shared%20Documents/Forms/AllItems.aspx"
                        
                        # Extract address components
                        address_parts = [
                            fields.get("MerchantAddress.house_number", ""),
                            fields.get("MerchantAddress.road", ""),
                            fields.get("MerchantAddress.street_address", ""),
                            fields.get("MerchantAddress.city", ""),
                            fields.get("MerchantAddress.state", ""),
                            fields.get("MerchantAddress.postal_code", "")
                        ]

                        # Remove empty values and join the rest
                        merchant_address = ", ".join(filter(None, address_parts))

                        # Construct metadata
                        metadata = {
                            "Merchant Name": fields.get("MerchantName", ""),
                            # "Merchant Address": {
                            #     "House Number": fields.get("MerchantAddress.house_number", ""),
                            #     "Road": fields.get("MerchantAddress.road", ""),
                            #     "City": fields.get("MerchantAddress.city", ""),
                            #     "State": fields.get("MerchantAddress.state", ""),
                            #     "Postal Code": fields.get("MerchantAddress.postal_code", ""),
                            #     "Street Address": fields.get("MerchantAddress.street_address", "")
                            # },
                            "Merchant Address": merchant_address,  # Merged address
                            "Merchant PhoneNumber": fields.get("MerchantPhoneNumber", ""),
                            "Transaction Date": fields.get("TransactionDate", ""),
                            "Transaction Time": fields.get("TransactionTime", ""),
                            "SubTotal": fields.get("Subtotal", ""),
                            "Total": fields.get("Total", ""),
                            # "Storage Path": storage_url  # You can dynamically fill this as needed
                            
                        }
                                                
                        # Display Items
                        if items:  # Ensure there are items to display
                            items_df = pd.DataFrame(items)
                            st.write(f"### Items for {name}")
                            st.table(items_df)  # Use st.dataframe(items_df) for interactivity
                        
                        # Display metadata
                        st.subheader(f"Metadata for {name}")
                        for key, value in metadata.items():
                            if isinstance(value, dict):
                                st.write(f"**{key}:**")
                                for sub_key, sub_value in value.items():
                                    st.write(f"  - {sub_key}: {sub_value}")
                            else:
                                st.write(f"**{key}:** {value}")

                        # Add a button inside each tab
                        xlsx_url = get_file_url(f"{name}.xlsx")
                        pdf_url = get_file_url(f"{name}.pdf")

                        if xlsx_url:
                            st.link_button("Open SharePoint (Excel)", xlsx_url)

                        if pdf_url:
                            st.link_button("Open SharePoint (PDF)", pdf_url)
                            # st.pdf(pdf_url)

                        st.markdown("---")

    else:
        st.warning("Please enter a keyword to search.")


