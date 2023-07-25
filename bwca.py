import sys
import requests
from collections import OrderedDict
import json
import smtplib
from email.mime.text import MIMEText

def send_email(subject, body):
    # Replace 'your_gmail_address' and 'your_gmail_password' with your actual Gmail credentials
    sender_email = ''
    password = ''
    receiver_email = ''

    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = receiver_email

    try:
        server = smtplib.SMTP('smtp-relay.brevo.com', 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error while sending email: {e}")
    finally:
        server.quit()


def get_api_data(api_url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Dnt": "1",
            "Referer": "https://www.recreation.gov/permits/233396/registration/detailed-availability?type=OvernightPaddle&date=2023-07-24T19:45:38-05:00"
        }
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for unsuccessful status codes (4xx and 5xx)
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while making the API call: {e}")
        return None

if __name__ == "__main__":
    permit_content = get_api_data("https://www.recreation.gov/api/permitcontent/233396")
    if permit_content:
        payload = permit_content.get('payload', {})
        divisions = payload.get('divisions', {})

    api_url = "https://www.recreation.gov/api/permits/233396/availability/month?start_date=2023-08-01T00:00:00.000Z&commercial_acct=false"
    api_data = get_api_data(api_url)

    if api_data:
        payload = api_data.get('payload', {})
        availability = payload.get('availability', {})

        range1 = set(range(1, 98))
        range2 = set(range(276718, 278020))
        combined_range = range1.union(range2)

        if len(sys.argv) != 2:
            print("Usage: python your_script_name.py target_date")
            sys.exit(1)

        target_date = sys.argv[1]
        full_date_str = f"{target_date}T00:00:00Z"

        data_dict = {}
        for num in combined_range:
            entry_num = str(num)
            entry_data = availability.get(entry_num)
            
            if entry_data:
                date_availability = entry_data.get('date_availability', {})
                data_for_date = date_availability.get(full_date_str, None)

                if data_for_date:
                    remaining = data_for_date.get('remaining', {})
                    name = divisions.get(entry_num, {}).get('name', {})
                    if "(OP)" in name:
                        name = name.replace("(OP)", '')

                        if remaining > 0:
                            data_dict[name] = remaining

        ordered_data_dict = OrderedDict(sorted(data_dict.items()))

        # Compare with the previous run
        previous_data = {}
        try:
            with open("previous_data.json", "r") as file:
                previous_data = json.load(file)
        except FileNotFoundError:
            pass

        if previous_data != data_dict:
            print("Changes detected:")
            for name, remaining in ordered_data_dict.items():
                print(f"{name}: {remaining}")
            
            # Send an email with the changes
            email_subject = "Changes Detected in Permit Availability"
            email_body = "\n".join([f"{name}: {remaining}" for name, remaining in ordered_data_dict.items()])
            send_email(email_subject, email_body)

        else:
            print("No changes detected.")

        # Save the current data to the text file
        with open("previous_data.json", "w") as file:
            json.dump(data_dict, file)

    else:
        print("Failed to retrieve data from the API.")
