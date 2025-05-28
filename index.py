import psycopg2
from decimal import Decimal
from getpass import getpass
import bcrypt

def connect_db():
    return psycopg2.connect(
        dbname="my_app_db",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )

class User:
    def __init__(self, user_id=None, username=None):
        self.user_id = user_id
        self.username = username

    @staticmethod
    def register():
        conn = connect_db()
        cur = conn.cursor()
        username = input("Enter username: ")
        password = getpass("Enter password: ")

        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash.decode('utf-8'))
            )
            conn.commit()
            print("User registered successfully!")
        except psycopg2.errors.UniqueViolation:
            print("Username already exists. Try another.")
            conn.rollback()
        except Exception as e:
            print("Error during registration:", e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def login():
        conn = connect_db()
        cur = conn.cursor()

        username = input("Enter username: ")
        password = getpass("Enter password: ")

        try:
            cur.execute(
                "SELECT id, password_hash FROM users WHERE username = %s",
                (username,)
            )
            user = cur.fetchone()
            if user is None:
                print("Invalid username or password.")
                return None

            user_id, password_hash = user
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                print("Login successful!")
                return User(user_id, username)
            else:
                print("Invalid username or password.")
                return None
        except Exception as e:
            print("Error during login:", e)
            return None
        finally:
            cur.close()
            conn.close()

class LoanSystem:
    def __init__(self, user: User):
        self.user = user

    def apply_loan(self):
        amount_str = input("Enter loan amount: ")
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                print("Loan amount must be positive.")
                return
        except:
            print("Invalid amount.")
            return

        conn = connect_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO loans (user_id, loan_amount, balance) VALUES (%s, %s, %s)",
                (self.user.user_id, amount, amount)
            )
            conn.commit()
            print("Loan applied successfully!")
        except Exception as e:
            print("Error applying loan:", e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    def make_payment(self):
        conn = connect_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, balance FROM loans WHERE user_id = %s AND balance > 0", (self.user.user_id,))
            loans = cur.fetchall()
            if not loans:
                print("No active loans found.")
                return

            print("Active loans:")
            for loan in loans:
                print(f"Loan ID: {loan[0]}, Balance: {loan[1]}")

            loan_id_str = input("Enter Loan ID to make a payment: ")
            try:
                loan_id = int(loan_id_str)
            except:
                print("Invalid Loan ID.")
                return

            cur.execute("SELECT balance FROM loans WHERE id = %s AND user_id = %s", (loan_id, self.user.user_id))
            res = cur.fetchone()
            if not res:
                print("Loan not found.")
                return

            balance = res[0]

            payment_str = input("Enter payment amount: ")
            try:
                payment_amount = Decimal(payment_str)
                if payment_amount <= 0:
                    print("Payment must be positive.")
                    return
            except:
                print("Invalid payment amount.")
                return

            if payment_amount > balance:
                print(f"Payment capped to remaining balance: {balance}")
                payment_amount = balance

            new_balance = balance - payment_amount

            cur.execute("UPDATE loans SET balance = %s WHERE id = %s", (new_balance, loan_id))

            cur.execute(
                "INSERT INTO payments (loan_id, payment_amount) VALUES (%s, %s)",
                (loan_id, payment_amount)
            )
            conn.commit()
            print(f"Payment successful! New balance: {new_balance}")

            if new_balance == 0:
                print("Loan fully paid!")
        except Exception as e:
            print("Error making payment:", e)
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    def check_balance(self):
        conn = connect_db()
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, balance FROM loans WHERE user_id = %s", (self.user.user_id,))
            loans = cur.fetchall()
            if not loans:
                print("No loans found.")
                return
            print("Your loans and balances:")
            for loan in loans:
                print(f"Loan ID: {loan[0]}, Balance: {loan[1]}")
        except Exception as e:
            print("Error fetching balances:", e)
        finally:
            cur.close()
            conn.close()

    def view_payment_history(self):
        loan_id_str = input("Enter Loan ID to view payment history: ")
        try:
            loan_id = int(loan_id_str)
        except:
            print("Invalid Loan ID.")
            return

        conn = connect_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT payment_amount, payment_date FROM payments WHERE loan_id = %s ORDER BY payment_date DESC",
                (loan_id,)
            )
            payments = cur.fetchall()
            if not payments:
                print("No payments made yet.")
                return

            print(f"Payment history for Loan ID {loan_id}:")
            for payment in payments:
                print(f"Amount: {payment[0]}, Date: {payment[1]}")
        except Exception as e:
            print("Error fetching payment history:", e)
        finally:
            cur.close()
            conn.close()

def user_dashboard(user: User):
    loan_system = LoanSystem(user)
    while True:
        print("""
1. Apply for Loan
2. Make Payment
3. Check Balance
4. View Payment History
5. Logout
""")
        choice = input("Choose: ")
        if choice == "1":
            loan_system.apply_loan()
        elif choice == "2":
            loan_system.make_payment()
        elif choice == "3":
            loan_system.check_balance()
        elif choice == "4":
            loan_system.view_payment_history()
        elif choice == "5":
            print("Logged out.")
            break
        else:
            print("Invalid choice, try again.")

def main():
    while True:
        print("""
1. Register
2. Login
3. Exit
""")
        choice = input("Choose: ")
        if choice == "1":
            User.register()
        elif choice == "2":
            user = User.login()
            if user:
                user_dashboard(user)
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()
