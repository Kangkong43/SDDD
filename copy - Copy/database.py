import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Database setup
DATABASE = 'app.db'

def get_db():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows column access by name
    return conn

def create_table():
    """Create the users table if it does not exist."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                profile_picture TEXT
            )
        ''')
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            professor_id INTEGER,
            day TEXT,
            office TEXT,
            start_time TEXT,
            end_time TEXT
        )
    ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                professor_id INTEGER,
                appointment_date TEXT NOT NULL,
                appointment_time TIME NOT NULL,
                purpose TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                office TEXT,
                reason TEXT,        
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (professor_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, 
        
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL,
            appointment_id INTEGER,
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
  
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        )
        ''')
     
        conn.commit()
    except Exception as e:
        print("Database Table Creation Error:", str(e))
    finally:
        conn.close()

# Ensure tables exist at startup
create_table()

def get_user_by_email(email):
    """Retrieve a user by email."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
    except Exception as e:
        print("Database Fetch Error:", str(e))
        user = None
    finally:
        conn.close()
    return user

def get_user_by_id(user_id):
    """Retrieve a user by ID."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, role, email, profile_picture FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None
    except Exception as e:
        print("Database Fetch Error:", str(e))
        return None
    finally:
        conn.close()

def create_user(name, email, password, role,):
    """Insert a new user into the database."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        hashed_password = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (name, email, password, role, profile_picture)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, hashed_password, role, None))
        conn.commit()
        return True  # Successfully created
    except sqlite3.IntegrityError:
        print("Error: Email already exists.")
        return False  # Email already exists
    except Exception as e:
        print("Database Insert Error:", str(e))
        return False
    finally:
        conn.close()

def verify_user(email, password):
    """Verify a user's credentials."""
    user = get_user_by_email(email)
    if user and check_password_hash(user['password'], password):
        return user
    return None

