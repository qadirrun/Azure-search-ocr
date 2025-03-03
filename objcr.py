import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import pandas as pd

def doc_ocr(file):
# Azure Form Recognizer details
    endpoint = COGNITIVE_SERVICE_ENDPOINT
    api_key = COGNITIVE_SERVICE_API_KEY

    # Initialize the Document Analysis Client
    client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(api_key))

    def handle_nested_field(field_name, field_value, data):
        if isinstance(field_value, dict):  # Handle nested fields (dict)
            for sub_field_name, sub_field in field_value.items():            
                if isinstance(sub_field.value, dict):  # Recursively handle nested dictionaries
                    handle_nested_field(f"{field_name}.{sub_field_name}", sub_field.value, data)
                elif isinstance(sub_field.value, list):  # Handle lists within nested fields
                    for idx, item in enumerate(sub_field.value):
                        if isinstance(item.value, dict):  # If the item is a dictionary, handle recursively
                            handle_nested_field(f"{field_name}.{sub_field_name}[{idx}]", item.value, data)
                        elif item.value:  # If it's a simple field, store its value
                            data.append({
                                "Field Name": f"{field_name}.{sub_field_name}[{idx}]",
                                "Value": item.value,
                                # "Confidence": item.confidence,
                            })
                elif sub_field.value:  # Handle simple nested field
                    data.append({
                        "Field Name": f"{field_name}.{sub_field_name}",
                        "Value": sub_field.value,
                        # "Confidence": sub_field.confidence,
                    })

        elif isinstance(field_value, list):  # Handle list of fields
            for idx, sub_field in enumerate(field_value):
                if isinstance(sub_field.value, dict):  # Recursively handle dictionaries in the list
                    handle_nested_field(f"{field_name}[{idx}]", sub_field.value, data)
                elif isinstance(sub_field.value, list):  # Handle lists inside the list
                    for sub_idx, item in enumerate(sub_field.value):
                        if item.value:
                            data.append({
                                "Field Name": f"{field_name}[{idx}][{sub_idx}]",
                                "Value": item.value,
                                # "Confidence": item.confidence,
                            })
                elif sub_field.value:  # Handle simple field in list
                    data.append({
                        "Field Name": f"{field_name}[{idx}]",
                        "Value": sub_field.value,
                        # "Confidence": sub_field.confidence,
                    })

        elif field_value:  # Handle simple field
            # print(field_name)

            # Handle MerchantAddress separately for its AddressValue
            if field_name == "MerchantAddress":
                # print(field_value)
                # Directly access each field if it's an object
                address_fields = ["house_number", "po_box", "road", "city", "state", "postal_code", "country_region", 
                                "street_address", "unit", "city_district", "state_district", "suburb", "house", "level"]
                for sub_field_name in address_fields:
                    value = getattr(field_value, sub_field_name, None)
                    if value:  # Only append non-null values
                        data.append({
                            "Field Name": f"{field_name}.{sub_field_name}",
                            "Value": value,
                        }) 

            else:
                data.append({
                    "Field Name": field_name,
                    "Value": field_value,
                    # "Confidence": field_value.confidence,
                })

    file_extension = os.path.splitext(file)[1].lower()
    # Allowed formats
    allowed_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".pdf"]
    if file_extension not in allowed_formats:
        print("Unsupported file format. Please provide an image or PDF.")
        return

    print(f"Processing: {file}")

    try:
        # Analyze the document
        with open(file, "rb") as f:
            poller = client.begin_analyze_document("prebuilt-receipt", f)
            result = poller.result()

        # Extract data from the analyzed document
        data = []
        if result.documents:
            for receipt in result.documents:  # Iterate over the receipts
                for field_name, field in receipt.fields.items():
                    if field.value:
                        handle_nested_field(field_name, field.value, data)

        # Convert extracted data to a pandas DataFrame
        df = pd.DataFrame(data)

        # Save the DataFrame to an Excel file
        output_file = f"{os.path.splitext(file)[0]}.xlsx"
        df.to_excel(output_file, index=False)
        print(f"Data saved nge {output_file}")
        return output_file
        
    except Exception as e:
        # Print error and proceed to the next file
        print(f"Failed to process {file}. Error: {e}")
        return None
                


