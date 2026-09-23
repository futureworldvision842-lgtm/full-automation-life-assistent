# risk_calculator.py

def calculate_risk_account_balance(account_balance):
    """
    Calculate 0.75 percent risk dollar amount from account balance
    Args:
        account_balance (float): The account balance in dollars

    Returns:
        float: The calculated risk dollar amount
    """
    risk_dollar_amount = 0.75 * account_balance
    return risk_dollar_amount

# Function to check the correctness of the calculate_risk_account_balance function
def check_risk(account_balance):
    calculated_risk = calculate_risk_account_balance(account_balance)
    print(f"Account balance: {account_balance}, Risk: {calculated_risk}")

# Test the function with a sample account balance
check_risk(100000)