def update_user(user_id, name=None, email=None, password=None, profile_picture=None):
    """Update a user's information."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        query = "UPDATE users SET "
        updates = []
        params = []

        if name is not None:  # Changed from "if name:"
            updates.append("name = ?")
            params.append(name)
        if email is not None:  # Changed from "if email:"
            updates.append("email = ?")
            params.append(email)
        if password is not None:  # Changed from "if password:"
            updates.append("password = ?")
            params.append(password)  # Now expecting an already hashed password
        if profile_picture is not None:  # Changed from "if profile_picture:"
            updates.append("profile_picture = ?")
            params.append(profile_picture)

        if updates:
            query += ", ".join(updates) + " WHERE id = ?"
            params.append(user_id)
            cursor.execute(query, params)
            conn.commit()

            if cursor.rowcount > 0:
                return True
            else:
                print("No user found with ID:", user_id)
                return False
        else:
            print("No data provided for update.")
            return False

    except Exception as e:
        print("Database Update Error:", str(e))
        return False
    finally:
        conn.close()

def add_schedule_to_db(professor_id, day, office, start_time, end_time):
    conn = get_db()
    cursor = conn.cursor()
    print("Adding schedule:", professor_id, day, office, start_time, end_time)

    # Check if the schedule already exists
    cursor.execute('''
        SELECT * FROM schedules
        WHERE professor_id = ? AND day = ? AND office = ? AND start_time = ? AND end_time = ?
    ''', (professor_id, day, office, start_time, end_time))

    if cursor.fetchone():
        conn.close()
        print("Schedule already exists.")
        return 'exists'

    try:
        cursor.execute('''
            INSERT INTO schedules (professor_id, day, office, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (professor_id, day, office, start_time, end_time))
        conn.commit()
        print("Schedule added successfully.")
        return 'success'
    except Exception as e:
        conn.rollback()
        print("Failed to add schedule:", str(e))
        return 'error'
    finally:
        conn.close()


def remove_schedule_to_db(professor_id, day, office, start_time, end_time):
    conn = get_db()
    cursor = conn.cursor()
    print("Removing schedule:", professor_id, day, office, start_time, end_time)

    # Check if the schedule exists
    cursor.execute('''
        SELECT * FROM schedules
        WHERE professor_id = ? AND day = ? AND office = ? AND start_time = ? AND end_time = ?
    ''', (professor_id, day, office, start_time, end_time))

    if not cursor.fetchone():
        conn.close()
        print("No schedule found to remove.")
        return 'no_schedule_found'

    try:
        cursor.execute('''
            DELETE FROM schedules
            WHERE professor_id = ? AND day = ? AND office = ? AND start_time = ? AND end_time = ?
        ''', (professor_id, day, office, start_time, end_time))

        conn.commit()
        print("Schedule removed successfully.")
        return 'success'
    except Exception as e:
        conn.rollback()
        print(f"Failed to remove schedule: {str(e)}")
        return 'error'
    finally:
        conn.close()



def get_schedules_for_professor(prof_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Execute query with parameterized input to prevent SQL injection
        cursor.execute('''
            SELECT day, office, start_time, end_time 
            FROM schedules 
            WHERE professor_id = ?
            ORDER BY day, start_time
        ''', (prof_id,))
        
        schedules = cursor.fetchall()
  
        # Properly format the returned data
        return [{
            'day': sched[0],
            'office': sched[1],
            'start_time': sched[2],  # Changed from 'time' to 'start_time'
            'end_time': sched[3]     # Added end_time which was missing
        } for sched in schedules]
        
    except Exception as e:
        # Log the error for debugging
        print(f"Database error: {str(e)}")
        return []  # Return empty list on error
    finally:
        # Ensure connection is always closed
        conn.close()

def update_schedule_in_db(professor_id, day, start_time, end_time, office):
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE schedules
            SET office = ?, start_time = ?, end_time = ?
            WHERE professor_id = ? AND day = ?
        ''', (office, start_time, end_time, professor_id, day))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error while updating schedule: {str(e)}")
        return False
    finally:
        conn.close()



    

def clear_schedules_for_professor(professor_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM schedules WHERE professor_id = ?', (professor_id,))
        conn.commit()
        print(f"All schedules cleared for professor_id: {professor_id}")
        return 'success'
    except Exception as e:
        conn.rollback()
        print(f"Failed to clear schedules: {str(e)}")
        return 'error'
    finally:
        conn.close()

def get_all_professors():
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users WHERE role = 'professor'")
    professors = cursor.fetchall()
    conn.close()
    return professors

def insert_appointment(user_id, professor_id, appointment_date, appointment_time, purpose, status, office): 
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO appointments (user_id, professor_id, appointment_date, appointment_time, purpose, status, office)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, professor_id, appointment_date, appointment_time, purpose, status, office))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Error while saving appointment: {str(e)}")
        raise
    finally:
        conn.close()



def get_user_appointments(user_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.id, p.name AS professor_name, a.appointment_date, a.start_time, a.end_time, a.purpose
            FROM appointments a
            JOIN users p ON a.professor_id = p.id
            WHERE a.user_id = ?
        ''', (user_id,))
        appointments = cursor.fetchall()
        return appointments
    except Exception as e:
        print(f"Error while fetching user appointments: {str(e)}")
        return []
    finally:
        conn.close()

def get_appointment_by_id(appointment_id):
    """Get full appointment details by ID"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT a.*, u.name AS student_name, p.name AS professor_name
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            JOIN users p ON a.professor_id = p.id
            WHERE a.id = ?
        ''', (appointment_id,))
        appointment = cursor.fetchone()
        return dict(appointment) if appointment else None
    except Exception as e:
        print(f"Error getting appointment: {str(e)}")
        return None
    finally:
        conn.close()

def check_duplicate_appointment(prof_id, appointment_date, appointment_time):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM appointments
        WHERE professor_id = ? AND appointment_date = ? AND appointment_time = ?
    """, (prof_id, appointment_date, appointment_time))
    
    existing_appointment = cursor.fetchone()
    conn.close()
    
    return existing_appointment is not None


def get_appointments_for_student(student_id):
    try:
        # Get the database connection
        conn = get_db()
        cursor = conn.cursor()

        # Query to fetch the appointments along with their id
        query = """
        SELECT a.id, p.name, a.office, a.appointment_date, a.appointment_time, a.purpose, a.status, a.reason -- <--- ADDED a.reason
        FROM appointments a
        JOIN users p ON a.professor_id = p.id
        WHERE a.user_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time ASC
        """

        # Execute the query with the student_id as the parameter
        cursor.execute(query, (student_id,))

        # Fetch all results
        appointments = cursor.fetchall()
        print(appointments)  # Debugging to see the fetched appointments
        
        # Convert the result to a list of dictionaries for easy access
        appointments_dict = [dict(zip([column[0] for column in cursor.description], row)) for row in appointments]
        
        return appointments_dict

    except Exception as e:
        print(f"Error fetching appointments: {e}")
        return []


    


def get_professor_appointments(professor_id):
    """Get all appointments for a professor with student names"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT a.id, u.name AS student_name, a.appointment_date, a.appointment_time,
                a.purpose, a.status, a.office, a.reason -- <--- ADDED a.reason
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.professor_id = ?
            ORDER BY a.appointment_date DESC, a.appointment_time ASC
        ''', (professor_id,))

        appointments = cursor.fetchall()
        return [dict(row) for row in appointments]
    except Exception as e:
        print(f"Error fetching professor appointments: {e}")
        return []
    finally:
        conn.close()


