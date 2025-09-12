import json
import random
from datetime import datetime

def generate_connect_staff_data():
    """
    Generates sample data for ConnectStaff and saves it to a JSON file.
    """
    try:
        with open('_sample_data/staff.json', 'r', encoding='utf-8') as f:
            staff_data = json.load(f)
    except FileNotFoundError:
        print("Error: _sample_data/staff.json not found.")
        return

    try:
        with open('_sample_data/company.json', 'r', encoding='utf-8') as f:
            company_data = json.load(f)
    except FileNotFoundError:
        print("Error: _sample_data/company.json not found.")
        return

    if not company_data:
        print("Error: _sample_data/company.json is empty.")
        return

    # Assuming the first company in the file is the one to use.
    corporate_number = company_data[0]['fields']['corporate_number']

    # --- Data Generation ---
    all_staff = [s for s in staff_data if s['model'] == 'staff.staff']

    # 1. Select 80% of staff randomly
    num_to_select = int(len(all_staff) * 0.8)
    selected_staff = random.sample(all_staff, num_to_select)

    # 2. Of the selected, determine which ones to approve (80%)
    num_to_approve = int(len(selected_staff) * 0.8)
    approved_staff_pks = {s['pk'] for s in random.sample(selected_staff, num_to_approve)}

    connect_staff_data = []
    pk_counter = 1
    superuser_pk = 1 # Assuming superuser has pk=1

    for staff in selected_staff:
        staff_pk = staff['pk']
        email = staff['fields']['email']

        if not email:
            continue

        is_approved = staff_pk in approved_staff_pks

        record = {
            "model": "connect.connectstaff",
            "pk": pk_counter,
            "fields": {
                "created_at": datetime.now().isoformat(),
                "created_by": superuser_pk,
                "updated_at": datetime.now().isoformat(),
                "updated_by": superuser_pk,
                "corporate_number": corporate_number,
                "email": email,
                "status": "approved" if is_approved else "pending",
                "approved_at": datetime.now().isoformat() if is_approved else None,
                "approved_by": superuser_pk if is_approved else None,
            }
        }
        connect_staff_data.append(record)
        pk_counter += 1

    # --- Save to file ---
    output_path = '_sample_data/connect_staff.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(connect_staff_data, f, indent=4, ensure_ascii=False)

    print(f"✅ Successfully generated {len(connect_staff_data)} records in {output_path}")

if __name__ == "__main__":
    generate_connect_staff_data()
