from flask import Flask, request, jsonify, render_template
from google.cloud import dialogflow_v2 as dialogflow
from db import create_tables, insert_sample_data, get_leave_balance, get_all_leaves
import os
import logging

def create_app():
    app = Flask(__name__)
    create_tables()
    insert_sample_data()
    
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "bank-key.json"
    print("Using credentials from:", os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    project_id = "bankbot-sfml"
    session_id = "test-session-1234"

    @app.route('/')
    def index():
        return render_template("index.html")
    
    def detect_intent_text(project_id, session_id, text, language_code="en"):
        session_client = dialogflow.SessionsClient()
        session = session_client.session_path(project_id, session_id)

        text_input = dialogflow.TextInput(text=text, language_code=language_code)
        query_input = dialogflow.QueryInput(text=text_input)

        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )

        result = response.query_result
        #logging.info("Extracted result: %s \n\n\n\n", result)

        response = result.fulfillment_text

        return response 
    
    @app.route('/chat', methods=['POST'])
    def chat():
        data = request.get_json()
        #logging.info("data info:                     %s \n\n", data)
        user_input = data.get("text", "")


        result = detect_intent_text(project_id, session_id, user_input, 'en')

        #logging.info(f"User input: {user_input}")
        #logging.info(f"Dialogflow response: {result} \n\n\n\n")

        return jsonify({'response': result})


    @app.route('/webhook', methods=['POST'])
    def webhook():
        req = request.get_json()
        service_type = req.get("queryResult", {}).get("parameters", {}).get("banking_service", "").lower()
        query_text = req.get("queryResult", {}).get("queryText", "").lower()
        intent_name = req.get("queryResult", {}).get("intent", {}).get("displayName", "").lower()
        name = req.get("queryResult", {}).get("parameters", {}).get("employee_name", "")
        leave_type = req.get("queryResult", {}).get("parameters", {}).get("leave_type", "").lower()
        
        # Default fallback response
        response_text = "I'm sorry, I couldn't find information about that service."

        #leave types and their descriptions
        leave_types = {
            "pl": " **Privilege Leave (PL) / Earned Leave (EL) / Annual Leave (AL)**\nThis is earned based on the number of days worked (typically 20 days per year). It is used for personal matters such as vacations or festivals. This leave can be carried forward and encashed.",
            "cl": " **Casual Leave (CL)**\nFor urgent/personal matters. Typically allowed for 1-2 days, with prior employer approval. Not always eligible for carry forward.",
            "sl": " **Sick Leave (SL)**\nTaken when an employee is ill or injured. Often requires a medical certificate if it exceeds 2-3 days. In some regions, CL and SL may be merged.",
            "ml": " **Maternity Leave (ML)**\nUp to 26 weeks for eligible women who have worked for at least 80 days in the past 12 months. Covers childbirth, miscarriage, and related medical conditions. May require medical proof.",
            "comp-off": " **Compensatory Off (Comp-off)**\nGranted when an employee works on holidays or weekends. Must be claimed and approved within 4-8 weeks of occurrence.",
            "marriage": " **Marriage Leave**\nOffered in some organizations (1-15 days) for an employee's legal first marriage. Requires submission of proof and approval from HR.",
            "paternity": " **Paternity Leave**\nGiven to new fathers to support family care. Duration ranges from 2 days to 4 weeks. Depends on the employer's internal policy.",
            "bereavement": " **Bereavement Leave**\nGranted in the event of the death of a family member. It can range from 2 to 20 days and is discretionary. Covers funerals, rituals, and grieving.",
            "lop": " **Loss of Pay (LOP) / Leave Without Pay (LWP)**\nUsed when all other leave balances are exhausted. This type of leave results in salary deduction and is granted under specific circumstances."
        }
        
        if intent_name == "leaveinfogeneral":
            response_text = (
                "<strong>MAB offers a comprehensive range of employee leave options</strong> "
                "to support personal, family, and professional needs.<br><br>"
                "Below are the types of leaves available to employees:<br><br>"
            )
            response_text += "<br><br>".join([desc for desc in leave_types.values()])
            
        elif intent_name == "leaveinfotypespecific":
            

            leave_info = get_leave_balance(name, leave_type.upper())
            desc = leave_types.get(leave_type, f"**{leave_type.upper()}** leave information not available.")

            if leave_info:
                response_text = (
                    f"{desc}<br><br>"
                    f"<strong>{name}'s {leave_type.upper()} Leave Usage:</strong><br>"
                    f"- Total: {leave_info['used_days'] + leave_info['remaining_days']} days<br>"
                    f"- Used: {leave_info['used_days']} days<br>"
                    f"- Remaining: {leave_info['remaining_days']} days"
                )
            else:
                response_text = f"No {leave_type.upper()} leave record found for {name}."

        elif query_text == "leave":
            response_text = (
                "**MAB offers a comprehensive range of employee leave options** to support personal, family, and professional needs. "
                "Below are the types of leaves available to employees:\n\n"
            )
            response_text += "\n".join([leave_types[key] for key in leave_types])
        else:
            if name:
                if leave_type:
                    leave_info = get_leave_balance(name, leave_type.upper())
                    if leave_info:
                        desc = leave_types.get(leave_type.lower(), f"**{leave_type.upper()}** leave info not available.")
                        response_text = (
                            f"{desc}\n\n"
                            f"**{name}'s {leave_type.upper()} Leave Usage**:\n"
                            f"- Total: {leave_info['used_days'] + leave_info['remaining_days']} days\n"
                            f"- Used: {leave_info['used_days']} days\n"
                            f"- Remaining: {leave_info['remaining_days']} days"
                        )
                    else:
                        response_text = f"No {leave_type.upper()} leave record found for {name}."
                else:
                    leave_records = get_all_leaves(name)
                    if leave_records:
                        response_text = f"**{name}'s Leave Balances**\n\n"
                        for record in leave_records:
                            lt = record['leave_type'].upper()
                            desc = leave_types.get(lt.lower(), f"**{lt}** leave info not available.")
                            response_text += (
                                f"{desc}\n- Total: {record['used_days'] + record['remaining_days']} days\n"
                                f"- Used: {record['used_days']} days\n"
                                f"- Remaining: {record['remaining_days']} days\n\n"
                            )
                    else:
                        response_text = f"Sorry, no leave record found for {name}."


        if service_type == "savings account":
            response_text = (
                "MAB's Savings Account offers an attractive interest rate of 8.00% per annum.\n"
                "Interest is calculated monthly based on the lowest balance maintained between the 5th and the last day of each month and is deposited monthly into the account.\n"
                "To open a savings account, a minimum initial deposit of 10,000 kyats is required, and the account must maintain a minimum balance of 10,000 kyats.\n"
                "Additionally, the savings account can be conveniently linked with an MPU card, iBanking, and Mobile Banking services, allowing easy access and management of funds.\n"
                "Would you like to explore another service or need more assistance?"
            )

        elif service_type == "current account":
            response_text = (
                "The Current Account is specially designed for businessmen and individuals who conduct frequent transactions."
                "It allows the use of cheques for both depositing and withdrawing cash, offering convenience and flexibility." 
                "To open a current account, a minimum initial deposit of 10,000 kyats is required, and the account must maintain a minimum balance of 10,000 kyats." 
                "There is no limit on cash withdrawals, making it ideal for high-volume transactions. Additionally, a cheque book is available for 1,600 kyats.\n"
                "Would you like to know about another service?"
            )
            
        elif service_type == "fixed deposit account":
            response_text = (
                "A Fixed Deposit Account allows customers to deposit money for a fixed period to earn higher interest rates compared to other types of accounts. "
                "This account type is ideal for individuals who want to save extra money or for parents saving for their children. "
                "Interest is calculated based on the deposit term and will be adjusted if withdrawn prematurely.\n"
                "The interest rates offered are:\n"
                "- 30 days: 11.00%\n"
                "- 60 days: 11.15%\n"
                "- 90 days: 11.25%\n"
                "- 180 days: 11.50%\n"
                "- 270 days: 11.75%\n"
                "- 365 days: 12.00%\n"
                "To open a fixed deposit account, a minimum initial deposit of 100,000 kyats is required. "
                "Would you like to know about another service?"
            )
        
        elif service_type == "call deposit account":
            response_text = (
                "The Call Deposit Account offers an annual interest rate of 5%. "
                "Interest is calculated based on the daily balance and deposited every month. "
                "It can be linked with your current account for flexible fund access. "
                "To open a Call Deposit Account, an initial deposit of 10,000 MMK is required, "
                "and the minimum balance must be maintained at 10,000 MMK. "
                "Would you like to know about another service?"
            )
        
        elif service_type == "better remit savings":
            query = req.get("queryResult", {}).get("queryText", "").lower()

            if "interest rate" in query:
                response_text = "The annual interest rate for Better Remit Savings is 9.25%."
            elif "minimum balance" in query:
                response_text = "The minimum balance required is 10,000 MMK."
            elif "mpu" in query or "debit card" in query:
                response_text = "Yes, the Better Remit Savings account supports MPU-UPI debit cards."
            elif "reward" in query:
                response_text = "You can earn MAB Reward Points from purchases with your linked debit card."
            elif "loan" in query:
                response_text = "You are eligible for Auto and Home Loans with flexible down payment options."
            elif "joint" in query:
                response_text = "Yes, you can open a joint Better Remit Savings account."
            elif "individual" in query:
                response_text = "Yes, an individual account can be opened for Better Remit Savings."
            elif "convert" in query:
                response_text = "The account type can be converted later based on your preference."
            else:
                response_text = (
                    "The Better Remit Savings Account from MAB offers an annual interest rate of 9.25%. "
                    "This account is ideal for Myanmar workers overseas to save conveniently while enjoying benefits like linking to an MPU-UPI debit card, earning MAB Reward Points, and eligibility for MAB loans such as Auto and Home loans with flexible Down Payment options. "
            "You can open the account with just 10,000 MMK as an initial deposit and maintain a minimum balance of 10,000 MMK."
            "Would you like to know more about another service?"
                )

        elif service_type == "ibanking":
            response_text = (
                "MAB iBanking is a secure online banking service that allows you to conveniently manage your accounts from anywhere in the world. "
                "It helps you avoid queues and do banking from the comfort of your home or office. "
                "MAB iBanking supports multiple account types including current, savings, fixed, better, call, and smart saving accounts.\n\n"
                "Additionally, MAB eToken can be used to generate OTPs for secure transaction authentication.\n\n"
                "For detailed FAQs, visit: https://www.mabbank.com/faq/i-banking-faq/"
            )
            
        elif service_type == "mobile banking":
            response_text = (
                "MAB Mobile Banking allows you to make financial and payment transactions from any of your mobile phones.\n"
                "It is:\n"
                "- Flexible\n"
                "- Accessible\n"
                "- Affordable\n"
                "- Convenient\n"
                "- Secure\n\n"
                "For more details, visit: https://www.mabbank.com/faq/mobile-banking-faq/"
            )
            
        elif service_type == "global transaction banking":
            response_text = (
                "MAB's Global Transaction Banking offers trade finance and worldwide payment services, including:\n"
                "- Western Union and telegraphic transfer services\n"
                "- Foreign currency account\n"
                "- Foreign exchange services\n\n"
                "Foreign exchange is available between 9:30 AM and 3:00 PM at select MAB branches. "
                "Customers (including tourists, students, importers/exporters, and more) can exchange foreign currencies "
                "against MMK or against each other in accordance with Central Bank regulations.\n"
                "- Minimum Purchase: USD 300\n"
                "- Maximum Purchase: USD 500\n\n"
                "Foreign exchange counters:\n"
                "1. MAB Foreign Exchange Counter - 20 University Avenue, Bahan, Yangon | T: +95 (1) 8605041\n"
                "2. International Airport Money Exchange Counter (MAB) - Arrival Lounge\n\n"
                "Would you like to explore another service?"
            )



        return jsonify({"fulfillment_text": response_text})
    
    return app