def clear_all_notifications_db(user_id):
    """Delete all notifications for a specific user"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM notifications WHERE user_id = ?', (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Database Error clearing notifications: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_appointment_status(appointment_id, status, professor_id, reason=None):
    """Update an appointment's status in the database and return the student ID"""
    conn = get_db()
    cursor = conn.cursor()
    student_id = None
 

    try:
        # Get the student_id associated with the appointment
        cursor.execute("SELECT user_id FROM appointments WHERE id = ? AND professor_id = ?", (appointment_id, professor_id))
        result = cursor.fetchone()
        if result:
            student_id = result[0]
            print(f"Debug: Updating appointment {appointment_id} with status {status} and reason {reason}")

            if status in ['Rejected', 'Cancelled'] and reason is not None:
                cursor.execute('''
                    UPDATE appointments
                    SET status = ?, reason = ?  -- <-- Updated column name to 'reason'
                    WHERE id = ?
                ''', (status, reason, appointment_id))
            else:
                # For Approved, Completed, or other statuses (or Rejected/Cancelled with no reason provided),
                # set the reason column to NULL.
                cursor.execute('''
                    UPDATE appointments
                    SET status = ?, reason = NULL -- <-- Updated column name to 'reason'
                    WHERE id = ?
                ''', (status, appointment_id))

            conn.commit()
            print(f"Rows updated: {cursor.rowcount}")

            if cursor.rowcount > 0:
                return True, student_id
            else:
                print(f"Warning: No appointment found with ID {appointment_id} for professor {professor_id}")
                return False, None
        else:
            print(f"Warning: Appointment with ID {appointment_id} not found.")
            return False, None
    except Exception as e:
        print(f"Error updating appointment status: {str(e)}")
        conn.rollback()
        return False, None
    finally:
        conn.close()






def create_notification(user_id, title, message, notification_type, appointment_id=None):
    """
    Create a new notification in the database
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO notifications (user_id, title, message, type, appointment_id, is_read, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, datetime('now'))",
            (user_id, title, message, notification_type, appointment_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating notification: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()



def get_user_notifications(user_id):
    """
    Get all notifications for a professor, ordered by newest first
    """
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id, title, message, type, appointment_id, is_read, created_at "
            "FROM notifications "
            "WHERE user_id = ? "
            "ORDER BY created_at DESC",
            (user_id,)
        )
        notifications = cursor.fetchall()
        
       
        formatted_notifications = []
        for row in notifications:
            notif = dict(row)
            try:
                notif['created_at'] = datetime.fromisoformat(notif['created_at'])  # safe for ISO format
            except Exception:
                notif['created_at'] = None  # fallback if it fails
            formatted_notifications.append(notif)

        return formatted_notifications

    except Exception as e:
        print(f"Error fetching notifications: {e}")
        return []
    finally:
        conn.close()
def cancel_appointment_in_db(appointment_id, student_id):
    """
    Cancel a pending appointment for a specific student.

    Args:
        appointment_id (int): The ID of the appointment to cancel.
        student_id (int): The ID of the student attempting to cancel.

    Returns:
        bool: True if the appointment was found and successfully cancelled, False otherwise.
    """
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Find the appointment and verify it belongs to the student and is pending
        cursor.execute('''
            SELECT id FROM appointments
            WHERE id = ? AND user_id = ? AND status = 'Pending'
        ''', (appointment_id, student_id))

        appointment = cursor.fetchone()

        if appointment:
        # If found and pending, update the status to 'Cancelled'
            cursor.execute('''
                UPDATE appointments
                SET status = 'Cancelled', reason = NULL -- <--- ADDED reason = NULL
                WHERE id = ?
            ''', (appointment_id,))
            conn.commit()
            print(f"Appointment {appointment_id} cancelled by student {student_id}.")
            return True
        else:
            # Appointment not found, or doesn't belong to the student, or is not pending
            print(f"Cancellation failed for appointment {appointment_id}: Not found, wrong student, or not pending.")
            return False

    except Exception as e:
        print(f"Database Error cancelling appointment {appointment_id}: {str(e)}")
        conn.rollback() # Rollback changes in case of error
        return False
    finally:
        conn.close()
def check_if_slot_taken(professor_id, appointment_date, appointment_time):
    """
    Checks if a specific time slot for a professor is already taken by an
    APPROVED appointment.
    Returns True if an APPROVED appointment exists, False otherwise.
    """
    conn = None # Initialize connection outside try block
    try:
        conn = get_db() # Assuming this function exists and returns a connection
        cursor = conn.cursor()

        # Modify the query to only count appointments with 'Approved' status
        # This is the crucial part that should prevent blocking on Rejected/Cancelled
        query = """
            SELECT COUNT(*) FROM appointments
            WHERE professor_id = ?
            AND appointment_date = ?
            AND appointment_time = ?
            AND status = 'Approved' -- Only consider Approved appointments as "taken"
        """
        params = (professor_id, appointment_date, appointment_time)

        print(f"DEBUG: Checking if professor {professor_id}'s slot is taken at {appointment_date} {appointment_time} with query: {query} and params: {params}") # Added debug print
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        print(f"DEBUG: check_if_slot_taken returned count: {count}") # Added debug print


        return count > 0 # Return True if count is greater than 0 (meaning an Approved booking exists)

    except Exception as e:
        print(f"Database error in check_if_slot_taken: {e}")
        # Log the error properly in a real application
        return False # Return False in case of database error

    finally:
        if conn:
            conn.close() # Ensure the connection is closed


def user_has_appointment_at_time(user_id, appointment_date, appointment_time):
    """
    Checks if a user has an ACTIVE (Pending or Approved) appointment
    at the given date and time.
    Returns True if an active appointment exists, False otherwise.
    """
    conn = None # Initialize connection outside try block
    try:
        conn = get_db() # Assuming this function exists and returns a connection
        cursor = conn.cursor()

        # Modify the query to only count appointments with 'Pending' or 'Approved' status
        # This is the crucial part that excludes Rejected/Cancelled/Completed
        query = """
            SELECT COUNT(*) FROM appointments
            WHERE user_id = ?
            AND appointment_date = ?
            AND appointment_time = ?
            AND status IN ('Pending', 'Approved') -- Only consider active statuses
        """
        params = (user_id, appointment_date, appointment_time)

        print(f"DEBUG: Checking if user {user_id} has active appointment at {appointment_date} {appointment_time} with query: {query} and params: {params}") # Added debug print
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        print(f"DEBUG: user_has_appointment_at_time returned count: {count}") # Added debug print

        return count > 0 # Return True if count is greater than 0 (meaning an active booking exists)

    except Exception as e:
        print(f"Database error in user_has_appointment_at_time: {e}")
        # Log the error properly in a real application
        return False # Return False in case of database error

    finally:
        if conn:
            conn.close() # Ensure the connection is closed
